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
    MessageType,
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
    """Player's view of an active game."""
    
    game_id: str
    opponent_id: str
    my_role: GameRole
    total_rounds: int
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
        """Respond to a game invitation."""
        session = self._games.get(game_id)
        if not session:
            return {"success": False, "error": "Unknown game"}
        
        session.state = "accepted" if accept else "declined"
        
        # Send response to referee
        response_msg = {
            **self.message_factory._base_fields(MessageType.GAME_INVITE_RESPONSE),
            "game_id": game_id,
            "accepted": accept,
        }
        
        try:
            if "referee" in self._client.connected_servers:
                await self._client.send_protocol_message("referee", response_msg)
        except Exception as e:
            logger.error(f"Failed to send invitation response: {e}")
        
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
        """Handle GAME_INVITE message."""
        game_id = message.get("game_id")
        opponent_id = message.get("opponent_id")
        role = message.get("assigned_role", "odd")
        rounds = message.get("rounds_to_play", 5)
        
        # Create game session
        session = GameSession(
            game_id=game_id,
            opponent_id=opponent_id,
            my_role=GameRole(role),
            total_rounds=rounds,
            state="invited",
        )
        self._games[game_id] = session
        
        logger.info(
            f"Received game invitation",
            game_id=game_id,
            opponent=opponent_id,
            role=role,
        )
        
        # Auto-accept (can be changed to manual)
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

