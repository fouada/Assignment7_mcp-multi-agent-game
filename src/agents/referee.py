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
    """Referee state matching game states."""
    
    IDLE = "idle"
    WAITING_FOR_PLAYERS = "waiting_for_players"
    COLLECTING_CHOICES = "collecting_choices"
    DRAWING_NUMBER = "drawing_number"
    FINISHED = "finished"


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
        
        @self.tool(
            "get_match_state",
            "Get current match state for debugging",
            {
                "type": "object",
                "properties": {
                    "match_id": {"type": "string"},
                },
                "required": ["match_id"],
            }
        )
        async def get_match_state(params: Dict) -> Dict:
            """Get match state including game details."""
            match_id = params.get("match_id")
            
            # Find session by match_id
            for session in self._sessions.values():
                if session.match.match_id == match_id:
                    game = session.game
                    return {
                        "match_id": match_id,
                        "game_id": game.game_id,
                        "state": session.state,
                        "game_phase": game.phase.value if hasattr(game.phase, 'value') else str(game.phase),
                        "current_round": game.current_round,
                        "total_rounds": game.total_rounds,
                        "is_complete": game.is_complete,
                        "player1": {
                            "id": game.player1_id,
                            "role": game.player1_role.value if game.player1_role else None,
                            "score": game.player1_score,
                        },
                        "player2": {
                            "id": game.player2_id,
                            "role": game.player2_role.value if game.player2_role else None,
                            "score": game.player2_score,
                        },
                        "round_history": [r.to_dict() for r in game.history] if hasattr(game, 'history') else [],
                    }
            
            return {"error": f"Match {match_id} not found", "active_matches": list(self._sessions.keys())}
    
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
                    "display_name": f"Referee_{self.referee_id}",
                    "version": "1.0.0",
                    "game_types": ["even_odd"],
                    "max_concurrent_matches": 2,
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
        
        # Send invitations and run the full game
        await self._run_full_game(session)
        
        return {
            "success": True,
            "match_id": match_id,
            "game_id": game.game_id,
            "state": "complete",
            "result": session.match.get_result() if session.match.state.value == "complete" else None,
        }
    
    async def _run_full_game(self, session: GameSession) -> None:
        """Run the complete game flow: invitations → rounds → result."""
        # Step 1: Send invitations and collect acceptances
        both_accepted = await self._send_game_invitations(session)
        
        if not both_accepted:
            logger.error(f"Not all players accepted game {session.game.game_id}")
            session.state = "cancelled"
            return
        
        # Step 2: Start the game (match.start() internally calls game.start())
        session.match.start()
        session.state = "running"
        logger.info(f"Game started: {session.game.game_id}")
        
        # Step 3: Run all rounds
        while not session.game.is_complete:
            await self._run_round(session)
        
        # Step 4: Complete the game
        await self._complete_game(session)
    
    async def _send_game_invitations(self, session: GameSession) -> bool:
        """Send game invitations to both players and return True if both accept."""
        match = session.match
        game = session.game
        accepted_count = 0
        
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
                
                # Send invitation and wait for response
                response = await self._client.send_protocol_message(player_id, invite)
                logger.debug(f"Invitation response from {player_id}: {response}")
                
                # Check acceptance
                if response.get("success") and response.get("accepted", True):
                    match.mark_player_ready(player_id)
                    accepted_count += 1
                
            except Exception as e:
                logger.error(f"Failed to send invitation to {player_id}: {e}")
        
        session.state = "both_accepted" if accepted_count == 2 else "waiting_for_acceptance"
        return accepted_count == 2
    
    async def _run_round(self, session: GameSession) -> None:
        """
        Run a single round of the game.
        
        Uses CHOOSE_PARITY_CALL to request player choices.
        """
        game = session.game
        match = session.match
        moves = {}
        
        # Calculate deadline (30 seconds from now)
        from datetime import datetime, timedelta
        deadline = (datetime.utcnow() + timedelta(seconds=self.move_timeout)).isoformat() + "Z"
        
        # Request parity choices from both players
        for player_id in [game.player1_id, game.player2_id]:
            opponent_id = game.get_opponent_id(player_id)
            
            # Build CHOOSE_PARITY_CALL message
            parity_call = self.message_factory.choose_parity_call(
                match_id=match.match_id,
                player_id=player_id,
                game_type="even_odd",
                opponent_id=opponent_id,
                round_id=game.current_round,
                your_standings={
                    "wins": game.get_player_score(player_id),
                    "losses": game.get_opponent_score(player_id),
                    "draws": 0,  # Track draws if needed
                },
                deadline=deadline,
            )
            
            try:
                if player_id in self._client.connected_servers:
                    response = await self._client.send_protocol_message(player_id, parity_call)
                    # CHOOSE_PARITY_RESPONSE contains parity_choice (the move number)
                    move = response.get("parity_choice") or response.get("move")
                    if move is not None:
                        moves[player_id] = int(move)
                        logger.debug(f"Received parity choice from {player_id}: {move}")
            except Exception as e:
                logger.error(f"Failed to get parity choice from {player_id}: {e}")
                # Default move on error
                moves[player_id] = 3
        
        # Play the round
        if game.player1_id in moves and game.player2_id in moves:
            # Submit both moves
            game.submit_move(game.player1_id, moves[game.player1_id])
            game.submit_move(game.player2_id, moves[game.player2_id])
            
            # Resolve the round
            round_result = game.resolve_round()
            
            logger.info(
                f"Round {round_result.round_number}: "
                f"P1={round_result.player1_move} P2={round_result.player2_move} "
                f"Sum={round_result.sum_value} Winner={round_result.winner_id or 'draw'}"
            )
            
            # Send round results to players
            await self._send_round_results(session, round_result)
    
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
        """
        Complete the game and report results.
        
        Step 5.5: Send GAME_OVER to both players
        Step 5.6: Send MATCH_RESULT_REPORT to league manager
        """
        game = session.game
        match = session.match
        game_result = game.get_result()
        
        session.state = "complete"
        match.complete(game_result)
        
        # Calculate final drawn_number (sum of last round's moves or total score)
        last_round = game_result.rounds[-1] if game_result.rounds else None
        drawn_number = last_round.sum_value if last_round else 0
        number_parity = "even" if drawn_number % 2 == 0 else "odd"
        
        # Build choices map (each player's role)
        choices = {
            game.player1_id: game.player1_role.value,  # "odd" or "even"
            game.player2_id: game.player2_role.value,
        }
        
        # Determine status and reason
        if game_result.winner_id:
            status = "WIN"
            winner_role = choices.get(game_result.winner_id, "unknown")
            reason = f"{game_result.winner_id} chose {winner_role}, number was {drawn_number} ({number_parity})"
        else:
            status = "DRAW"
            reason = "Game ended in a draw"
        
        logger.info(
            f"Game completed",
            game_id=game.game_id,
            winner=game_result.winner_id,
            score=f"{game_result.player1_score}-{game_result.player2_score}",
            drawn_number=drawn_number,
        )
        
        # Step 5.5: Send GAME_OVER to both players
        for player_id in [game.player1_id, game.player2_id]:
            game_over_msg = self.message_factory.game_over(
                match_id=match.match_id,
                game_type="even_odd",
                status=status,
                winner_player_id=game_result.winner_id,
                drawn_number=drawn_number,
                number_parity=number_parity,
                choices=choices,
                reason=reason,
            )
            
            try:
                if player_id in self._client.connected_servers:
                    await self._client.send_protocol_message(player_id, game_over_msg)
            except Exception as e:
                logger.error(f"Failed to send GAME_OVER to {player_id}: {e}")
        
        # Step 5.6: Report to league manager
        await self._report_to_league(session, game_result, drawn_number, choices)
    
    async def _report_to_league(
        self,
        session: GameSession,
        result: GameResult,
        drawn_number: int = 0,
        choices: Dict[str, str] = None,
    ) -> None:
        """
        Report game result to league manager.
        
        Args:
            session: Game session
            result: Game result
            drawn_number: The final drawn number (sum)
            choices: Map of player_id to their parity choice
        """
        try:
            # Connect to league manager if not connected
            if "league_manager" not in self._client.connected_servers:
                await self._client.connect("league_manager", self.league_manager_url)
            
            # Build details
            details = {
                "drawn_number": drawn_number,
                "choices": choices or {},
            }
            
            # Call report tool with  format
            await self._client.call_tool(
                server_name="league_manager",
                tool_name="report_match_result",
                arguments={
                    "match_id": session.match.match_id,
                    "winner_id": result.winner_id,
                    "player1_score": result.player1_score,
                    "player2_score": result.player2_score,
                    "details": details,  # includes drawn_number and choices
                },
            )
            
            logger.info(
                f"Reported result to league manager",
                match_id=session.match.match_id,
                winner=result.winner_id,
                drawn_number=drawn_number,
            )
            
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
    
    async def _handle_choose_parity_response(self, message: Dict) -> Dict:
        """
        Handle CHOOSE_PARITY_RESPONSE message.
        
        The response contains:
        - parity_choice: "even" or "odd" (player's role confirmation)
        - move: the actual number choice (1-10)
        """
        match_id = message.get("match_id")
        player_id = message.get("player_id", "").replace("player:", "")
        parity_choice = message.get("parity_choice")  # "even" or "odd"
        move = message.get("move")  # Actual number move
        
        # Find the game session by match_id
        session = None
        game_id = None
        for gid, s in self._sessions.items():
            if s.match.match_id == match_id:
                session = s
                game_id = gid
                break
        
        if not session:
            return {"success": False, "error": f"Unknown match: {match_id}"}
        
        # Extract move value
        if move is not None:
            try:
                move_value = int(move)
            except (TypeError, ValueError):
                move_value = 3  # Default
        else:
            # Fallback: try parsing parity_choice as number (backward compat)
            try:
                move_value = int(parity_choice)
            except (TypeError, ValueError):
                move_value = 3  # Default
        
        logger.debug(f"Player {player_id} chose parity '{parity_choice}' with move {move_value}")
        
        return await self._handle_move_submission({
            "game_id": game_id,
            "player_id": player_id,
            "move": move_value,
        })

