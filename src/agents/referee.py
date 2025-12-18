"""
Referee Agent
=============

Manages individual games:
- Send invitations to players
- Coordinate handshake
- Collect and validate moves
- Declare results
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from ..server.base_server import BaseGameServer
from ..client.mcp_client import MCPClient
from ..game.odd_even import OddEvenGame, GameRole, GameResult
from ..game.match import Match, MatchState
from ..common.logger import get_logger
from ..common.protocol import (
    MessageType,
    MessageFactory,
    GameStatus,
    PROTOCOL_VERSION,
)
from ..common.exceptions import TimeoutError, GameError

logger = get_logger(__name__)


class RefereeState(Enum):
    """Referee state."""
    
    IDLE = "idle"
    PREPARING_MATCH = "preparing_match"
    WAITING_FOR_PLAYERS = "waiting_for_players"
    RUNNING_GAME = "running_game"
    GAME_COMPLETE = "game_complete"


@dataclass
class GameSession:
    """Active game session."""
    
    match: Match
    game: OddEvenGame
    state: str = "waiting"
    pending_moves: Dict[str, int] = field(default_factory=dict)
    move_timeout: float = 30.0
    created_at: datetime = field(default_factory=datetime.utcnow)


class RefereeAgent(BaseGameServer):
    """
    Referee Agent.
    
    Runs as MCP server and manages individual games:
    - Invites players to games
    - Manages game rounds
    - Validates moves
    - Reports results to league manager
    """
    
    def __init__(
        self,
        referee_id: str = "REF01",  # Referee identifier (REF01, REF02, etc.)
        league_id: str = "league_2024_01",
        host: str = "localhost",
        port: int = 8001,
        move_timeout: float = 30.0,
        league_manager_url: Optional[str] = None,
    ):
        self.referee_id = referee_id
        super().__init__(
            name=referee_id,  # Use referee_id as name for sender format "referee:REF01"
            server_type="referee",
            league_id=league_id,
            host=host,
            port=port,
        )
        
        self.move_timeout = move_timeout
        self.league_manager_url = league_manager_url or "http://localhost:8000/mcp"
        
        # Registration state
        self.auth_token: Optional[str] = None
        self.registered = False
        
        # State
        self.state = RefereeState.IDLE
        
        # Active games
        self._sessions: Dict[str, GameSession] = {}
        self._player_connections: Dict[str, str] = {}  # player_id -> endpoint
        
        # MCP client for communicating with players
        self._client: Optional[MCPClient] = None
        
        # Register tools
        self._register_tools()
        
        # Register resources
        self._register_resources()
    
    def _register_tools(self) -> None:
        """Register referee tools."""
        
        @self.tool(
            "start_match",
            "Start a match between two players",
            {
                "type": "object",
                "properties": {
                    "match_id": {"type": "string"},
                    "player1_id": {"type": "string"},
                    "player1_endpoint": {"type": "string"},
                    "player2_id": {"type": "string"},
                    "player2_endpoint": {"type": "string"},
                    "rounds": {"type": "integer"},
                },
                "required": ["match_id", "player1_id", "player2_id"],
            }
        )
        async def start_match(params: Dict) -> Dict:
            return await self._start_match(params)
        
        @self.tool(
            "submit_move",
            "Submit a move from a player",
            {
                "type": "object",
                "properties": {
                    "game_id": {"type": "string"},
                    "player_id": {"type": "string"},
                    "move": {"type": "integer"},
                },
                "required": ["game_id", "player_id", "move"],
            }
        )
        async def submit_move(params: Dict) -> Dict:
            return await self._handle_move_submission(params)
        
        @self.tool(
            "get_game_state",
            "Get current state of a game",
            {
                "type": "object",
                "properties": {
                    "game_id": {"type": "string"},
                },
                "required": ["game_id"],
            }
        )
        async def get_game_state(params: Dict) -> Dict:
            return self._get_game_state(params.get("game_id"))
        
        @self.tool(
            "list_active_games",
            "List all active games",
        )
        async def list_active_games(params: Dict) -> Dict:
            return {
                "games": [
                    {
                        "game_id": session.game.game_id,
                        "match_id": session.match.match_id,
                        "state": session.state,
                        "round": session.game.current_round,
                    }
                    for session in self._sessions.values()
                ]
            }
    
    def _register_resources(self) -> None:
        """Register referee resources."""
        
        @self.resource(
            "game://state/{game_id}",
            "Game State",
            "Current state of a specific game",
        )
        async def game_state_resource(params: Dict) -> Dict:
            game_id = params.get("game_id")
            return self._get_game_state(game_id)
    
    async def on_start(self) -> None:
        """Initialize referee."""
        self._client = MCPClient(name=f"{self.referee_id}_client")
        await self._client.start()
        logger.info(f"Referee agent {self.referee_id} started")
    
    async def register_with_league(self) -> bool:
        """
        Register with the league manager (Step 1 of league flow).
        
        Returns:
            True if registration successful, False otherwise
        """
        try:
            # Connect to league manager
            await self._client.connect("league_manager", self.league_manager_url)
            
            # Call registration tool
            response = await self._client.call_tool(
                server_name="league_manager",
                tool_name="register_referee",
                arguments={
                    "referee_id": self.referee_id,
                    "endpoint": self.url,
                    "version": "1.0.0",
                },
            )
            
            # Parse response
            result = response.get("content", [{}])[0]
            if isinstance(result, dict):
                text = result.get("text", "{}")
                import json
                data = json.loads(text)
            else:
                data = response
            
            if data.get("status") == "ACCEPTED":
                self.auth_token = data.get("auth_token")
                self.registered = True
                
                # Update message factory with auth token
                if self.auth_token:
                    self.message_factory.set_auth_token(self.auth_token)
                
                logger.info(f"Referee {self.referee_id} registered with league")
                return True
            else:
                logger.error(f"Referee registration rejected: {data.get('reason')}")
                return False
                
        except Exception as e:
            logger.error(f"Referee registration failed: {e}")
            return False
    
    async def on_stop(self) -> None:
        """Cleanup referee."""
        if self._client:
            await self._client.stop()
        logger.info("Referee agent stopped")
    
    async def _start_match(self, params: Dict) -> Dict[str, Any]:
        """Start a new match."""
        match_id = params.get("match_id")
        player1_id = params.get("player1_id")
        player1_endpoint = params.get("player1_endpoint")
        player2_id = params.get("player2_id")
        player2_endpoint = params.get("player2_endpoint")
        rounds = params.get("rounds", 5)
        
        # Create match
        match = Match(
            match_id=match_id,
            league_id=self.league_id,
        )
        match.set_players(
            player1_id=player1_id,
            player1_endpoint=player1_endpoint,
            player2_id=player2_id,
            player2_endpoint=player2_endpoint,
        )
        
        # Create game
        game = match.create_game(
            total_rounds=rounds,
            player1_role=GameRole.ODD,
        )
        
        # Create session
        session = GameSession(
            match=match,
            game=game,
            move_timeout=self.move_timeout,
        )
        self._sessions[game.game_id] = session
        
        # Store player connections
        self._player_connections[player1_id] = player1_endpoint
        self._player_connections[player2_id] = player2_endpoint
        
        logger.info(
            f"Match created",
            match_id=match_id,
            game_id=game.game_id,
            player1=player1_id,
            player2=player2_id,
        )
        
        # Send invitations to players
        await self._send_game_invitations(session)
        
        return {
            "success": True,
            "match_id": match_id,
            "game_id": game.game_id,
            "state": "invitations_sent",
        }
    
    async def _send_game_invitations(self, session: GameSession) -> None:
        """Send game invitations to both players."""
        match = session.match
        game = session.game
        
        for player_id in [game.player1_id, game.player2_id]:
            endpoint = self._player_connections.get(player_id)
            if not endpoint:
                continue
            
            opponent_id = game.get_opponent_id(player_id)
            role = game.get_player_role(player_id)
            
            invite = self.message_factory.game_invite(
                game_id=game.game_id,
                opponent_id=opponent_id,
                role=role.value,
                rounds=game.total_rounds,
                match_id=match.match_id,
            )
            
            try:
                # Connect to player if not already connected
                if player_id not in self._client.connected_servers:
                    await self._client.connect(player_id, endpoint)
                
                # Send invitation
                await self._client.send_protocol_message(player_id, invite)
                logger.debug(f"Sent game invitation to {player_id}")
                
            except Exception as e:
                logger.error(f"Failed to send invitation to {player_id}: {e}")
        
        session.state = "waiting_for_acceptance"
    
    async def handle_game_acceptance(
        self,
        game_id: str,
        player_id: str,
        accepted: bool,
    ) -> Dict[str, Any]:
        """Handle player's game acceptance."""
        session = self._sessions.get(game_id)
        if not session:
            return {"success": False, "error": "Unknown game"}
        
        if not accepted:
            # Cancel the game
            session.state = "cancelled"
            return {"success": True, "state": "cancelled"}
        
        # Mark player ready
        match = session.match
        both_ready = match.mark_player_ready(player_id)
        
        if both_ready:
            # Start the game
            await self._start_game(session)
        
        return {
            "success": True,
            "state": session.state,
            "both_ready": both_ready,
        }
    
    async def _start_game(self, session: GameSession) -> None:
        """Start the game and first round."""
        session.game.start()
        session.match.start()
        session.state = "awaiting_moves"
        
        logger.info(f"Game started: {session.game.game_id}")
        
        # Send game start to both players
        await self._request_moves(session)
    
    async def _request_moves(self, session: GameSession) -> None:
        """Request moves from both players."""
        game = session.game
        
        for player_id in [game.player1_id, game.player2_id]:
            role = game.get_player_role(player_id)
            
            move_request = self.message_factory.move_request(
                game_id=game.game_id,
                round_number=game.current_round,
                role=role.value,
                current_score={
                    game.player1_id: game.player1_score,
                    game.player2_id: game.player2_score,
                },
                time_limit=self.move_timeout,
            )
            
            try:
                if player_id in self._client.connected_servers:
                    await self._client.send_protocol_message(player_id, move_request)
                    logger.debug(f"Requested move from {player_id}")
            except Exception as e:
                logger.error(f"Failed to request move from {player_id}: {e}")
    
    async def _handle_move_submission(self, params: Dict) -> Dict[str, Any]:
        """Handle a move submission from a player."""
        game_id = params.get("game_id")
        player_id = params.get("player_id")
        move_value = params.get("move")
        
        session = self._sessions.get(game_id)
        if not session:
            return {"success": False, "error": "Unknown game"}
        
        if session.state != "awaiting_moves":
            return {"success": False, "error": f"Invalid state: {session.state}"}
        
        game = session.game
        
        try:
            # Submit move to game
            both_received = game.submit_move(player_id, move_value)
            
            logger.debug(f"Move received from {player_id}: {move_value}")
            
            if both_received:
                # Resolve the round
                result = await self._resolve_round(session)
                return {
                    "success": True,
                    "round_resolved": True,
                    "result": result.to_dict(),
                }
            
            return {
                "success": True,
                "round_resolved": False,
                "waiting_for": game.get_opponent_id(player_id),
            }
            
        except Exception as e:
            logger.error(f"Move submission error: {e}")
            return {"success": False, "error": str(e)}
    
    async def _resolve_round(self, session: GameSession) -> Any:
        """Resolve the current round."""
        game = session.game
        
        # Resolve round
        result = game.resolve_round()
        
        logger.info(
            f"Round {result.round_number} resolved",
            game_id=game.game_id,
            winner=result.winner_id,
            sum=result.sum_value,
        )
        
        # Send results to players
        await self._send_round_results(session, result)
        
        # Check if game is complete
        if game.is_complete:
            await self._complete_game(session)
        else:
            # Request next round moves
            session.state = "awaiting_moves"
            await self._request_moves(session)
        
        return result
    
    async def _send_round_results(self, session: GameSession, result) -> None:
        """Send round results to both players."""
        game = session.game
        
        for player_id in [game.player1_id, game.player2_id]:
            opponent_id = game.get_opponent_id(player_id)
            
            if player_id == game.player1_id:
                your_move = result.player1_move
                opponent_move = result.player2_move
                your_score = game.player1_score
                opponent_score = game.player2_score
            else:
                your_move = result.player2_move
                opponent_move = result.player1_move
                your_score = game.player2_score
                opponent_score = game.player1_score
            
            result_msg = self.message_factory.move_result(
                game_id=game.game_id,
                round_number=result.round_number,
                your_move=your_move,
                opponent_move=opponent_move,
                winner_id=result.winner_id,
                your_score=your_score,
                opponent_score=opponent_score,
            )
            
            try:
                if player_id in self._client.connected_servers:
                    await self._client.send_protocol_message(player_id, result_msg)
            except Exception as e:
                logger.error(f"Failed to send result to {player_id}: {e}")
    
    async def _complete_game(self, session: GameSession) -> None:
        """Complete the game and report results."""
        game = session.game
        game_result = game.get_result()
        
        session.state = "complete"
        session.match.complete(game_result)
        
        logger.info(
            f"Game completed",
            game_id=game.game_id,
            winner=game_result.winner_id,
            score=f"{game_result.player1_score}-{game_result.player2_score}",
        )
        
        # Send game end to players
        for player_id in [game.player1_id, game.player2_id]:
            end_msg = self.message_factory.game_end(
                game_id=game.game_id,
                winner_id=game_result.winner_id,
                final_score={
                    game.player1_id: game_result.player1_score,
                    game.player2_id: game_result.player2_score,
                },
            )
            
            try:
                if player_id in self._client.connected_servers:
                    await self._client.send_protocol_message(player_id, end_msg)
            except Exception as e:
                logger.error(f"Failed to send game end to {player_id}: {e}")
        
        # Report to league manager
        await self._report_to_league(session, game_result)
    
    async def _report_to_league(
        self,
        session: GameSession,
        result: GameResult,
    ) -> None:
        """Report game result to league manager."""
        try:
            # Connect to league manager if not connected
            if "league_manager" not in self._client.connected_servers:
                await self._client.connect("league_manager", self.league_manager_url)
            
            # Call report tool
            await self._client.call_tool(
                server_name="league_manager",
                tool_name="report_match_result",
                arguments={
                    "match_id": session.match.match_id,
                    "winner_id": result.winner_id,
                    "player1_score": result.player1_score,
                    "player2_score": result.player2_score,
                },
            )
            
            logger.info(f"Reported result to league manager")
            
        except Exception as e:
            logger.error(f"Failed to report to league manager: {e}")
    
    def _get_game_state(self, game_id: str) -> Dict[str, Any]:
        """Get game state."""
        session = self._sessions.get(game_id)
        if not session:
            return {"error": "Unknown game"}
        
        return {
            "game_id": game_id,
            "match_id": session.match.match_id,
            "session_state": session.state,
            "game_state": session.game.get_state(),
        }
    
    # ========================================================================
    # Protocol Message Handlers
    # ========================================================================
    
    async def _handle_game_invite_response(self, message: Dict) -> Dict:
        """Handle GAME_INVITE_RESPONSE message."""
        game_id = message.get("game_id")
        player_id = message.get("sender", "").replace("player:", "")
        accepted = message.get("accepted", False)
        
        return await self.handle_game_acceptance(game_id, player_id, accepted)
    
    async def _handle_move_response(self, message: Dict) -> Dict:
        """Handle MOVE_RESPONSE message."""
        game_id = message.get("game_id")
        player_id = message.get("sender", "").replace("player:", "")
        move = message.get("move")
        
        return await self._handle_move_submission({
            "game_id": game_id,
            "player_id": player_id,
            "move": move,
        })

