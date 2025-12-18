"""
League Manager Agent
====================

Manages the overall league:
- Player registration
- Match scheduling (round-robin)
- Standings/rankings
- Round coordination
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid

from ..server.base_server import BaseGameServer
from ..game.match import Match, MatchScheduler, MatchState
from ..common.logger import get_logger
from ..common.protocol import (
    MessageType,
    MessageFactory,
    RegistrationStatus,
    PROTOCOL_VERSION,
    generate_auth_token,
)
from ..common.exceptions import (
    RegistrationError,
    AlreadyRegisteredError,
    LeagueFullError,
)

logger = get_logger(__name__)


class LeagueState(Enum):
    """League state."""
    
    REGISTRATION = "registration"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


@dataclass
class RegisteredReferee:
    """A registered referee in the league."""
    
    referee_id: str
    endpoint: str
    auth_token: str = ""  # Authentication token for this referee
    version: str = "1.0.0"
    registered_at: datetime = field(default_factory=datetime.utcnow)
    is_available: bool = True  # Available to referee matches
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "referee_id": self.referee_id,
            "endpoint": self.endpoint,
            "is_available": self.is_available,
        }


@dataclass
class RegisteredPlayer:
    """A registered player in the league."""
    
    player_id: str
    display_name: str
    endpoint: str
    auth_token: str = ""  # Authentication token for this player
    version: str = "1.0.0"
    game_types: List[str] = field(default_factory=list)
    registered_at: datetime = field(default_factory=datetime.utcnow)
    
    # Stats
    wins: int = 0
    losses: int = 0
    draws: int = 0
    points: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "player_id": self.player_id,
            "display_name": self.display_name,
            "endpoint": self.endpoint,
            "wins": self.wins,
            "losses": self.losses,
            "draws": self.draws,
            "points": self.points,
        }
    
    def record_win(self) -> None:
        self.wins += 1
        self.points += 3
    
    def record_loss(self) -> None:
        self.losses += 1
    
    def record_draw(self) -> None:
        self.draws += 1
        self.points += 1


class LeagueManager(BaseGameServer):
    """
    League Manager Agent.
    
    Runs as MCP server and manages:
    - Player registration
    - Round-robin scheduling  
    - League standings
    - Match coordination with referee
    """
    
    def __init__(
        self,
        league_id: str = "league_2024_01",
        min_players: int = 2,
        max_players: int = 100,
        host: str = "localhost",
        port: int = 8000,
    ):
        super().__init__(
            name="league_manager",
            server_type="league_manager",
            league_id=league_id,
            host=host,
            port=port,
        )
        
        self.min_players = min_players
        self.max_players = max_players
        
        # League state
        self.state = LeagueState.REGISTRATION
        self.current_round = 0
        
        # Referees (Step 1: Referee Registration)
        self._referees: Dict[str, RegisteredReferee] = {}
        self._referee_id_counter = 0
        
        # Players
        self._players: Dict[str, RegisteredPlayer] = {}
        self._player_id_counter = 0
        
        # Schedule
        self._schedule: List[List[tuple]] = []
        self._matches: Dict[str, Match] = {}
        self._current_round_matches: List[Match] = []
        
        # Referee
        self._referee_endpoint: Optional[str] = None
        
        # Register tools
        self._register_tools()
        
        # Register resources
        self._register_resources()
    
    def _register_tools(self) -> None:
        """Register league manager tools."""
        
        @self.tool(
            "register_player",
            "Register a new player in the league",
            {
                "type": "object",
                "properties": {
                    "display_name": {"type": "string"},
                    "endpoint": {"type": "string"},
                    "version": {"type": "string"},
                    "game_types": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["display_name", "endpoint"],
            }
        )
        async def register_player(params: Dict) -> Dict:
            return await self._handle_registration(params)
        
        @self.tool(
            "get_standings",
            "Get current league standings",
        )
        async def get_standings(params: Dict) -> Dict:
            return self._get_standings()
        
        @self.tool(
            "get_schedule",
            "Get match schedule",
        )
        async def get_schedule(params: Dict) -> Dict:
            return self._get_schedule()
        
        @self.tool(
            "start_league",
            "Start the league competition",
        )
        async def start_league(params: Dict) -> Dict:
            return await self._start_league()
        
        @self.tool(
            "report_match_result",
            "Report match result from referee",
            {
                "type": "object",
                "properties": {
                    "match_id": {"type": "string"},
                    "winner_id": {"type": "string"},
                    "player1_score": {"type": "integer"},
                    "player2_score": {"type": "integer"},
                },
                "required": ["match_id"],
            }
        )
        async def report_match_result(params: Dict) -> Dict:
            return await self._handle_match_result(params)
        
        @self.tool(
            "get_players",
            "Get list of registered players",
        )
        async def get_players(params: Dict) -> Dict:
            return {"players": [p.to_dict() for p in self._players.values()]}
        
        @self.tool(
            "register_referee",
            "Register a referee with the league (Step 1 of league flow)",
            {
                "type": "object",
                "properties": {
                    "referee_id": {"type": "string"},
                    "endpoint": {"type": "string"},
                    "version": {"type": "string"},
                },
                "required": ["referee_id", "endpoint"],
            }
        )
        async def register_referee(params: Dict) -> Dict:
            return await self._handle_referee_registration(params)
        
        @self.tool(
            "get_referees",
            "Get list of registered referees",
        )
        async def get_referees(params: Dict) -> Dict:
            return {"referees": [r.to_dict() for r in self._referees.values()]}
        
        @self.tool(
            "set_referee",
            "Set the referee endpoint (legacy)",
            {
                "type": "object",
                "properties": {
                    "endpoint": {"type": "string"},
                },
                "required": ["endpoint"],
            }
        )
        async def set_referee(params: Dict) -> Dict:
            self._referee_endpoint = params.get("endpoint")
            return {"success": True, "referee_endpoint": self._referee_endpoint}
    
    def _register_resources(self) -> None:
        """Register league manager resources."""
        
        @self.resource(
            "league://standings",
            "League Standings",
            "Current league standings and rankings",
        )
        async def standings_resource(params: Dict) -> Dict:
            return self._get_standings()
        
        @self.resource(
            "league://players",
            "Registered Players",
            "List of all registered players",
        )
        async def players_resource(params: Dict) -> Dict:
            return {"players": [p.to_dict() for p in self._players.values()]}
        
        @self.resource(
            "league://schedule",
            "Match Schedule",
            "Complete match schedule",
        )
        async def schedule_resource(params: Dict) -> Dict:
            return self._get_schedule()
    
    async def _handle_referee_registration(self, params: Dict) -> Dict:
        """Handle referee registration (Step 1 of league flow)."""
        referee_id = params.get("referee_id", "")
        endpoint = params.get("endpoint", "")
        version = params.get("version", "1.0.0")
        
        # Validate state
        if self.state != LeagueState.REGISTRATION:
            return self.message_factory.referee_register_response(
                status=RegistrationStatus.REJECTED.value,
                referee_id="",
                reason="League registration is closed",
            )
        
        # Check if referee already registered
        if referee_id in self._referees:
            return self.message_factory.referee_register_response(
                status=RegistrationStatus.REJECTED.value,
                referee_id=referee_id,
                reason="Referee already registered",
            )
        
        # Generate auth token for referee
        auth_token = generate_auth_token(referee_id, self.league_id)
        
        # Create referee
        referee = RegisteredReferee(
            referee_id=referee_id,
            endpoint=endpoint,
            auth_token=auth_token,
            version=version,
        )
        
        self._referees[referee_id] = referee
        
        logger.info(
            f"Referee registered: {referee_id}",
            endpoint=endpoint,
        )
        
        return self.message_factory.referee_register_response(
            status=RegistrationStatus.ACCEPTED.value,
            referee_id=referee_id,
            auth_token=auth_token,
        )
    
    async def _handle_registration(self, params: Dict) -> Dict:
        """Handle player registration."""
        display_name = params.get("display_name", "")
        endpoint = params.get("endpoint", "")
        version = params.get("version", "1.0.0")
        game_types = params.get("game_types", ["even_odd"])
        
        # Validate state
        if self.state != LeagueState.REGISTRATION:
            return self.message_factory.register_response(
                status=RegistrationStatus.REJECTED.value,
                player_id="",
                reason="League registration is closed",
            )
        
        # Check if league is full
        if len(self._players) >= self.max_players:
            return self.message_factory.register_response(
                status=RegistrationStatus.REJECTED.value,
                player_id="",
                reason="League is full",
            )
        
        # Check game types
        if "even_odd" not in game_types:
            return self.message_factory.register_response(
                status=RegistrationStatus.REJECTED.value,
                player_id="",
                reason="Player must support 'even_odd' game type",
            )
        
        # Check if endpoint already registered
        for player in self._players.values():
            if player.endpoint == endpoint:
                return self.message_factory.register_response(
                    status=RegistrationStatus.REJECTED.value,
                    player_id="",
                    reason="Endpoint already registered",
                )
        
        # Generate player ID
        self._player_id_counter += 1
        player_id = f"P{self._player_id_counter:02d}"
        
        # Generate authentication token
        auth_token = generate_auth_token(player_id, self.league_id)
        
        # Create player
        player = RegisteredPlayer(
            player_id=player_id,
            display_name=display_name,
            endpoint=endpoint,
            auth_token=auth_token,
            version=version,
            game_types=game_types,
        )
        
        self._players[player_id] = player
        
        logger.info(
            f"Player registered: {display_name}",
            player_id=player_id,
            endpoint=endpoint,
        )
        
        return self.message_factory.register_response(
            status=RegistrationStatus.ACCEPTED.value,
            player_id=player_id,
            auth_token=auth_token,
        )
    
    async def _start_league(self) -> Dict[str, Any]:
        """Start the league."""
        if self.state != LeagueState.REGISTRATION:
            return {"success": False, "error": "League already started"}
        
        if len(self._players) < self.min_players:
            return {
                "success": False,
                "error": f"Need at least {self.min_players} players, have {len(self._players)}",
            }
        
        # Generate schedule
        player_ids = list(self._players.keys())
        self._schedule = MatchScheduler.create_round_robin_schedule(player_ids)
        
        self.state = LeagueState.READY
        
        logger.info(
            f"League ready to start",
            players=len(self._players),
            rounds=len(self._schedule),
        )
        
        return {
            "success": True,
            "players": len(self._players),
            "rounds": len(self._schedule),
            "schedule": self._get_schedule(),
        }
    
    def _assign_referee_to_match(self, match_index: int) -> Optional[str]:
        """
        Assign an available referee to a match (Step 4: Round Announcement).
        
        Uses round-robin assignment from registered referees.
        """
        available_referees = [r for r in self._referees.values() if r.is_available]
        if not available_referees:
            return None
        
        # Round-robin assignment
        referee = available_referees[match_index % len(available_referees)]
        return referee.referee_id
    
    async def start_next_round(self) -> Dict[str, Any]:
        """
        Start the next round of matches.
        
        Step 4: Publishes ROUND_ANNOUNCEMENT with matches and assigned referees.
        """
        if self.state not in (LeagueState.READY, LeagueState.IN_PROGRESS):
            return {"success": False, "error": "League not ready"}
        
        if self.current_round >= len(self._schedule):
            self.state = LeagueState.COMPLETED
            return {"success": False, "error": "All rounds completed", "league_complete": True}
        
        # Check if we have registered referees
        if not self._referees:
            return {"success": False, "error": "No referees registered. Register referees first (Step 1)."}
        
        self.state = LeagueState.IN_PROGRESS
        
        # Get round pairings
        pairings = self._schedule[self.current_round]
        self.current_round += 1
        
        # Create matches
        player_endpoints = {p.player_id: p.endpoint for p in self._players.values()}
        player_names = {p.player_id: p.display_name for p in self._players.values()}
        
        self._current_round_matches = MatchScheduler.create_matches_for_round(
            league_id=self.league_id,
            round_id=self.current_round,
            pairings=pairings,
            player_endpoints=player_endpoints,
            player_names=player_names,
        )
        
        # Step 4: Assign referees to matches and prepare announcement
        round_matches_info = []
        for i, match in enumerate(self._current_round_matches):
            # Assign referee
            referee_id = self._assign_referee_to_match(i)
            match.referee_id = referee_id
            
            # Store match
            self._matches[match.match_id] = match
            
            # Prepare match info for announcement
            round_matches_info.append({
                "match_id": match.match_id,
                "player1_id": match.player1.player_id,
                "player1_name": match.player1.name,
                "player2_id": match.player2.player_id,
                "player2_name": match.player2.name,
                "referee_id": referee_id,
                "referee_endpoint": self._referees[referee_id].endpoint if referee_id else None,
            })
        
        logger.info(
            f"Round {self.current_round} announced",
            matches=len(self._current_round_matches),
            referees_assigned=len([m for m in round_matches_info if m["referee_id"]]),
        )
        
        # Create ROUND_ANNOUNCEMENT message
        announcement = self.message_factory.round_announcement(
            round_number=self.current_round,
            matches=round_matches_info,
        )
        
        return {
            "success": True,
            "round": self.current_round,
            "announcement": announcement,
            "matches": round_matches_info,
        }
    
    async def _handle_match_result(self, params: Dict) -> Dict[str, Any]:
        """Handle match result from referee."""
        match_id = params.get("match_id")
        winner_id = params.get("winner_id")
        player1_score = params.get("player1_score", 0)
        player2_score = params.get("player2_score", 0)
        
        match = self._matches.get(match_id)
        if not match:
            return {"success": False, "error": f"Unknown match: {match_id}"}
        
        # Update standings
        if winner_id:
            if winner_id in self._players:
                self._players[winner_id].record_win()
            
            # Record loss for other player
            loser_id = match.player1.player_id if winner_id == match.player2.player_id else match.player2.player_id
            if loser_id in self._players:
                self._players[loser_id].record_loss()
        else:
            # Draw
            if match.player1.player_id in self._players:
                self._players[match.player1.player_id].record_draw()
            if match.player2.player_id in self._players:
                self._players[match.player2.player_id].record_draw()
        
        # Update match state
        match.state = MatchState.COMPLETED
        match.winner_id = winner_id
        match.final_score = {
            match.player1.player_id: player1_score,
            match.player2.player_id: player2_score,
        }
        
        logger.info(
            f"Match result recorded",
            match_id=match_id,
            winner=winner_id,
            score=f"{player1_score}-{player2_score}",
        )
        
        # Check if round complete
        round_complete = all(
            m.state == MatchState.COMPLETED
            for m in self._current_round_matches
        )
        
        # Step 6: If round complete, publish standings to all players
        standings = self._get_standings()
        standings_message = None
        if round_complete:
            standings_message = await self._publish_standings_update()
        
        return {
            "success": True,
            "round_complete": round_complete,
            "standings": standings,
            "standings_published": standings_message is not None,
        }
    
    async def _publish_standings_update(self) -> Dict[str, Any]:
        """
        Step 6: Publish standings update to all players after round completion.
        
        Creates and returns a STANDINGS_UPDATE message that should be
        broadcast to all registered players.
        """
        standings = self._get_standings()
        
        # Create STANDINGS_UPDATE message
        standings_message = self.message_factory.standings_update(
            round_number=self.current_round,
            total_rounds=len(self._schedule),
            standings=standings["standings"],
        )
        
        logger.info(
            f"Publishing standings update",
            round=self.current_round,
            total_players=len(self._players),
        )
        
        # Note: In a full implementation, this would broadcast to all players
        # via their registered endpoints. For now, we return the message
        # for the caller to handle distribution.
        
        return standings_message
    
    def _get_standings(self) -> Dict[str, Any]:
        """Get current standings."""
        # Sort by points, then wins, then goal difference
        sorted_players = sorted(
            self._players.values(),
            key=lambda p: (p.points, p.wins, -p.losses),
            reverse=True
        )
        
        return {
            "round": self.current_round,
            "total_rounds": len(self._schedule),
            "standings": [
                {
                    "rank": i + 1,
                    **p.to_dict()
                }
                for i, p in enumerate(sorted_players)
            ]
        }
    
    def _get_schedule(self) -> Dict[str, Any]:
        """Get match schedule."""
        schedule = []
        
        for round_num, pairings in enumerate(self._schedule, 1):
            round_matches = []
            for p1, p2 in pairings:
                p1_name = self._players[p1].display_name if p1 in self._players else p1
                p2_name = self._players[p2].display_name if p2 in self._players else p2
                round_matches.append({
                    "player1": {"id": p1, "name": p1_name},
                    "player2": {"id": p2, "name": p2_name},
                })
            schedule.append({
                "round": round_num,
                "matches": round_matches,
                "status": "completed" if round_num < self.current_round else
                         "in_progress" if round_num == self.current_round else "scheduled",
            })
        
        return {"schedule": schedule}
    
    # ========================================================================
    # Protocol Message Handlers
    # ========================================================================
    
    async def _handle_league_register_request(self, message: Dict) -> Dict:
        """Handle LEAGUE_REGISTER_REQUEST message."""
        player_meta = message.get("player_meta", {})
        
        result = await self._handle_registration({
            "display_name": player_meta.get("display_name", ""),
            "endpoint": player_meta.get("contact_endpoint", ""),
            "version": player_meta.get("version", "1.0.0"),
            "game_types": player_meta.get("game_types", []),
        })
        
        return result
    
    @property
    def player_count(self) -> int:
        """Get number of registered players."""
        return len(self._players)
    
    @property
    def is_registration_open(self) -> bool:
        """Check if registration is open."""
        return self.state == LeagueState.REGISTRATION

