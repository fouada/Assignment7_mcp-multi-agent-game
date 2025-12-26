"""
League Manager Agent
====================

Manages the overall league:
- Player registration
- Match scheduling (round-robin)
- Standings/rankings
- Round coordination
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from ..client.mcp_client import MCPClient
from ..common.events import (
    AgentRegisteredEvent,
    StandingsUpdatedEvent,
    TournamentRoundStartedEvent,
    get_event_bus,
)
from ..common.logger import get_logger
from ..common.protocol import RegistrationStatus, generate_auth_token
from ..game.match import Match, MatchScheduler, MatchState
from ..server.base_server import BaseGameServer

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
    display_name: str = ""  # Human-readable name (e.g., "Referee_Alpha")
    auth_token: str = ""  # Authentication token for this referee
    version: str = "1.0.0"
    game_types: list[str] = field(default_factory=lambda: ["even_odd"])
    max_concurrent_matches: int = 2  # Max matches referee can handle
    registered_at: datetime = field(default_factory=datetime.utcnow)
    is_available: bool = True  # Available to referee matches

    def to_dict(self) -> dict[str, Any]:
        return {
            "referee_id": self.referee_id,
            "display_name": self.display_name,
            "endpoint": self.endpoint,
            "game_types": self.game_types,
            "max_concurrent_matches": self.max_concurrent_matches,
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
    game_types: list[str] = field(default_factory=list)
    registered_at: datetime = field(default_factory=datetime.utcnow)

    # Stats
    played: int = 0  # Games played
    wins: int = 0
    draws: int = 0
    losses: int = 0
    points: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "display_name": self.display_name,
            "endpoint": self.endpoint,
            "played": self.played,
            "wins": self.wins,
            "draws": self.draws,
            "losses": self.losses,
            "points": self.points,
        }

    def record_win(self) -> None:
        self.played += 1
        self.wins += 1
        self.points += 3

    def record_loss(self) -> None:
        self.played += 1
        self.losses += 1

    def record_draw(self) -> None:
        self.played += 1
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
        self._referees: dict[str, RegisteredReferee] = {}
        self._referee_id_counter = 0

        # Players
        self._players: dict[str, RegisteredPlayer] = {}
        self._player_id_counter = 0

        # Schedule
        self._schedule: list[list[tuple]] = []
        self._matches: dict[str, Match] = {}
        self._current_round_matches: list[Match] = []

        # Referee
        self._referee_endpoint: str | None = None

        # MCP client for communicating with referees
        self._client: MCPClient | None = None

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
            },
        )
        async def register_player(params: dict) -> dict:
            return await self._handle_registration(params)

        @self.tool(
            "get_standings",
            "Get current league standings",
        )
        async def get_standings(params: dict) -> dict:
            return self._get_standings()

        @self.tool(
            "get_schedule",
            "Get match schedule",
        )
        async def get_schedule(params: dict) -> dict:
            return self._get_schedule()

        @self.tool(
            "start_league",
            "Start the league competition",
        )
        async def start_league(params: dict) -> dict:
            return await self._start_league()

        @self.tool(
            "start_next_round",
            "Start the next round of matches",
        )
        async def start_next_round_tool(params: dict) -> dict:
            return await self.start_next_round()

        @self.tool(
            "run_all_rounds",
            "Run all remaining rounds automatically",
        )
        async def run_all_rounds_tool(params: dict) -> dict:
            return await self._run_all_rounds()

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
            },
        )
        async def report_match_result(params: dict) -> dict:
            return await self._handle_match_result(params)

        @self.tool(
            "get_players",
            "Get list of registered players",
        )
        async def get_players(params: dict) -> dict:
            return {"players": [p.to_dict() for p in self._players.values()]}

        @self.tool(
            "get_player_info",
            "Get info for a specific player",
            {
                "type": "object",
                "properties": {
                    "player_id": {"type": "string"},
                },
                "required": ["player_id"],
            },
        )
        async def get_player_info(params: dict) -> dict:
            player_id = params.get("player_id")
            player_id_str = str(player_id) if player_id is not None else ""
            player = self._players.get(player_id_str)
            if not player:
                return {"error": f"Player {player_id} not found"}
            return {"player": player.to_dict()}

        @self.tool(
            "get_round_status",
            "Get current round status",
        )
        async def get_round_status(params: dict) -> dict:
            return {
                "league_id": self.league_id,
                "state": self.state.value,
                "current_round": self.current_round,
                "total_rounds": len(self._schedule),
                "rounds_completed": self.current_round - 1 if self.current_round > 0 else 0,
                "current_round_matches": len(self._current_round_matches),
                "matches_completed": sum(
                    1 for m in self._current_round_matches if m.state == MatchState.COMPLETED
                ),
            }

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
            },
        )
        async def register_referee(params: dict) -> dict:
            return await self._handle_referee_registration(params)

        @self.tool(
            "get_referees",
            "Get list of registered referees",
        )
        async def get_referees(params: dict) -> dict:
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
            },
        )
        async def set_referee(params: dict) -> dict:
            self._referee_endpoint = params.get("endpoint")
            return {"success": True, "referee_endpoint": self._referee_endpoint}

    def _register_resources(self) -> None:
        """Register league manager resources."""

        @self.resource(
            "league://standings",
            "League Standings",
            "Current league standings and rankings",
        )
        async def standings_resource(params: dict) -> dict:
            return self._get_standings()

        @self.resource(
            "league://players",
            "Registered Players",
            "List of all registered players",
        )
        async def players_resource(params: dict) -> dict:
            return {"players": [p.to_dict() for p in self._players.values()]}

        @self.resource(
            "league://schedule",
            "Match Schedule",
            "Complete match schedule",
        )
        async def schedule_resource(params: dict) -> dict:
            return self._get_schedule()

    async def on_start(self) -> None:
        """Initialize League Manager - create MCP client for referee communication."""
        self._client = MCPClient(f"{self.name}_client")
        await self._client.start()
        logger.info("League Manager MCP client started")

    async def on_stop(self) -> None:
        """Cleanup League Manager."""
        if self._client:
            await self._client.stop()
        logger.info("League Manager stopped")

    async def _handle_referee_registration(self, params: dict) -> dict:
        """Handle referee registration."""
        referee_id = params.get("referee_id", "")
        endpoint = params.get("endpoint", "")
        display_name = params.get("display_name", f"Referee_{referee_id}")
        version = params.get("version", "1.0.0")
        game_types = params.get("game_types", ["even_odd"])
        max_concurrent_matches = params.get("max_concurrent_matches", 2)

        # Allow referee registration during REGISTRATION, READY, or IN_PROGRESS states
        # (Referees are essential for running matches)
        if self.state == LeagueState.COMPLETED:
            return self.message_factory.referee_register_response(
                status=RegistrationStatus.REJECTED.value,
                referee_id="",
                reason="League has completed",
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
            display_name=display_name,
            auth_token=auth_token,
            version=version,
            game_types=game_types,
            max_concurrent_matches=max_concurrent_matches,
        )

        self._referees[referee_id] = referee

        logger.info(
            f"Referee registered: {referee_id} ({display_name})",
            endpoint=endpoint,
            game_types=game_types,
            max_concurrent_matches=max_concurrent_matches,
        )

        return self.message_factory.referee_register_response(
            status=RegistrationStatus.ACCEPTED.value,
            referee_id=referee_id,
            auth_token=auth_token,
            league_id=self.league_id,
        )

    async def _handle_registration(self, params: dict) -> dict:
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

        # Emit agent registered event
        try:
            event_bus = get_event_bus()
            await event_bus.emit(
                "agent.registered",
                AgentRegisteredEvent(
                    agent_id=player_id,
                    agent_type="player",
                    agent_name=display_name,
                    source="league_manager",
                ),
            )
        except Exception as e:
            logger.error(f"Failed to emit AgentRegisteredEvent: {e}")

        return self.message_factory.register_response(
            status=RegistrationStatus.ACCEPTED.value,
            player_id=player_id,
            auth_token=auth_token,
        )

    async def _start_league(self) -> dict[str, Any]:
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
            "League ready to start",
            players=len(self._players),
            rounds=len(self._schedule),
        )

        return {
            "success": True,
            "players": len(self._players),
            "rounds": len(self._schedule),
            "schedule": self._get_schedule(),
        }

    def _assign_referee_to_match(self, match_index: int) -> str | None:
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

    async def start_next_round(self) -> dict[str, Any]:
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
            return {
                "success": False,
                "error": "No referees registered. Register referees first (Step 1).",
            }

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
            referee_endpoint = self._referees[referee_id].endpoint if referee_id else None

            # Store match
            self._matches[match.match_id] = match

            # Prepare match info for announcement
            round_matches_info.append(
                {
                    "match_id": match.match_id,
                    "game_type": "even_odd",
                    "player_A_id": match.player1.player_id if match.player1 else "",
                    "player_B_id": match.player2.player_id if match.player2 else "",
                    "referee_endpoint": referee_endpoint,
                    # Also include detailed info for internal use
                    "_player_A_endpoint": match.player1.endpoint if match.player1 else "",
                    "_player_B_endpoint": match.player2.endpoint if match.player2 else "",
                    "_player_A_name": match.player1.display_name if match.player1 else "",
                    "_player_B_name": match.player2.display_name if match.player2 else "",
                }
            )

        logger.info(
            f"Round {self.current_round} announced",
            matches=len(self._current_round_matches),
            referees_assigned=len([m for m in round_matches_info if m["referee_endpoint"]]),
        )

        # Emit tournament round started event
        try:
            event_bus = get_event_bus()
            await event_bus.emit(
                "tournament.round.started",
                TournamentRoundStartedEvent(
                    round_number=self.current_round,
                    total_rounds=len(self._schedule),
                    matches=[str(m["match_id"]) for m in round_matches_info if m.get("match_id")],
                    source="league_manager",
                ),
            )
        except Exception as e:
            logger.error(f"Failed to emit TournamentRoundStartedEvent: {e}")

        # Create ROUND_ANNOUNCEMENT message
        announcement = self.message_factory.round_announcement(
            round_id=self.current_round,
            matches=round_matches_info,
        )

        # Execute matches through referee (Step 5: Game Management)
        import asyncio

        for match_info in round_matches_info:
            await self._send_match_to_referee(match_info)

        # Wait for matches to complete
        await asyncio.sleep(2)

        return {
            "success": True,
            "round": self.current_round,
            "announcement": announcement,
            "matches": round_matches_info,
        }

    async def _run_all_rounds(self) -> dict[str, Any]:
        """
        Run all remaining rounds automatically.

        This orchestrates the full league competition by:
        1. Starting each round
        2. Sending match assignments to referee
        3. Waiting for match completion
        4. Moving to next round
        """
        import asyncio

        results = []
        rounds_completed = 0

        while self.current_round < len(self._schedule):
            # Start next round
            round_result = await self.start_next_round()

            if not round_result.get("success"):
                if round_result.get("league_complete"):
                    break
                return {
                    "success": False,
                    "error": f"Failed to start round: {round_result.get('error')}",
                    "rounds_completed": rounds_completed,
                }

            # Execute matches through referee
            matches = round_result.get("matches", [])
            for match_info in matches:
                await self._send_match_to_referee(match_info)

            # Wait for matches to complete (simple timeout-based approach)
            await asyncio.sleep(2)

            rounds_completed += 1
            results.append(
                {
                    "round": round_result.get("round"),
                    "matches": len(matches),
                }
            )

        self.state = LeagueState.COMPLETED

        # Get final standings
        final_standings = self._get_standings()

        # Determine champion (rank 1)
        champion = None
        simplified_standings = []
        for standing in final_standings["standings"]:
            simplified_standings.append(
                {
                    "rank": standing["rank"],
                    "player_id": standing["player_id"],
                    "points": standing["points"],
                }
            )
            if standing["rank"] == 1:
                champion = {
                    "player_id": standing["player_id"],
                    "display_name": standing["display_name"],
                    "points": standing["points"],
                }

        # Calculate total matches
        total_matches = sum(len(r) for r in self._schedule)

        # Create LEAGUE_COMPLETED message
        league_completed_message = self.message_factory.league_completed(
            total_rounds=len(self._schedule),
            total_matches=total_matches,
            champion=champion or {"player_id": "unknown", "display_name": "Unknown", "points": 0},
            final_standings=simplified_standings,
        )

        logger.info(
            "League completed",
            total_rounds=len(self._schedule),
            total_matches=total_matches,
            champion=champion,
        )

        return {
            "success": True,
            "rounds_completed": rounds_completed,
            "total_rounds": len(self._schedule),
            "total_matches": total_matches,
            "results": results,
            "standings": final_standings,
            "champion": champion,
            "league_completed_message": league_completed_message,
        }

    async def _send_match_to_referee(self, match_info: dict) -> None:
        """Send match assignment to referee."""
        referee_endpoint = match_info.get("referee_endpoint")
        if not referee_endpoint:
            logger.warning(f"No referee assigned for match {match_info.get('match_id')}")
            return

        # Get player IDs from match info
        player_a_id = match_info.get("player_A_id")
        player_b_id = match_info.get("player_B_id")

        try:
            if self._client is None:
                logger.error("MCP client not initialized")
                return

            # Use MCP client to call referee's start_match tool
            await self._client.connect("referee", referee_endpoint)

            player_a_id_str = str(player_a_id) if player_a_id is not None else ""
            player_b_id_str = str(player_b_id) if player_b_id is not None else ""

            await self._client.call_tool(
                "referee",
                "start_match",
                {
                    "match_id": match_info.get("match_id"),
                    "player1_id": player_a_id_str,
                    "player1_endpoint": self._players[player_a_id_str].endpoint,
                    "player2_id": player_b_id_str,
                    "player2_endpoint": self._players[player_b_id_str].endpoint,
                    "rounds": 5,
                },
            )

            logger.info(
                "Match sent to referee",
                match_id=match_info.get("match_id"),
                referee_endpoint=referee_endpoint,
            )

        except Exception as e:
            logger.error(f"Failed to send match to referee: {e}")

    async def _handle_match_result(self, params: dict) -> dict[str, Any]:
        """Handle match result from referee."""
        match_id = params.get("match_id")
        match_id_str = str(match_id) if match_id is not None else ""
        winner_id = params.get("winner_id")
        player1_score = params.get("player1_score", 0)
        player2_score = params.get("player2_score", 0)

        match = self._matches.get(match_id_str)
        if not match:
            return {"success": False, "error": f"Unknown match: {match_id}"}

        # Update standings
        if winner_id:
            if winner_id in self._players:
                self._players[winner_id].record_win()

            # Record loss for other player
            player1_id = match.player1.player_id if match.player1 else ""
            player2_id = match.player2.player_id if match.player2 else ""
            loser_id = player1_id if winner_id == player2_id else player2_id
            if loser_id in self._players:
                self._players[loser_id].record_loss()
        else:
            # Draw
            player1_id = match.player1.player_id if match.player1 else ""
            player2_id = match.player2.player_id if match.player2 else ""
            if player1_id in self._players:
                self._players[player1_id].record_draw()
            if player2_id in self._players:
                self._players[player2_id].record_draw()

        # Update match state
        match.state = MatchState.COMPLETED
        match.winner_id = winner_id
        player1_id = match.player1.player_id if match.player1 else ""
        player2_id = match.player2.player_id if match.player2 else ""
        match.final_score = {
            player1_id: player1_score,
            player2_id: player2_score,
        }

        logger.info(
            "Match result recorded",
            match_id=match_id,
            winner=winner_id,
            score=f"{player1_score}-{player2_score}",
        )

        # Check if round complete
        round_complete = all(m.state == MatchState.COMPLETED for m in self._current_round_matches)

        # Step 6: If round complete, publish standings to all players
        standings = self._get_standings()
        standings_message = None
        if round_complete:
            standings_message = await self._publish_standings_update()

        # Emit standings updated event
        try:
            event_bus = get_event_bus()
            await event_bus.emit(
                "standings.updated",
                StandingsUpdatedEvent(
                    standings=standings.get("standings", []),
                    round_number=self.current_round,
                    source="league_manager",
                ),
            )
        except Exception as e:
            logger.error(f"Failed to emit StandingsUpdatedEvent: {e}")

        return {
            "success": True,
            "round_complete": round_complete,
            "standings": standings,
            "standings_published": standings_message is not None,
        }

    async def _publish_standings_update(self) -> dict[str, Any]:
        """
        Step 6: Publish standings update to all players after round completion.

        Creates LEAGUE_STANDINGS_UPDATE and ROUND_COMPLETED messages.
        """
        standings = self._get_standings()

        # Create LEAGUE_STANDINGS_UPDATE message
        standings_message = self.message_factory.standings_update(
            round_id=self.current_round,
            standings=standings["standings"],
        )

        # Determine next round
        next_round_id = None
        if self.current_round < len(self._schedule):
            next_round_id = self.current_round + 1

        # Create ROUND_COMPLETED message
        round_completed_message = self.message_factory.round_completed(
            round_id=self.current_round,
            matches_played=len(self._current_round_matches),
            next_round_id=next_round_id,
        )

        logger.info(
            "Publishing standings update and round completed",
            round_id=self.current_round,
            matches_played=len(self._current_round_matches),
            next_round_id=next_round_id,
            total_players=len(self._players),
        )

        # Note: In a full implementation, this would broadcast to all players
        # via their registered endpoints. For now, we return the message
        # for the caller to handle distribution.

        return {
            "standings_update": standings_message,
            "round_completed": round_completed_message,
        }

    def _get_standings(self) -> dict[str, Any]:
        """Get current standings."""
        # Sort by points, then wins, then goal difference
        sorted_players = sorted(
            self._players.values(), key=lambda p: (p.points, p.wins, -p.losses), reverse=True
        )

        # Build standings
        standings = []
        for i, p in enumerate(sorted_players):
            standings.append(
                {
                    "rank": i + 1,
                    "player_id": p.player_id,
                    "display_name": p.display_name,
                    "played": p.played,
                    "wins": p.wins,
                    "draws": p.draws,
                    "losses": p.losses,
                    "points": p.points,
                }
            )

        return {
            "round_id": self.current_round,
            "total_rounds": len(self._schedule),
            "standings": standings,
        }

    def _get_schedule(self) -> dict[str, Any]:
        """Get match schedule."""
        schedule = []

        for round_num, pairings in enumerate(self._schedule, 1):
            round_matches = []
            for p1, p2 in pairings:
                p1_name = self._players[p1].display_name if p1 in self._players else p1
                p2_name = self._players[p2].display_name if p2 in self._players else p2
                round_matches.append(
                    {
                        "player1": {"id": p1, "name": p1_name},
                        "player2": {"id": p2, "name": p2_name},
                    }
                )
            schedule.append(
                {
                    "round": round_num,
                    "matches": round_matches,
                    "status": "completed"
                    if round_num < self.current_round
                    else "in_progress"
                    if round_num == self.current_round
                    else "scheduled",
                }
            )

        return {"schedule": schedule}

    # ========================================================================
    # Protocol Message Handlers
    # ========================================================================

    async def _handle_league_register_request(self, message: dict) -> dict:
        """Handle LEAGUE_REGISTER_REQUEST message."""
        player_meta = message.get("player_meta", {})

        result = await self._handle_registration(
            {
                "display_name": player_meta.get("display_name", ""),
                "endpoint": player_meta.get("contact_endpoint", ""),
                "version": player_meta.get("version", "1.0.0"),
                "game_types": player_meta.get("game_types", []),
            }
        )

        return result

    @property
    def player_count(self) -> int:
        """Get number of registered players."""
        return len(self._players)

    @property
    def is_registration_open(self) -> bool:
        """Check if registration is open."""
        return self.state == LeagueState.REGISTRATION
