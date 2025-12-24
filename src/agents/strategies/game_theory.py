"""
Game Theory Strategies
======================

Implements various game-theoretic strategies for the Odd/Even game.

Strategies:
1. NashEquilibriumStrategy - Optimal mixed strategy (50/50)
2. BestResponseStrategy - Exploits opponent's bias
3. AdaptiveBayesianStrategy - Learns and adapts with Bayesian updating
4. FictitiousPlayStrategy - Classic game theory learning algorithm
5. RegretMatchingStrategy - CFR-inspired regret minimization
6. UCBStrategy - Multi-armed bandit approach
7. ThompsonSamplingStrategy - Bayesian bandit with Beta distributions

Theory Background:
- Odd/Even is equivalent to "Matching Pennies" - a zero-sum game
- Nash Equilibrium: 50/50 mix between odd and even parity
- Any deviation from Nash can be exploited by best response
- Adaptive strategies try to detect and exploit deviations
"""

import random
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple

from .base import (
    Strategy,
    GameTheoryStrategy,
    StrategyConfig,
    ParityChoice,
    OpponentModel,
)
from ...game.odd_even import GameRole
from ...common.logger import get_logger

logger = get_logger(__name__)


# =============================================================================
# Nash Equilibrium Strategy
# =============================================================================

class NashEquilibriumStrategy(GameTheoryStrategy):
    """
    Plays the Nash Equilibrium mixed strategy.
    
    In Odd/Even (equivalent to Matching Pennies):
    - Optimal strategy: play Odd 50%, Even 50%
    - Guarantees 50% expected win rate
    - Cannot be exploited by any opponent strategy
    - Cannot exploit biased opponents either
    
    Use when:
    - Playing against sophisticated/unknown opponents
    - You want guaranteed baseline performance
    - Opponent might be trying to exploit you
    """
    
    def __init__(
        self,
        config: Optional[StrategyConfig] = None,
        odd_probability: float = 0.5,
    ):
        super().__init__(config)
        self.odd_probability = odd_probability
    
    def _decide_parity(
        self,
        my_role: GameRole,
        opponent_model: OpponentModel,
    ) -> ParityChoice:
        """
        Nash equilibrium: 50/50 random choice.
        
        Note: The role doesn't matter for Nash - we just randomize.
        The game is symmetric after role assignment.
        """
        if random.random() < self.odd_probability:
            return ParityChoice.ODD
        return ParityChoice.EVEN
    
    def get_stats(self) -> Dict[str, Any]:
        stats = super().get_stats()
        stats["odd_probability"] = self.odd_probability
        return stats


# =============================================================================
# Best Response Strategy
# =============================================================================

class BestResponseStrategy(GameTheoryStrategy):
    """
    Plays the best response to opponent's observed frequency.
    
    Algorithm:
    1. Track opponent's parity distribution (% odd vs even)
    2. Calculate best response based on our role
    3. Play the optimal counter to their bias
    
    Game Theory:
    - If opponent plays Odd with probability p:
      - ODD player should play Even when p > 0.5
      - EVEN player should play Odd when p > 0.5
    
    Use when:
    - Opponent has observable bias
    - You don't care about being exploited back
    - Short games where opponent won't adapt
    
    Weakness:
    - If opponent detects our exploitation, they can counter-exploit
    - Needs sufficient data to estimate opponent's strategy
    """
    
    def __init__(
        self,
        config: Optional[StrategyConfig] = None,
        deterministic: bool = False,
    ):
        """
        Args:
            config: Strategy configuration
            deterministic: If True, always play best response.
                          If False, play proportional to expected value.
        """
        super().__init__(config)
        self.deterministic = deterministic
    
    def _decide_parity(
        self,
        my_role: GameRole,
        opponent_model: OpponentModel,
    ) -> ParityChoice:
        """
        Calculate and play best response to opponent's frequency.
        """
        # Not enough data? Play Nash
        if opponent_model.total_observations < self.config.min_observations:
            return ParityChoice.ODD if random.random() < 0.5 else ParityChoice.EVEN
        
        prob_opp_odd = opponent_model.odd_probability
        
        if self.deterministic:
            return self._calculate_best_response_parity(my_role, prob_opp_odd)
        else:
            # Probabilistic: play best response with probability proportional to edge
            best_response = self._calculate_best_response_parity(my_role, prob_opp_odd)
            edge = abs(prob_opp_odd - 0.5) * 2  # 0 to 1
            
            # With probability = edge, play best response
            # Otherwise, play random (Nash)
            if random.random() < edge:
                return best_response
            else:
                return ParityChoice.ODD if random.random() < 0.5 else ParityChoice.EVEN
    
    def get_stats(self) -> Dict[str, Any]:
        stats = super().get_stats()
        stats["deterministic"] = self.deterministic
        return stats


# =============================================================================
# Adaptive Bayesian Strategy
# =============================================================================

class AdaptiveBayesianStrategy(GameTheoryStrategy):
    """
    Adapts between Nash and exploitation using Bayesian inference.
    
    Algorithm:
    1. Maintain a belief about opponent's strategy (Beta distribution)
    2. Calculate confidence in opponent's bias
    3. When confident, exploit; otherwise, play Nash
    4. Use ε-greedy exploration to avoid being exploited
    
    Key Parameters:
    - confidence_threshold: How sure before exploiting (0.7 = 70%)
    - exploration_rate: ε for ε-greedy (0.2 = 20% random)
    - min_observations: Data needed before exploitation
    
    Use when:
    - Opponent might be biased but you're not sure
    - You want to balance exploration and exploitation
    - Games have enough rounds to learn
    
    This is the RECOMMENDED strategy for most scenarios.
    """
    
    @dataclass
    class BayesianBelief:
        """Beta distribution belief about opponent's odd probability."""
        alpha: float = 1.0  # Prior successes (odd)
        beta: float = 1.0   # Prior failures (even)
        
        def update(self, is_odd: bool) -> None:
            """Update belief with observation."""
            if is_odd:
                self.alpha += 1
            else:
                self.beta += 1
        
        @property
        def mean(self) -> float:
            """Expected probability of odd."""
            return self.alpha / (self.alpha + self.beta)
        
        @property
        def variance(self) -> float:
            """Variance of belief."""
            a, b = self.alpha, self.beta
            return (a * b) / ((a + b) ** 2 * (a + b + 1))
        
        @property
        def std(self) -> float:
            """Standard deviation."""
            return math.sqrt(self.variance)
        
        @property
        def observations(self) -> int:
            """Total observations (excluding prior)."""
            return int(self.alpha + self.beta - 2)
        
        def confidence_in_bias(self) -> float:
            """
            Confidence that opponent is biased (not 50/50).
            
            Uses distance from 0.5 relative to uncertainty.
            Returns 0-1 where 1 = very confident in bias.
            """
            distance_from_fair = abs(self.mean - 0.5)
            # Confidence increases as distance grows relative to std
            if self.std < 0.01:
                return 1.0 if distance_from_fair > 0.1 else 0.0
            z_score = distance_from_fair / self.std
            # Sigmoid-like transformation
            return 1 - math.exp(-z_score)
        
        def reset(self) -> None:
            """Reset to prior."""
            self.alpha = 1.0
            self.beta = 1.0
    
    def __init__(self, config: Optional[StrategyConfig] = None):
        super().__init__(config)
        self._beliefs: Dict[str, "AdaptiveBayesianStrategy.BayesianBelief"] = {}
    
    def _get_belief(self, game_id: str) -> "BayesianBelief":
        """Get or create Bayesian belief for a game."""
        if game_id not in self._beliefs:
            self._beliefs[game_id] = self.BayesianBelief(
                alpha=self.config.prior_alpha,
                beta=self.config.prior_beta,
            )
        return self._beliefs[game_id]
    
    def _update_belief(
        self,
        game_id: str,
        history: List[Dict],
    ) -> "BayesianBelief":
        """Update Bayesian belief from history."""
        belief = self._get_belief(game_id)
        
        # Find new observations
        processed = belief.observations
        new_history = history[processed:]
        
        for h in new_history:
            opponent_move = h.get("opponent_move")
            if opponent_move is not None:
                is_odd = opponent_move % 2 == 1
                belief.update(is_odd)
        
        return belief
    
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
        Adaptive decision using Bayesian inference.
        
        1. Update belief about opponent
        2. Check confidence in bias
        3. Explore (ε), exploit (if confident), or play Nash
        """
        # Update beliefs
        belief = self._update_belief(game_id, history)
        model = self._update_opponent_model(game_id, history, my_role)
        
        # Exploration: play random with probability ε
        if random.random() < self.config.exploration_rate:
            parity = ParityChoice.ODD if random.random() < 0.5 else ParityChoice.EVEN
            logger.debug(f"[Adaptive] Exploring: {parity.value}")
        
        # Exploitation: if confident in bias, play best response
        elif (belief.observations >= self.config.min_observations and
              belief.confidence_in_bias() >= self.config.confidence_threshold):
            parity = self._calculate_best_response_parity(my_role, belief.mean)
            logger.debug(
                f"[Adaptive] Exploiting: {parity.value} "
                f"(opponent odd prob: {belief.mean:.2f}, "
                f"confidence: {belief.confidence_in_bias():.2f})"
            )
        
        # Default: Nash equilibrium
        else:
            parity = ParityChoice.ODD if random.random() < 0.5 else ParityChoice.EVEN
            logger.debug(f"[Adaptive] Nash: {parity.value}")
        
        return self._parity_to_move(parity)
    
    def reset(self) -> None:
        super().reset()
        self._beliefs.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        stats = super().get_stats()
        stats.update({
            "exploration_rate": self.config.exploration_rate,
            "confidence_threshold": self.config.confidence_threshold,
            "beliefs": {
                game_id: {
                    "mean": b.mean,
                    "std": b.std,
                    "confidence": b.confidence_in_bias(),
                    "observations": b.observations,
                }
                for game_id, b in self._beliefs.items()
            }
        })
        return stats


# =============================================================================
# Fictitious Play Strategy
# =============================================================================

class FictitiousPlayStrategy(GameTheoryStrategy):
    """
    Classic Fictitious Play algorithm from game theory.
    
    Algorithm:
    1. Maintain empirical frequency of opponent's actions
    2. Play best response to empirical frequency
    3. Converges to Nash equilibrium against itself
    
    History:
    - Introduced by Brown (1951)
    - Proven to converge in zero-sum games
    
    Properties:
    - Simple and interpretable
    - Exploits biased opponents
    - Converges to Nash against rational opponents
    
    Weakness:
    - Can oscillate before converging
    - Slow to adapt to changing strategies
    """
    
    def __init__(
        self,
        config: Optional[StrategyConfig] = None,
        smoothing: float = 0.0,
    ):
        """
        Args:
            config: Strategy configuration
            smoothing: Add smoothing to avoid extreme responses (0-1)
        """
        super().__init__(config)
        self.smoothing = smoothing
    
    def _decide_parity(
        self,
        my_role: GameRole,
        opponent_model: OpponentModel,
    ) -> ParityChoice:
        """
        Pure fictitious play: best response to empirical frequency.
        """
        if opponent_model.total_observations == 0:
            # No data: randomize
            return ParityChoice.ODD if random.random() < 0.5 else ParityChoice.EVEN
        
        # Apply smoothing to avoid extreme exploitation
        raw_prob = opponent_model.odd_probability
        smoothed_prob = self.smoothing * 0.5 + (1 - self.smoothing) * raw_prob
        
        return self._calculate_best_response_parity(my_role, smoothed_prob)
    
    def get_stats(self) -> Dict[str, Any]:
        stats = super().get_stats()
        stats["smoothing"] = self.smoothing
        return stats


# =============================================================================
# Regret Matching Strategy
# =============================================================================

class RegretMatchingStrategy(GameTheoryStrategy):
    """
    Regret-based learning inspired by Counterfactual Regret Minimization (CFR).
    
    Used in poker AI (Libratus, Pluribus) to find Nash equilibria.
    
    Algorithm:
    1. Track "regret" for not playing each action
    2. Play actions proportional to positive regret
    3. Converges to Nash equilibrium over time
    
    Regret Calculation:
    - If we played action A and got utility U
    - Regret for action B = U(B) - U(A) (counterfactual)
    - Accumulate regrets over time
    
    Properties:
    - Theoretical guarantees for convergence
    - Self-correcting
    - Robust to opponent exploitation
    """
    
    def __init__(self, config: Optional[StrategyConfig] = None):
        super().__init__(config)
        # Cumulative regrets per game: {game_id: {"odd": float, "even": float}}
        self._regrets: Dict[str, Dict[str, float]] = {}
        # Last action per game for regret calculation
        self._last_action: Dict[str, ParityChoice] = {}
    
    def _get_regrets(self, game_id: str) -> Dict[str, float]:
        """Get or create regret table for a game."""
        if game_id not in self._regrets:
            self._regrets[game_id] = {"odd": 0.0, "even": 0.0}
        return self._regrets[game_id]
    
    def _update_regrets(
        self,
        game_id: str,
        my_role: GameRole,
        last_round: Dict,
    ) -> None:
        """
        Update regrets based on last round's outcome.
        
        Calculates counterfactual regret for the action not taken.
        """
        if game_id not in self._last_action:
            return
        
        regrets = self._get_regrets(game_id)
        my_action = self._last_action[game_id]
        opponent_move = last_round.get("opponent_move", 0)
        opponent_parity = ParityChoice.from_number(opponent_move)
        
        # Calculate what would have happened with each action
        def utility(my_parity: ParityChoice) -> float:
            """Utility of playing my_parity against opponent."""
            # Sum parity when we play my_parity
            if my_parity == ParityChoice.ODD:
                sum_is_odd = opponent_parity == ParityChoice.EVEN  # ODD + EVEN = ODD
            else:
                sum_is_odd = opponent_parity == ParityChoice.ODD   # EVEN + ODD = ODD
            
            # Did we win?
            if my_role == GameRole.ODD:
                return 1.0 if sum_is_odd else -1.0
            else:
                return 1.0 if not sum_is_odd else -1.0
        
        # Actual utility
        actual_utility = utility(my_action)
        
        # Counterfactual regrets
        for action in [ParityChoice.ODD, ParityChoice.EVEN]:
            if action != my_action:
                counterfactual = utility(action)
                regret = counterfactual - actual_utility
                regrets[action.value] += regret
    
    def _regret_matching_probabilities(
        self,
        regrets: Dict[str, float],
    ) -> Tuple[float, float]:
        """
        Convert regrets to action probabilities.
        
        Play proportional to positive regrets.
        """
        pos_odd = max(0, regrets["odd"])
        pos_even = max(0, regrets["even"])
        total = pos_odd + pos_even
        
        if total <= 0:
            # No positive regrets: uniform
            return 0.5, 0.5
        
        return pos_odd / total, pos_even / total
    
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
        Regret matching decision.
        """
        # Update regrets from last round
        if history:
            self._update_regrets(game_id, my_role, history[-1])
        
        # Get current regrets
        regrets = self._get_regrets(game_id)
        
        # Calculate probabilities from regrets
        p_odd, p_even = self._regret_matching_probabilities(regrets)
        
        # Sample action
        if random.random() < p_odd:
            parity = ParityChoice.ODD
        else:
            parity = ParityChoice.EVEN
        
        # Remember for next regret update
        self._last_action[game_id] = parity
        
        logger.debug(
            f"[RegretMatching] Regrets: odd={regrets['odd']:.2f}, even={regrets['even']:.2f}, "
            f"probs: odd={p_odd:.2f}, even={p_even:.2f}, chose: {parity.value}"
        )
        
        return self._parity_to_move(parity)
    
    def reset(self) -> None:
        super().reset()
        self._regrets.clear()
        self._last_action.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        stats = super().get_stats()
        stats["regrets"] = dict(self._regrets)
        return stats


# =============================================================================
# UCB (Upper Confidence Bound) Strategy
# =============================================================================

class UCBStrategy(GameTheoryStrategy):
    """
    Multi-Armed Bandit approach using Upper Confidence Bound.
    
    Treats each parity choice as a "bandit arm" and uses UCB1 algorithm.
    
    Algorithm:
    - UCB score = mean reward + c * sqrt(ln(n) / n_i)
    - Play action with highest UCB score
    - Balances exploration and exploitation theoretically
    
    Properties:
    - Provably optimal exploration-exploitation tradeoff
    - Adapts based on uncertainty
    - Good for unknown opponent strategies
    
    c parameter:
    - Higher c = more exploration
    - sqrt(2) ≈ 1.414 is theoretically optimal for [0,1] rewards
    """
    
    @dataclass
    class ArmStats:
        """Statistics for one arm (parity choice)."""
        pulls: int = 0
        total_reward: float = 0.0
        
        @property
        def mean_reward(self) -> float:
            if self.pulls == 0:
                return 0.5  # Optimistic prior
            return self.total_reward / self.pulls
        
        def update(self, reward: float) -> None:
            self.pulls += 1
            self.total_reward += reward
    
    def __init__(self, config: Optional[StrategyConfig] = None):
        super().__init__(config)
        self._arms: Dict[str, Dict[str, "UCBStrategy.ArmStats"]] = {}
        self._last_action: Dict[str, ParityChoice] = {}
        self._total_pulls: Dict[str, int] = {}
    
    def _get_arms(self, game_id: str) -> Dict[str, "ArmStats"]:
        """Get or create arm stats for a game."""
        if game_id not in self._arms:
            self._arms[game_id] = {
                "odd": self.ArmStats(),
                "even": self.ArmStats(),
            }
            self._total_pulls[game_id] = 0
        return self._arms[game_id]
    
    def _ucb_score(
        self,
        arm: "ArmStats",
        total_pulls: int,
        c: float,
    ) -> float:
        """
        Calculate UCB score for an arm.
        
        UCB1: mean + c * sqrt(ln(n) / n_i)
        """
        if arm.pulls == 0:
            return float('inf')  # Play unexplored arms first
        
        exploration = c * math.sqrt(math.log(total_pulls) / arm.pulls)
        return arm.mean_reward + exploration
    
    def _update_arms(
        self,
        game_id: str,
        my_role: GameRole,
        last_round: Dict,
    ) -> None:
        """Update arm statistics from last round."""
        if game_id not in self._last_action:
            return
        
        arms = self._get_arms(game_id)
        my_action = self._last_action[game_id]
        
        # Calculate reward (1 for win, 0 for loss)
        my_move = last_round.get("my_move", 0)
        opponent_move = last_round.get("opponent_move", 0)
        total = my_move + opponent_move
        sum_is_odd = total % 2 == 1
        
        if my_role == GameRole.ODD:
            reward = 1.0 if sum_is_odd else 0.0
        else:
            reward = 1.0 if not sum_is_odd else 0.0
        
        # Update arm
        arms[my_action.value].update(reward)
    
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
        UCB decision.
        """
        # Update from last round
        if history:
            self._update_arms(game_id, my_role, history[-1])
        
        arms = self._get_arms(game_id)
        self._total_pulls[game_id] = sum(a.pulls for a in arms.values())
        total = max(1, self._total_pulls[game_id])
        
        # Calculate UCB scores
        c = self.config.ucb_exploration_constant
        ucb_odd = self._ucb_score(arms["odd"], total, c)
        ucb_even = self._ucb_score(arms["even"], total, c)
        
        # Select action with highest UCB
        if ucb_odd >= ucb_even:
            parity = ParityChoice.ODD
        else:
            parity = ParityChoice.EVEN
        
        self._last_action[game_id] = parity
        
        logger.debug(
            f"[UCB] Scores: odd={ucb_odd:.3f}, even={ucb_even:.3f}, "
            f"chose: {parity.value}"
        )
        
        return self._parity_to_move(parity)
    
    def reset(self) -> None:
        super().reset()
        self._arms.clear()
        self._last_action.clear()
        self._total_pulls.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        stats = super().get_stats()
        stats["arms"] = {
            game_id: {
                action: {"pulls": arm.pulls, "mean": arm.mean_reward}
                for action, arm in arms.items()
            }
            for game_id, arms in self._arms.items()
        }
        return stats


# =============================================================================
# Thompson Sampling Strategy
# =============================================================================

class ThompsonSamplingStrategy(GameTheoryStrategy):
    """
    Bayesian bandit strategy using Thompson Sampling.
    
    Maintains Beta distribution belief about reward probability for each action.
    Samples from posteriors and plays action with highest sample.
    
    Algorithm:
    1. Maintain Beta(α, β) for each action
    2. Sample θ ~ Beta(α, β) for each action
    3. Play action with highest θ
    4. Update posterior with outcome
    
    Properties:
    - Probability matching: explores proportional to posterior
    - Bayesian optimality
    - Often outperforms UCB in practice
    - Naturally handles uncertainty
    """
    
    @dataclass
    class BetaPosterior:
        """Beta distribution posterior for one action."""
        alpha: float = 1.0  # Prior wins + 1
        beta: float = 1.0   # Prior losses + 1
        
        def sample(self) -> float:
            """Sample from Beta distribution."""
            import random
            # Use random.betavariate for Beta sampling
            return random.betavariate(self.alpha, self.beta)
        
        def update(self, reward: float) -> None:
            """Update posterior with reward (0 or 1)."""
            if reward > 0.5:
                self.alpha += 1
            else:
                self.beta += 1
        
        @property
        def mean(self) -> float:
            return self.alpha / (self.alpha + self.beta)
        
        def reset(self, prior_alpha: float = 1.0, prior_beta: float = 1.0) -> None:
            self.alpha = prior_alpha
            self.beta = prior_beta
    
    def __init__(self, config: Optional[StrategyConfig] = None):
        super().__init__(config)
        self._posteriors: Dict[str, Dict[str, "ThompsonSamplingStrategy.BetaPosterior"]] = {}
        self._last_action: Dict[str, ParityChoice] = {}
    
    def _get_posteriors(self, game_id: str) -> Dict[str, "BetaPosterior"]:
        """Get or create posteriors for a game."""
        if game_id not in self._posteriors:
            self._posteriors[game_id] = {
                "odd": self.BetaPosterior(
                    self.config.prior_alpha,
                    self.config.prior_beta,
                ),
                "even": self.BetaPosterior(
                    self.config.prior_alpha,
                    self.config.prior_beta,
                ),
            }
        return self._posteriors[game_id]
    
    def _update_posteriors(
        self,
        game_id: str,
        my_role: GameRole,
        last_round: Dict,
    ) -> None:
        """Update posteriors from last round."""
        if game_id not in self._last_action:
            return
        
        posteriors = self._get_posteriors(game_id)
        my_action = self._last_action[game_id]
        
        # Calculate reward
        my_move = last_round.get("my_move", 0)
        opponent_move = last_round.get("opponent_move", 0)
        total = my_move + opponent_move
        sum_is_odd = total % 2 == 1
        
        if my_role == GameRole.ODD:
            reward = 1.0 if sum_is_odd else 0.0
        else:
            reward = 1.0 if not sum_is_odd else 0.0
        
        # Update posterior for played action
        posteriors[my_action.value].update(reward)
    
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
        Thompson Sampling decision.
        """
        # Update from last round
        if history:
            self._update_posteriors(game_id, my_role, history[-1])
        
        posteriors = self._get_posteriors(game_id)
        
        # Sample from each posterior
        sample_odd = posteriors["odd"].sample()
        sample_even = posteriors["even"].sample()
        
        # Play action with highest sample
        if sample_odd >= sample_even:
            parity = ParityChoice.ODD
        else:
            parity = ParityChoice.EVEN
        
        self._last_action[game_id] = parity
        
        logger.debug(
            f"[Thompson] Samples: odd={sample_odd:.3f}, even={sample_even:.3f}, "
            f"chose: {parity.value}"
        )
        
        return self._parity_to_move(parity)
    
    def reset(self) -> None:
        super().reset()
        self._posteriors.clear()
        self._last_action.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        stats = super().get_stats()
        stats["posteriors"] = {
            game_id: {
                action: {"alpha": p.alpha, "beta": p.beta, "mean": p.mean}
                for action, p in posteriors.items()
            }
            for game_id, posteriors in self._posteriors.items()
        }
        return stats

