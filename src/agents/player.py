"""
Player Agent
============

AI player agent that:
- Registers with league
- Responds to game invitations
- Makes moves using strategy (LLM or algorithm)
- Tracks game state
"""

import asyncio
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any

from ..server.base_server import BaseGameServer
from ..client.mcp_client import MCPClient
from ..game.odd_even import GameRole
from ..common.logger import get_logger
from ..common.protocol import (
    MessageFactory,
    PROTOCOL_VERSION,
)
from ..common.config import LLMConfig

logger = get_logger(__name__)


# ============================================================================
# Strategy Interface
# ============================================================================

class Strategy(ABC):
    """Base class for player strategies."""
    
    @abstractmethod
    async def decide_move(
        self,
        game_id: str,
        round_number: int,
        my_role: GameRole,
        my_score: int,
        opponent_score: int,
        history: List[Dict],
    ) -> int:
        """
        Decide what move to make.
        
        Args:
            game_id: Current game ID
            round_number: Current round number
            my_role: My role (ODD or EVEN)
            my_score: My current score
            opponent_score: Opponent's current score
            history: History of previous rounds
            
        Returns:
            Move value (1-5)
        """
        pass


class RandomStrategy(Strategy):
    """Random strategy - picks random values."""
    
    def __init__(self, min_value: int = 1, max_value: int = 5):
        self.min_value = min_value
        self.max_value = max_value
    
    async def decide_move(
        self,
        game_id: str,
        round_number: int,
        my_role: GameRole,
        my_score: int,
        opponent_score: int,
        history: List[Dict],
    ) -> int:
        return random.randint(self.min_value, self.max_value)


class PatternStrategy(Strategy):
    """
    Pattern-based strategy.
    
    Analyzes opponent's patterns and tries to counter.
    """
    
    def __init__(self, min_value: int = 1, max_value: int = 5):
        self.min_value = min_value
        self.max_value = max_value
    
    async def decide_move(
        self,
        game_id: str,
        round_number: int,
        my_role: GameRole,
        my_score: int,
        opponent_score: int,
        history: List[Dict],
    ) -> int:
        if not history:
            return random.randint(self.min_value, self.max_value)
        
        # Analyze opponent's moves
        opponent_moves = [h.get("opponent_move", 3) for h in history]
        
        # Simple pattern: predict opponent will repeat recent average
        avg_opponent = sum(opponent_moves[-3:]) / min(len(opponent_moves), 3)
        
        # Choose move to counter
        if my_role == GameRole.ODD:
            # We want sum to be odd
            # If opponent likely plays X, we play something to make sum odd
            predicted_sum = avg_opponent + 3  # Our middle value
            if int(predicted_sum) % 2 == 0:
                # Sum would be even, adjust
                return random.choice([1, 3, 5])  # Odd values to shift parity
            else:
                return random.choice([2, 4])  # Even values
        else:
            # We want sum to be even
            predicted_sum = avg_opponent + 3
            if int(predicted_sum) % 2 == 1:
                # Sum would be odd, adjust
                return random.choice([1, 3, 5])
            else:
                return random.choice([2, 4])


class LLMStrategy(Strategy):
    """
    LLM-based strategy using Anthropic Claude or OpenAI.
    
    Uses an LLM to analyze the game and decide moves.
    Default: Anthropic Claude (claude-sonnet-4-20250514)
    """
    
    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        self._client = None
        logger.info(f"LLM Strategy initialized: {self.config.provider} / {self.config.model}")
    
    async def _get_client(self):
        """Get or create LLM client."""
        if self._client is not None:
            return self._client
        
        if not self.config.api_key:
            logger.warning(f"No API key for {self.config.provider}, falling back to random")
            return None
        
        if self.config.provider == "anthropic":
            try:
                import anthropic
                self._client = anthropic.AsyncAnthropic(api_key=self.config.api_key)
                logger.info("Anthropic Claude client initialized")
            except ImportError:
                logger.warning("Anthropic not installed. Install with: pip install anthropic")
                return None
        elif self.config.provider == "openai":
            try:
                import openai
                self._client = openai.AsyncOpenAI(api_key=self.config.api_key)
                logger.info("OpenAI client initialized")
            except ImportError:
                logger.warning("OpenAI not installed. Install with: pip install openai")
                return None
        
        return self._client
    
    async def decide_move(
        self,
        game_id: str,
        round_number: int,
        my_role: GameRole,
        my_score: int,
        opponent_score: int,
        history: List[Dict],
    ) -> int:
        client = await self._get_client()
        
        if client is None:
            # Fallback to random
            logger.debug("No LLM client, using random move")
            return random.randint(1, 5)
        
        # Build prompt
        prompt = self._build_prompt(
            round_number, my_role, my_score, opponent_score, history
        )
        
        try:
            if self.config.provider == "anthropic":
                # Anthropic Claude API
                response = await client.messages.create(
                    model=self.config.model,
                    max_tokens=10,
                    system="You are an expert game player. Respond with ONLY a single number from 1 to 5.",
                    messages=[
                        {"role": "user", "content": prompt},
                    ],
                )
                answer = response.content[0].text.strip()
                logger.debug(f"Claude response: {answer}")
            else:
                # OpenAI API
                response = await client.chat.completions.create(
                    model=self.config.model,
                    messages=[
                        {"role": "system", "content": "You are an expert game player. Respond with ONLY a single number from 1 to 5."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=self.config.temperature,
                    max_tokens=10,
                )
                answer = response.choices[0].message.content.strip()
                logger.debug(f"OpenAI response: {answer}")
            
            # Parse response - extract first digit found
            import re
            numbers = re.findall(r'[1-5]', answer)
            if numbers:
                move = int(numbers[0])
                logger.info(f"LLM decided move: {move}", game_id=game_id, round=round_number)
                return move
            
        except Exception as e:
            logger.warning(f"LLM decision failed: {e}")
        
        # Fallback
        logger.debug("LLM failed, using random fallback")
        return random.randint(1, 5)
    
    def _build_prompt(
        self,
        round_number: int,
        my_role: GameRole,
        my_score: int,
        opponent_score: int,
        history: List[Dict],
    ) -> str:
        """Build prompt for LLM."""
        role_explanation = (
            "You win when the sum of both numbers is ODD" if my_role == GameRole.ODD
            else "You win when the sum of both numbers is EVEN"
        )
        
        history_str = ""
        if history:
            history_str = "\nPrevious rounds:\n"
            for h in history[-5:]:  # Last 5 rounds
                history_str += f"  Round {h.get('round', '?')}: You played {h.get('my_move', '?')}, opponent played {h.get('opponent_move', '?')}, sum was {h.get('sum', '?')}\n"
        
        return f"""You are playing the Odd/Even game.

Rules:
- Both players choose a number from 1 to 5
- Numbers are revealed simultaneously
- The sum is calculated
- {role_explanation}

Current situation:
- Round: {round_number}
- Your role: {my_role.value.upper()}
- Your score: {my_score}
- Opponent score: {opponent_score}
{history_str}
Choose your move (a single number from 1 to 5). Consider:
1. Your role and what sum parity you need
2. Any patterns in opponent's moves
3. Game theory and mixed strategies

Reply with ONLY a number from 1 to 5:"""


# ============================================================================
# Player Agent
# ============================================================================

@dataclass
class GameSession:
    """Player's view of an active game (Section 8.7)."""
    
    game_id: str
    opponent_id: str
    my_role: GameRole
    total_rounds: int
    match_id: str = ""  # Added for Section 8.7.2 GAME_JOIN_ACK
    current_round: int = 0
    my_score: int = 0
    opponent_score: int = 0
    history: List[Dict] = field(default_factory=list)
    state: str = "invited"


class PlayerAgent(BaseGameServer):
    """
    AI Player Agent.
    
    Runs as MCP server and:
    - Registers with the league
    - Accepts game invitations
    - Makes moves using strategy
    - Tracks game state
    """
    
    def __init__(
        self,
        player_name: str,
        strategy: Optional[Strategy] = None,
        league_id: str = "league_2024_01",
        host: str = "localhost",
        port: int = 8101,
        league_manager_url: str = "http://localhost:8000/mcp",
    ):
        super().__init__(
            name=player_name,
            server_type="player",
            league_id=league_id,
            host=host,
            port=port,
        )
        
        self.player_name = player_name
        self.strategy = strategy or RandomStrategy()
        self.league_manager_url = league_manager_url
        
        # Player state
        self.player_id: Optional[str] = None
        self.auth_token: Optional[str] = None  # Token received after registration
        self.registered = False
        
        # Active games
        self._games: Dict[str, GameSession] = {}
        
        # MCP client
        self._client: Optional[MCPClient] = None
        
        # Update message factory sender
        self.message_factory = MessageFactory(
            sender=f"player:{player_name}",
            league_id=league_id,
        )
        
        # Register tools
        self._register_tools()
    
    def _register_tools(self) -> None:
        """Register player tools."""
        
        @self.tool(
            "get_status",
            "Get player status",
        )
        async def get_status(params: Dict) -> Dict:
            return {
                "player_name": self.player_name,
                "player_id": self.player_id,
                "registered": self.registered,
                "has_auth_token": self.auth_token is not None,
                "active_games": len(self._games),
            }
        
        @self.tool(
            "accept_game",
            "Accept a game invitation",
            {
                "type": "object",
                "properties": {
                    "game_id": {"type": "string"},
                    "accept": {"type": "boolean"},
                },
                "required": ["game_id"],
            }
        )
        async def accept_game(params: Dict) -> Dict:
            game_id = params.get("game_id")
            accept = params.get("accept", True)
            return await self._respond_to_invitation(game_id, accept)
        
        @self.tool(
            "get_game_state",
            "Get state of a game",
            {
                "type": "object",
                "properties": {
                    "game_id": {"type": "string"},
                },
                "required": ["game_id"],
            }
        )
        async def get_game_state(params: Dict) -> Dict:
            game_id = params.get("game_id")
            session = self._games.get(game_id)
            if not session:
                return {"error": "Unknown game"}
            return {
                "game_id": session.game_id,
                "opponent_id": session.opponent_id,
                "my_role": session.my_role.value,
                "round": session.current_round,
                "my_score": session.my_score,
                "opponent_score": session.opponent_score,
                "state": session.state,
            }
        
        @self.tool(
            "get_player_state",
            "Get player state including game history (Section 8.11.2)",
        )
        async def get_player_state(params: Dict) -> Dict:
            """Get comprehensive player state and history."""
            # Compile game history
            game_history = []
            for game_id, session in self._games.items():
                game_history.append({
                    "game_id": game_id,
                    "opponent_id": session.opponent_id,
                    "my_role": session.my_role.value if session.my_role else None,
                    "state": session.state,
                    "my_score": session.my_score,
                    "opponent_score": session.opponent_score,
                    "rounds_played": session.current_round,
                    "result": self._get_game_result(session),
                })
            
            # Get completed games summary
            wins = sum(1 for g in game_history if g["result"] == "win")
            losses = sum(1 for g in game_history if g["result"] == "loss")
            draws = sum(1 for g in game_history if g["result"] == "draw")
            
            return {
                "player_id": self.player_id,
                "player_name": self.player_name,
                "registered": self.registered,
                "league_id": self.league_id,
                "strategy": self.strategy.__class__.__name__,
                "statistics": {
                    "total_games": len(game_history),
                    "wins": wins,
                    "losses": losses,
                    "draws": draws,
                    "active_games": sum(1 for g in game_history if g["state"] not in ("complete", "finished")),
                },
                "game_history": game_history,
            }
        
        def _get_game_result(self, session: GameSession) -> Optional[str]:
            """Determine game result from session."""
            if session.state not in ("complete", "finished"):
                return None
            if session.my_score > session.opponent_score:
                return "win"
            elif session.my_score < session.opponent_score:
                return "loss"
            else:
                return "draw"
    
    async def on_start(self) -> None:
        """Initialize player."""
        self._client = MCPClient(name=f"{self.player_name}_client")
        await self._client.start()
        logger.info(f"Player agent {self.player_name} started")
    
    async def on_stop(self) -> None:
        """Cleanup player."""
        if self._client:
            await self._client.stop()
        logger.info(f"Player agent {self.player_name} stopped")
    
    async def register_with_league(self) -> bool:
        """Register with the league manager."""
        try:
            # Connect to league manager
            await self._client.connect("league_manager", self.league_manager_url)
            
            # Call registration tool
            response = await self._client.call_tool(
                server_name="league_manager",
                tool_name="register_player",
                arguments={
                    "display_name": self.player_name,
                    "endpoint": self.url,
                    "version": "1.0.0",
                    "game_types": ["even_odd"],
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
                self.player_id = data.get("player_id")
                self.auth_token = data.get("auth_token")
                self.registered = True
                
                # Update message factory with auth token for subsequent messages
                if self.auth_token:
                    self.message_factory.set_auth_token(self.auth_token)
                
                logger.info(f"Registered as {self.player_id} with auth token")
                return True
            else:
                logger.error(f"Registration rejected: {data.get('reason')}")
                return False
                
        except Exception as e:
            logger.error(f"Registration failed: {e}")
            return False
    
    async def _respond_to_invitation(
        self,
        game_id: str,
        accept: bool,
    ) -> Dict[str, Any]:
        """
        Respond to a game invitation (Section 8.7.2 - GAME_JOIN_ACK).
        
        Players must return GAME_JOIN_ACK within 5 seconds.
        """
        session = self._games.get(game_id)
        if not session:
            return {"success": False, "error": "Unknown game"}
        
        session.state = "accepted" if accept else "declined"
        
        # Send GAME_JOIN_ACK to referee (Section 8.7.2)
        # Use match_id if available, otherwise fallback to game_id
        match_id = session.match_id if session.match_id else game_id
        response_msg = self.message_factory.game_join_ack(
            match_id=match_id,
            player_id=self.player_id,
            accept=accept,
        )
        
        try:
            if "referee" in self._client.connected_servers:
                await self._client.send_protocol_message("referee", response_msg)
        except Exception as e:
            logger.error(f"Failed to send GAME_JOIN_ACK: {e}")
        
        return {"success": True, "accepted": accept}
    
    async def make_move(self, game_id: str) -> int:
        """Make a move in a game."""
        session = self._games.get(game_id)
        if not session:
            raise ValueError(f"Unknown game: {game_id}")
        
        # Use strategy to decide move
        move = await self.strategy.decide_move(
            game_id=game_id,
            round_number=session.current_round,
            my_role=session.my_role,
            my_score=session.my_score,
            opponent_score=session.opponent_score,
            history=session.history,
        )
        
        logger.info(f"Decided move: {move}", game_id=game_id, round=session.current_round)
        
        return move
    
    # ========================================================================
    # Protocol Message Handlers
    # ========================================================================
    
    async def _handle_game_invite(self, message: Dict) -> Dict:
        """
        Handle GAME_INVITE / GAME_INVITATION message (Section 8.7.1).
        
        Supports both:
        - assigned_role: "odd" or "even" (game-specific)
        - role_in_match: "PLAYER_A" or "PLAYER_B" (generic)
        """
        game_id = message.get("game_id")
        match_id = message.get("match_id", game_id)
        opponent_id = message.get("opponent_id")
        rounds = message.get("rounds_to_play", 5)
        
        # Support both role formats
        role = message.get("assigned_role") or message.get("role_in_match", "odd")
        # Map PLAYER_A/B to odd/even if needed
        if role == "PLAYER_A":
            role = "odd"
        elif role == "PLAYER_B":
            role = "even"
        
        # Create game session
        session = GameSession(
            game_id=game_id,
            opponent_id=opponent_id,
            my_role=GameRole(role),
            total_rounds=rounds,
            match_id=match_id,
            state="invited",
        )
        self._games[game_id] = session
        
        logger.info(
            f"Received game invitation",
            game_id=game_id,
            match_id=match_id,
            opponent=opponent_id,
            role=role,
        )
        
        # Auto-accept within 5 second timeout (Section 8.7.2)
        return await self._respond_to_invitation(game_id, True)
    
    async def _handle_move_request(self, message: Dict) -> Dict:
        """Handle MOVE_REQUEST message."""
        game_id = message.get("game_id")
        round_number = message.get("round_number", 1)
        
        session = self._games.get(game_id)
        if not session:
            return {"error": "Unknown game"}
        
        session.current_round = round_number
        session.state = "making_move"
        
        # Decide move
        move = await self.make_move(game_id)
        
        # Send move response
        move_msg = self.message_factory.move_response(
            game_id=game_id,
            round_number=round_number,
            move=move,
        )
        
        try:
            if "referee" in self._client.connected_servers:
                await self._client.send_protocol_message("referee", move_msg)
        except Exception as e:
            logger.error(f"Failed to send move: {e}")
        
        return {"success": True, "move": move}
    
    async def _handle_choose_parity_call(self, message: Dict) -> Dict:
        """
        Handle CHOOSE_PARITY_CALL message (Section 8.7.3).
        
        Responds with CHOOSE_PARITY_RESPONSE containing:
        - parity_choice: "even" or "odd" (the player's assigned role)
        - move: the actual number choice (1-10)
        """
        match_id = message.get("match_id")
        player_id = message.get("player_id")
        context = message.get("context", {})
        round_id = context.get("round_id", 1)
        
        # Find game session by match_id
        session = None
        for game_id, s in self._games.items():
            if s.match_id == match_id:
                session = s
                break
        
        if not session:
            # Try to find by any active game
            for s in self._games.values():
                if s.state in ("accepted", "making_move", "awaiting_next"):
                    session = s
                    break
        
        if not session:
            logger.error(f"No active game session found for match {match_id}")
            return {"error": "No active game session"}
        
        session.current_round = round_id
        session.state = "making_move"
        
        # Decide move (number 1-10)
        move = await self.make_move(session.game_id)
        
        # Get player's assigned role (Section 8.7.3: parity_choice is "even" or "odd")
        parity_choice = session.my_role.value  # "odd" or "even"
        
        # Send CHOOSE_PARITY_RESPONSE (Section 8.7.3)
        response_msg = self.message_factory.choose_parity_response(
            match_id=match_id,
            player_id=self.player_id,
            parity_choice=parity_choice,  # Role: "even" or "odd"
        )
        # Also include move in the response for the referee
        response_msg["move"] = move
        
        try:
            if "referee" in self._client.connected_servers:
                await self._client.send_protocol_message("referee", response_msg)
        except Exception as e:
            logger.error(f"Failed to send CHOOSE_PARITY_RESPONSE: {e}")
        
        logger.info(f"Sent parity choice '{parity_choice}' with move {move} for round {round_id}")
        
        return {"success": True, "parity_choice": parity_choice, "move": move}
    
    async def _handle_move_result(self, message: Dict) -> Dict:
        """Handle MOVE_RESULT message."""
        game_id = message.get("game_id")
        
        session = self._games.get(game_id)
        if not session:
            return {"error": "Unknown game"}
        
        # Update session with result
        session.history.append({
            "round": message.get("round_number"),
            "my_move": message.get("your_move"),
            "opponent_move": message.get("opponent_move"),
            "sum": message.get("sum_value"),
            "winner": message.get("round_winner_id"),
        })
        
        session.my_score = message.get("your_new_score", session.my_score)
        session.opponent_score = message.get("opponent_new_score", session.opponent_score)
        session.state = "awaiting_next"
        
        logger.debug(
            f"Round result received",
            game_id=game_id,
            my_score=session.my_score,
            opponent_score=session.opponent_score,
        )
        
        return {"success": True}
    
    async def _handle_game_end(self, message: Dict) -> Dict:
        """Handle GAME_END message."""
        game_id = message.get("game_id")
        winner_id = message.get("winner_id")
        
        session = self._games.get(game_id)
        if session:
            session.state = "completed"
            
            won = winner_id == self.player_id
            logger.info(
                f"Game ended",
                game_id=game_id,
                won=won,
                final_score=f"{session.my_score}-{session.opponent_score}",
            )
        
        return {"success": True, "won": winner_id == self.player_id}


# ============================================================================
# Factory Functions
# ============================================================================

def create_player(
    name: str,
    port: int,
    strategy_type: str = "random",
    llm_config: Optional[LLMConfig] = None,
) -> PlayerAgent:
    """
    Create a player agent.
    
    Args:
        name: Player name
        port: Server port
        strategy_type: "random", "pattern", or "llm"
        llm_config: LLM configuration (for llm strategy)
        
    Returns:
        PlayerAgent instance
    """
    if strategy_type == "random":
        strategy = RandomStrategy()
    elif strategy_type == "pattern":
        strategy = PatternStrategy()
    elif strategy_type == "llm":
        strategy = LLMStrategy(llm_config)
    else:
        strategy = RandomStrategy()
    
    return PlayerAgent(
        player_name=name,
        strategy=strategy,
        port=port,
    )

