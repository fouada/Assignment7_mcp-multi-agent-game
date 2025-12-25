"""
Classic Strategies
==================

Original strategies from the project:
- RandomStrategy: Uniform random moves
- PatternStrategy: Simple pattern detection
- LLMStrategy: LLM-powered decisions

These are kept for backwards compatibility and comparison.
"""

import random
import re
from typing import Any

from ...common.config import LLMConfig
from ...common.logger import get_logger
from ...game.odd_even import GameRole
from .base import Strategy, StrategyConfig

logger = get_logger(__name__)


class RandomStrategy(Strategy):
    """
    Random strategy - picks uniformly random values.

    Game Theory Analysis:
    - Approximates Nash Equilibrium (50% each parity)
    - Cannot be exploited
    - Cannot exploit opponents
    - Good baseline strategy
    """

    def __init__(self, config: StrategyConfig | None = None):
        super().__init__(config)

    async def decide_move(
        self,
        game_id: str,
        round_number: int,
        my_role: GameRole,
        my_score: int,
        opponent_score: int,
        history: list[dict],
    ) -> int:
        """Pick a random number in the valid range."""
        return random.randint(self.config.min_value, self.config.max_value)

    def get_stats(self) -> dict[str, Any]:
        stats = super().get_stats()
        stats.update({
            "min_value": self.config.min_value,
            "max_value": self.config.max_value,
        })
        return stats


class PatternStrategy(Strategy):
    """
    Pattern-based strategy.

    Analyzes opponent's patterns and tries to counter.

    Game Theory Analysis:
    - Exploitive strategy (tries to predict opponent)
    - Can beat predictable opponents
    - Original implementation has flawed logic (uses average)
    - This version is improved to track parity
    """

    def __init__(self, config: StrategyConfig | None = None):
        super().__init__(config)
        self._opponent_parities: dict[str, list[bool]] = {}  # game_id -> [is_odd, ...]

    def _get_opponent_history(self, game_id: str) -> list[bool]:
        """Get opponent's parity history for a game."""
        if game_id not in self._opponent_parities:
            self._opponent_parities[game_id] = []
        return self._opponent_parities[game_id]

    def _update_history(self, game_id: str, history: list[dict]) -> list[bool]:
        """Update opponent history from game history."""
        opp_parities = self._get_opponent_history(game_id)

        # Add new observations
        for i in range(len(opp_parities), len(history)):
            opponent_move = history[i].get("opponent_move", 0)
            is_odd = opponent_move % 2 == 1
            opp_parities.append(is_odd)

        return opp_parities

    async def decide_move(
        self,
        game_id: str,
        round_number: int,
        my_role: GameRole,
        my_score: int,
        opponent_score: int,
        history: list[dict],
    ) -> int:
        """
        Decide based on opponent's pattern.

        Improved version: tracks parity frequency, not average.
        """
        if not history:
            return random.randint(self.config.min_value, self.config.max_value)

        # Update opponent history
        opp_parities = self._update_history(game_id, history)

        if not opp_parities:
            return random.randint(self.config.min_value, self.config.max_value)

        # Calculate opponent's odd frequency (last 5 rounds)
        recent = opp_parities[-5:]
        odd_freq = sum(recent) / len(recent)

        # Predict opponent's next parity
        opponent_likely_odd = odd_freq > 0.5

        # Calculate best response
        if my_role == GameRole.ODD:
            # We want sum to be odd
            # If opponent plays odd, we should play even (and vice versa)
            should_play_odd = not opponent_likely_odd
        else:
            # We want sum to be even
            # If opponent plays odd, we should play odd (to get even sum)
            should_play_odd = opponent_likely_odd

        # Pick a number with the desired parity
        if should_play_odd:
            candidates = [n for n in range(self.config.min_value, self.config.max_value + 1) if n % 2 == 1]
        else:
            candidates = [n for n in range(self.config.min_value, self.config.max_value + 1) if n % 2 == 0]

        return random.choice(candidates) if candidates else random.randint(self.config.min_value, self.config.max_value)

    def reset(self) -> None:
        self._opponent_parities.clear()

    def get_stats(self) -> dict[str, Any]:
        stats = super().get_stats()
        stats["games_tracked"] = len(self._opponent_parities)
        return stats


class LLMStrategy(Strategy):
    """
    LLM-based strategy using Anthropic Claude or OpenAI.

    Uses an LLM to analyze the game and decide moves.

    Game Theory Analysis:
    - Quality depends on LLM's reasoning
    - Can incorporate game theory in prompt
    - Expensive (API calls per move)
    - Falls back to random on error

    Providers:
    - Anthropic: claude-sonnet-4-20250514 (default)
    - OpenAI: gpt-4o-mini
    """

    def __init__(
        self,
        config: StrategyConfig | None = None,
        llm_config: LLMConfig | None = None,
    ):
        super().__init__(config)
        self.llm_config = llm_config or LLMConfig()
        self._client = None
        logger.info(f"LLM Strategy initialized: {self.llm_config.provider} / {self.llm_config.model}")

    async def _get_client(self):
        """Get or create LLM client."""
        if self._client is not None:
            return self._client

        if not self.llm_config.api_key:
            logger.warning(f"No API key for {self.llm_config.provider}, falling back to random")
            return None

        if self.llm_config.provider == "anthropic":
            try:
                import anthropic
                self._client = anthropic.AsyncAnthropic(api_key=self.llm_config.api_key)
                logger.info("Anthropic Claude client initialized")
            except ImportError:
                logger.warning("Anthropic not installed. Install with: pip install anthropic")
                return None
        elif self.llm_config.provider == "openai":
            try:
                import openai
                self._client = openai.AsyncOpenAI(api_key=self.llm_config.api_key)
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
        history: list[dict],
    ) -> int:
        """Use LLM to decide move."""
        client = await self._get_client()

        if client is None:
            logger.debug("No LLM client, using random move")
            return random.randint(self.config.min_value, self.config.max_value)

        # Build prompt with game theory context
        prompt = self._build_prompt(
            round_number, my_role, my_score, opponent_score, history
        )

        try:
            if self.llm_config.provider == "anthropic":
                response = await client.messages.create(
                    model=self.llm_config.model,
                    max_tokens=10,
                    system="You are an expert game theorist. Respond with ONLY a single number from 1 to 10.",
                    messages=[
                        {"role": "user", "content": prompt},
                    ],
                )
                answer = response.content[0].text.strip()
                logger.debug(f"Claude response: {answer}")
            else:
                response = await client.chat.completions.create(
                    model=self.llm_config.model,
                    messages=[
                        {"role": "system", "content": "You are an expert game theorist. Respond with ONLY a single number from 1 to 10."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=self.llm_config.temperature,
                    max_tokens=10,
                )
                answer = response.choices[0].message.content.strip()
                logger.debug(f"OpenAI response: {answer}")

            # Parse response - extract first valid number
            numbers = re.findall(r'\b([1-9]|10)\b', answer)
            if numbers:
                move = int(numbers[0])
                if self.config.min_value <= move <= self.config.max_value:
                    logger.info(f"LLM decided move: {move}", game_id=game_id, round=round_number)
                    return move

        except Exception as e:
            logger.warning(f"LLM decision failed: {e}")

        # Fallback to random
        logger.debug("LLM failed, using random fallback")
        return random.randint(self.config.min_value, self.config.max_value)

    def _build_prompt(
        self,
        round_number: int,
        my_role: GameRole,
        my_score: int,
        opponent_score: int,
        history: list[dict],
    ) -> str:
        """Build prompt for LLM with game theory context."""
        role_explanation = (
            "You win when the sum of both numbers is ODD" if my_role == GameRole.ODD
            else "You win when the sum of both numbers is EVEN"
        )

        # Analyze opponent's pattern
        pattern_analysis = ""
        if history:
            opp_moves = [h.get("opponent_move", 0) for h in history]
            opp_odd = sum(1 for m in opp_moves if m % 2 == 1)
            opp_even = len(opp_moves) - opp_odd
            pattern_analysis = f"\nOpponent's pattern: played odd {opp_odd} times, even {opp_even} times."

        history_str = ""
        if history:
            history_str = "\nRecent rounds:\n"
            for h in history[-5:]:
                my_m = h.get("my_move", "?")
                opp_m = h.get("opponent_move", "?")
                s = h.get("sum", "?")
                history_str += f"  Round {h.get('round', '?')}: You: {my_m}, Opponent: {opp_m}, Sum: {s}\n"

        return f"""You are playing the Odd/Even game.

RULES:
- Both players simultaneously choose a number from 1 to 10
- The sum is calculated
- {role_explanation}

GAME THEORY:
- This is equivalent to Matching Pennies
- Nash equilibrium: 50% odd, 50% even numbers
- Best response: If opponent is biased, exploit it
- ODD player: play OPPOSITE parity to opponent's tendency
- EVEN player: play SAME parity as opponent's tendency

CURRENT STATE:
- Round: {round_number}
- Your role: {my_role.value.upper()}
- Score: You {my_score} - {opponent_score} Opponent
{pattern_analysis}
{history_str}

Think about:
1. Is opponent biased toward odd or even?
2. What's the best response to their pattern?
3. Should you be unpredictable instead?

Choose a number from 1 to 10. Reply with ONLY the number:"""

    def get_stats(self) -> dict[str, Any]:
        stats = super().get_stats()
        stats.update({
            "provider": self.llm_config.provider,
            "model": self.llm_config.model,
        })
        return stats

