# 🎲 Game Theory Strategies

> A comprehensive guide to game-theoretic strategies for the Odd/Even game

## 📋 Table of Contents

- [Game Theory Background](#game-theory-background)
- [Available Strategies](#available-strategies)
- [Strategy Selection Guide](#strategy-selection-guide)
- [Usage Examples](#usage-examples)
- [Strategy Comparison](#strategy-comparison)
- [Configuration Reference](#configuration-reference)

---

## 🎯 Game Theory Background

### The Odd/Even Game

The Odd/Even game is equivalent to **Matching Pennies** - a classic zero-sum game in game theory.

```
Rules:
1. Two players are assigned roles: ODD or EVEN
2. Both simultaneously choose a number (1-10)
3. The sum is calculated
4. ODD player wins if sum is odd, EVEN player wins if sum is even
```

### Key Insight: Parity Matters, Not Numbers

What matters for winning is the **parity** (odd/even) of your choice:

| My Choice | Opponent Choice | Sum | Winner |
|-----------|-----------------|-----|--------|
| Odd | Odd | Even | EVEN player |
| Odd | Even | Odd | ODD player |
| Even | Odd | Odd | ODD player |
| Even | Even | Even | EVEN player |

### Nash Equilibrium

The **Nash Equilibrium** for this game is:
- Play **Odd** with probability **50%**
- Play **Even** with probability **50%**

At this equilibrium:
- Neither player can improve by changing strategy alone
- Expected win rate = **50%** for both players
- This is the "safe" baseline strategy

### Exploitation vs Safety

| Approach | Description | Risk |
|----------|-------------|------|
| **Nash** | Play 50/50 | Can't be exploited, can't exploit |
| **Exploitive** | Counter opponent's bias | Can be counter-exploited |
| **Adaptive** | Learn and adapt | Best of both worlds |

---

## 🧠 Available Strategies

### Classic Strategies

#### 1. RandomStrategy
```python
from src.agents import create_player

player = create_player("Bot", 8101, strategy_type="random")
```

| Property | Value |
|----------|-------|
| **Logic** | Uniform random 1-10 |
| **Game Theory** | Approximates Nash (50% parity each) |
| **Pros** | Simple, unpredictable |
| **Cons** | Can't exploit opponent bias |
| **Best Against** | Unknown opponents |

#### 2. PatternStrategy
```python
player = create_player("Bot", 8101, strategy_type="pattern")
```

| Property | Value |
|----------|-------|
| **Logic** | Tracks opponent's parity frequency |
| **Game Theory** | Exploitive |
| **Pros** | Can beat predictable opponents |
| **Cons** | Can be counter-exploited |
| **Best Against** | Biased opponents |

#### 3. LLMStrategy
```python
from src.common.config import LLMConfig

player = create_player(
    "ClaudeBot", 8101,
    strategy_type="llm",
    llm_config=LLMConfig(provider="anthropic")
)
```

| Property | Value |
|----------|-------|
| **Logic** | LLM reasons about game theory |
| **Game Theory** | Depends on LLM |
| **Pros** | Can reason about complex patterns |
| **Cons** | Expensive, slow, inconsistent |
| **Best Against** | Complex scenarios |

---

### Game Theory Strategies

#### 4. NashEquilibriumStrategy ⚖️
```python
player = create_player("Bot", 8101, strategy_type="nash")
```

| Property | Value |
|----------|-------|
| **Logic** | 50% odd, 50% even parity |
| **Guarantee** | 50% expected win rate |
| **Cannot be** | Exploited |
| **Cannot** | Exploit opponents |
| **Use When** | Unknown/skilled opponents |

**Theory**: The minimax optimal strategy. No matter what opponent does, you get 50%.

#### 5. BestResponseStrategy 🎯
```python
player = create_player(
    "Bot", 8101,
    strategy_type="best_response",
    deterministic=True  # Always play best response
)
```

| Property | Value |
|----------|-------|
| **Logic** | Play optimal counter to opponent's frequency |
| **Win Rate** | >50% vs biased opponents |
| **Risk** | Can be counter-exploited |
| **min_observations** | Minimum data before exploiting (default: 3) |

**Algorithm**:
```
If opponent plays Odd 60% of the time:
  - ODD player: Play Even (to get Odd sum)
  - EVEN player: Play Odd (to get Even sum)
```

#### 6. AdaptiveBayesianStrategy ⭐ RECOMMENDED
```python
player = create_player(
    "Bot", 8101,
    strategy_type="adaptive_bayesian",
    exploration_rate=0.15,      # 15% random exploration
    confidence_threshold=0.7    # Exploit when 70% confident
)
```

| Property | Value |
|----------|-------|
| **Logic** | Bayesian belief updating + ε-greedy |
| **Default** | Starts with Nash |
| **Learns** | Opponent's bias via Beta distribution |
| **Exploits** | When confident in bias |
| **Explores** | 15% of the time (configurable) |

**Why Recommended**:
- Safe when uncertain (plays Nash)
- Exploits when confident
- Explores to avoid being exploited
- Theoretically grounded

**Algorithm**:
```python
1. Update Bayesian belief about opponent's parity
2. If random() < exploration_rate:
       play random (explore)
3. Elif confident in opponent bias:
       play best response (exploit)
4. Else:
       play Nash (safe default)
```

#### 7. FictitiousPlayStrategy 📚
```python
player = create_player(
    "Bot", 8101,
    strategy_type="fictitious_play",
    smoothing=0.1  # Smooth exploitation (0 = pure best response)
)
```

| Property | Value |
|----------|-------|
| **Logic** | Best response to empirical frequency |
| **History** | Classic game theory (Brown, 1951) |
| **Convergence** | To Nash equilibrium |
| **Smoothing** | Reduces oscillation |

**Theory**: If both players use Fictitious Play, they converge to Nash equilibrium.

#### 8. RegretMatchingStrategy 🎰
```python
player = create_player("Bot", 8101, strategy_type="regret_matching")
```

| Property | Value |
|----------|-------|
| **Logic** | Minimize cumulative regret |
| **Inspired By** | CFR (Counterfactual Regret Minimization) |
| **Used In** | Poker AI (Libratus, Pluribus) |
| **Convergence** | To Nash equilibrium |

**Algorithm**:
```
1. Track "regret" for each action not taken
2. Regret = what I could have won - what I won
3. Play proportional to positive regrets
4. Converges to Nash over time
```

#### 9. UCBStrategy 📊
```python
player = create_player(
    "Bot", 8101,
    strategy_type="ucb",
    ucb_exploration_constant=1.414  # sqrt(2) is optimal
)
```

| Property | Value |
|----------|-------|
| **Logic** | Upper Confidence Bound (UCB1) |
| **Category** | Multi-Armed Bandit |
| **Balance** | Exploration vs Exploitation |
| **Formula** | mean + c × √(ln(n) / nᵢ) |

**When to Use**: When you want theoretically optimal exploration-exploitation.

#### 10. ThompsonSamplingStrategy 🎲
```python
player = create_player(
    "Bot", 8101,
    strategy_type="thompson_sampling",
    prior_alpha=1.0,  # Beta distribution prior
    prior_beta=1.0
)
```

| Property | Value |
|----------|-------|
| **Logic** | Sample from Beta posteriors |
| **Category** | Bayesian Bandit |
| **Often** | Outperforms UCB in practice |
| **Naturally** | Handles uncertainty |

**Algorithm**:
```
1. Maintain Beta(α, β) for each parity
2. Sample θ ~ Beta(α, β) for each
3. Play parity with highest sample
4. Update posterior with outcome
```

---

## 📋 Strategy Selection Guide

### Quick Decision Tree

```
Is opponent known?
├── No → AdaptiveBayesianStrategy (safe + learns)
└── Yes
    ├── Opponent is Nash? → NashEquilibriumStrategy
    ├── Opponent is biased? → BestResponseStrategy
    └── Opponent adapts? → RegretMatchingStrategy
```

### By Scenario

| Scenario | Recommended | Reason |
|----------|-------------|--------|
| **Tournament (unknown opponents)** | AdaptiveBayesian | Learns while staying safe |
| **Playing against beginners** | BestResponse | Exploit predictable play |
| **Playing against experts** | Nash | Can't be exploited |
| **Short games (1-3 rounds)** | Nash | Not enough data to learn |
| **Long games (10+ rounds)** | AdaptiveBayesian | Time to learn patterns |
| **Research/Analysis** | RegretMatching | Theoretical guarantees |

### Performance Expectations

```
Against Random:
  Nash: 50%, BestResponse: 50%, Adaptive: 50%
  
Against 70% Odd bias:
  Nash: 50%, BestResponse: 70%, Adaptive: ~65%
  
Against Adaptive:
  Nash: 50%, BestResponse: ~45%, Adaptive: ~50%
```

---

## 💻 Usage Examples

### Basic Usage

```python
from src.agents import create_player, list_available_strategies

# See all strategies
print(list_available_strategies())

# Create players with different strategies
random_player = create_player("Random", 8101, strategy_type="random")
nash_player = create_player("Nash", 8102, strategy_type="nash")
adaptive_player = create_player("Adaptive", 8103, strategy_type="adaptive_bayesian")
```

### With Configuration

```python
from src.agents import create_player
from src.agents.strategies import StrategyConfig

# Custom configuration
config = StrategyConfig(
    min_value=1,
    max_value=10,
    exploration_rate=0.2,
    confidence_threshold=0.6,
)

player = create_player(
    "CustomBot", 8101,
    strategy_type="adaptive_bayesian",
    strategy_config=config
)
```

### Using Factory Directly

```python
from src.agents.strategies import StrategyFactory, StrategyType

# Create strategy
strategy = StrategyFactory.create(StrategyType.ADAPTIVE_BAYESIAN)

# Create with custom parameters
strategy = StrategyFactory.create(
    StrategyType.UCB,
    ucb_exploration_constant=2.0
)

# Get recommended
strategy = StrategyFactory.get_recommended_strategy()
```

### In League Configuration

```bash
# Run league with adaptive strategy for all players
uv run python -m src.main --run --strategy adaptive_bayesian

# Run with mixed strategies
uv run python -m src.main --run --strategy mixed
```

---

## 📊 Strategy Comparison

### Theoretical Properties

| Strategy | Exploits Bias | Can Be Exploited | Converges to Nash | Learning Speed |
|----------|--------------|------------------|-------------------|----------------|
| Nash | ❌ | ❌ | ✅ (is Nash) | N/A |
| BestResponse | ✅ Strong | ✅ Yes | ❌ | Fast |
| AdaptiveBayesian | ✅ Moderate | ⚠️ Limited | ⚠️ Partial | Moderate |
| FictitiousPlay | ✅ Moderate | ⚠️ Temporary | ✅ Yes | Slow |
| RegretMatching | ⚠️ Indirect | ❌ | ✅ Yes | Moderate |
| UCB | ✅ Moderate | ⚠️ Limited | ⚠️ Partial | Moderate |
| Thompson | ✅ Moderate | ⚠️ Limited | ⚠️ Partial | Fast |

### Computational Complexity

| Strategy | Time per Move | Space | Suitable for |
|----------|---------------|-------|--------------|
| Nash | O(1) | O(1) | Any |
| BestResponse | O(1) | O(n) | Any |
| AdaptiveBayesian | O(1) | O(n) | Any |
| FictitiousPlay | O(1) | O(n) | Any |
| RegretMatching | O(1) | O(n) | Any |
| UCB | O(1) | O(n) | Any |
| Thompson | O(1) | O(n) | Any |

---

## ⚙️ Configuration Reference

### StrategyConfig Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `min_value` | int | 1 | Minimum move value |
| `max_value` | int | 10 | Maximum move value |
| `exploration_rate` | float | 0.2 | ε for ε-greedy exploration |
| `confidence_threshold` | float | 0.7 | When to switch from Nash to exploit |
| `min_observations` | int | 3 | Minimum data before exploitation |
| `learning_rate` | float | 0.1 | Learning rate for regret matching |
| `decay_rate` | float | 0.99 | Decay for time-weighted observations |
| `ucb_exploration_constant` | float | 1.414 | c in UCB formula |
| `prior_alpha` | float | 1.0 | Beta distribution prior α |
| `prior_beta` | float | 1.0 | Beta distribution prior β |

### Strategy-Specific Parameters

| Strategy | Parameter | Default | Description |
|----------|-----------|---------|-------------|
| Nash | `odd_probability` | 0.5 | Probability of playing odd |
| BestResponse | `deterministic` | False | Always play best response |
| FictitiousPlay | `smoothing` | 0.0 | Smooth exploitation |

---

## 📚 References

1. **Matching Pennies**: Von Neumann, J. (1928). "Zur Theorie der Gesellschaftsspiele"
2. **Fictitious Play**: Brown, G.W. (1951). "Iterative solution of games by fictitious play"
3. **Regret Matching**: Hart, S. & Mas-Colell, A. (2000). "A simple adaptive procedure leading to correlated equilibrium"
4. **CFR**: Zinkevich et al. (2008). "Regret Minimization in Games with Incomplete Information"
5. **UCB1**: Auer et al. (2002). "Finite-time Analysis of the Multiarmed Bandit Problem"
6. **Thompson Sampling**: Thompson, W.R. (1933). "On the likelihood that one unknown probability exceeds another"

---

<div align="center">

**Built with ❤️ using Game Theory**

</div>

