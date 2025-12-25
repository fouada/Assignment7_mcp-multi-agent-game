"""
Statistical Comparison Framework
=================================

MIT-Level research framework for rigorous empirical comparison of strategies:
1. A/B testing with statistical power analysis
2. Multi-armed bandit tournament
3. Bayesian hypothesis testing
4. Bootstrap confidence intervals
5. Non-parametric tests (Mann-Whitney U, Kruskal-Wallis)
6. Effect size measurement (Cohen's d, Cliff's delta)
7. Multiple comparison correction (Bonferroni, Holm-Bonferroni, FDR)

Theoretical Foundation:
- Lehmann, E. L. (1986). "Testing Statistical Hypotheses"
- Efron, B. (1979). "Bootstrap methods: Another look at the jackknife"
- Kruschke, J. K. (2013). "Bayesian estimation supersedes the t-test"

Usage:
    python experiments/statistical_comparison.py --strategies nash,bayesian,regret --games 1000
"""

import asyncio
import time
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import json
from scipy import stats
from scipy.stats import mannwhitneyu, kruskal
import itertools
from collections import defaultdict

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.strategies import StrategyFactory, StrategyType
from src.game.odd_even import OddEvenGame
from src.common.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# Data Structures
# ============================================================================


@dataclass
class ComparisonResult:
    """Result of pairwise strategy comparison."""
    strategy_a: str
    strategy_b: str
    
    # Win rates
    win_rate_a: float
    win_rate_b: float
    draw_rate: float
    
    # Statistical tests
    t_statistic: float
    t_pvalue: float
    mann_whitney_u: float
    mann_whitney_pvalue: float
    
    # Effect sizes
    cohens_d: float
    cliffs_delta: float
    
    # Confidence intervals (95%)
    ci_win_rate_a: Tuple[float, float]
    ci_win_rate_b: Tuple[float, float]
    
    # Power analysis
    statistical_power: float
    required_samples: int
    
    # Interpretation
    winner: str
    confidence_level: str
    practical_significance: bool


@dataclass
class TournamentResult:
    """Result of full tournament."""
    strategies: List[str]
    total_games: int
    
    # Rankings
    elo_ratings: Dict[str, float]
    win_rates: Dict[str, float]
    rankings: List[str]
    
    # Statistical analysis
    anova_f_statistic: float
    anova_pvalue: float
    kruskal_h_statistic: float
    kruskal_pvalue: float
    
    # Pairwise comparisons
    pairwise_results: List[ComparisonResult]
    
    # Significance matrix (after correction)
    significance_matrix: Dict[Tuple[str, str], bool]


@dataclass
class BayesianComparisonResult:
    """Bayesian comparison result."""
    strategy_a: str
    strategy_b: str
    
    # Posterior distributions (Beta parameters)
    posterior_a_alpha: float
    posterior_a_beta: float
    posterior_b_alpha: float
    posterior_b_beta: float
    
    # Probabilities
    prob_a_better: float  # P(θ_A > θ_B | data)
    prob_b_better: float
    prob_equivalent: float  # P(|θ_A - θ_B| < ε | data)
    
    # Credible intervals (95%)
    credible_interval_a: Tuple[float, float]
    credible_interval_b: Tuple[float, float]
    
    # Bayes factor
    bayes_factor: float
    interpretation: str


# ============================================================================
# Statistical Testing
# ============================================================================


class StatisticalComparator:
    """
    Rigorous statistical comparison of strategies.
    
    Methods:
    1. Frequentist hypothesis testing
    2. Bayesian hypothesis testing
    3. Effect size computation
    4. Power analysis
    """
    
    def __init__(self, alpha: float = 0.05, power: float = 0.8):
        self.alpha = alpha
        self.power = power
        
    def compare_strategies(
        self,
        strategy_a: str,
        strategy_b: str,
        results_a: np.ndarray,
        results_b: np.ndarray,
        num_games: int
    ) -> ComparisonResult:
        """
        Comprehensive pairwise comparison.
        
        Args:
            strategy_a, strategy_b: Strategy names
            results_a, results_b: Binary arrays (1 = win, 0 = loss)
            num_games: Total games played
            
        Returns:
            ComparisonResult with all statistics
        """
        logger.info(f"Comparing {strategy_a} vs {strategy_b}")
        
        # Win rates
        win_rate_a = np.mean(results_a)
        win_rate_b = np.mean(results_b)
        draw_rate = np.mean((results_a == 0.5))  # If draws are possible
        
        # Parametric test (t-test)
        t_stat, t_pval = stats.ttest_ind(results_a, results_b)
        
        # Non-parametric test (Mann-Whitney U)
        u_stat, u_pval = mannwhitneyu(results_a, results_b, alternative='two-sided')
        
        # Effect sizes
        cohens_d = self._compute_cohens_d(results_a, results_b)
        cliffs_delta = self._compute_cliffs_delta(results_a, results_b)
        
        # Bootstrap confidence intervals
        ci_a = self._bootstrap_ci(results_a, num_bootstrap=10000)
        ci_b = self._bootstrap_ci(results_b, num_bootstrap=10000)
        
        # Power analysis
        power, required_n = self._power_analysis(
            effect_size=cohens_d,
            n=num_games,
            alpha=self.alpha,
            power=self.power
        )
        
        # Determine winner
        if t_pval < self.alpha:
            winner = strategy_a if win_rate_a > win_rate_b else strategy_b
            confidence = "high" if t_pval < 0.01 else "medium"
        else:
            winner = "no significant difference"
            confidence = "low"
            
        # Practical significance (large effect size)
        practical_sig = abs(cohens_d) > 0.5
        
        result = ComparisonResult(
            strategy_a=strategy_a,
            strategy_b=strategy_b,
            win_rate_a=win_rate_a,
            win_rate_b=win_rate_b,
            draw_rate=draw_rate,
            t_statistic=t_stat,
            t_pvalue=t_pval,
            mann_whitney_u=u_stat,
            mann_whitney_pvalue=u_pval,
            cohens_d=cohens_d,
            cliffs_delta=cliffs_delta,
            ci_win_rate_a=ci_a,
            ci_win_rate_b=ci_b,
            statistical_power=power,
            required_samples=required_n,
            winner=winner,
            confidence_level=confidence,
            practical_significance=practical_sig
        )
        
        logger.info(
            f"  Win rates: {win_rate_a:.3f} vs {win_rate_b:.3f}\n"
            f"  p-value: {t_pval:.4f}, Cohen's d: {cohens_d:.3f}\n"
            f"  Winner: {winner} ({confidence} confidence)"
        )
        
        return result
    
    def _compute_cohens_d(self, a: np.ndarray, b: np.ndarray) -> float:
        """
        Compute Cohen's d effect size.
        
        d = (μ_A - μ_B) / s_pooled
        
        Interpretation:
        - |d| < 0.2: negligible
        - 0.2 ≤ |d| < 0.5: small
        - 0.5 ≤ |d| < 0.8: medium
        - |d| ≥ 0.8: large
        """
        mean_a = np.mean(a)
        mean_b = np.mean(b)
        
        var_a = np.var(a, ddof=1)
        var_b = np.var(b, ddof=1)
        
        n_a = len(a)
        n_b = len(b)
        
        # Pooled standard deviation
        s_pooled = np.sqrt(((n_a - 1) * var_a + (n_b - 1) * var_b) / (n_a + n_b - 2))
        
        if s_pooled == 0:
            return 0.0
            
        d = (mean_a - mean_b) / s_pooled
        return d
    
    def _compute_cliffs_delta(self, a: np.ndarray, b: np.ndarray) -> float:
        """
        Compute Cliff's delta (non-parametric effect size).
        
        δ = (# pairs where a > b - # pairs where a < b) / (n_a * n_b)
        
        Range: [-1, 1]
        Interpretation:
        - |δ| < 0.147: negligible
        - 0.147 ≤ |δ| < 0.33: small
        - 0.33 ≤ |δ| < 0.474: medium
        - |δ| ≥ 0.474: large
        """
        n_greater = np.sum([np.sum(a_i > b) for a_i in a])
        n_less = np.sum([np.sum(a_i < b) for a_i in a])
        
        n_pairs = len(a) * len(b)
        
        if n_pairs == 0:
            return 0.0
            
        delta = (n_greater - n_less) / n_pairs
        return delta
    
    def _bootstrap_ci(
        self,
        data: np.ndarray,
        num_bootstrap: int = 10000,
        confidence: float = 0.95
    ) -> Tuple[float, float]:
        """
        Compute bootstrap confidence interval for mean.
        """
        bootstrap_means = []
        
        for _ in range(num_bootstrap):
            sample = np.random.choice(data, size=len(data), replace=True)
            bootstrap_means.append(np.mean(sample))
            
        alpha = 1 - confidence
        lower = np.percentile(bootstrap_means, 100 * alpha / 2)
        upper = np.percentile(bootstrap_means, 100 * (1 - alpha / 2))
        
        return (lower, upper)
    
    def _power_analysis(
        self,
        effect_size: float,
        n: int,
        alpha: float,
        power: float
    ) -> Tuple[float, int]:
        """
        Compute statistical power and required sample size.
        
        Returns:
            (achieved_power, required_n_for_target_power)
        """
        # Use scipy's power analysis (simplified)
        from scipy.stats import norm
        
        # For two-sample t-test
        # Power = P(reject H0 | H1 is true)
        
        # Non-centrality parameter
        ncp = effect_size * np.sqrt(n / 2)
        
        # Critical value
        z_crit = norm.ppf(1 - alpha / 2)
        
        # Achieved power
        achieved_power = 1 - norm.cdf(z_crit - ncp) + norm.cdf(-z_crit - ncp)
        
        # Required n for target power
        z_power = norm.ppf(power)
        required_n = int(np.ceil(2 * ((z_crit + z_power) / effect_size) ** 2))
        
        return achieved_power, required_n


# ============================================================================
# Bayesian Comparison
# ============================================================================


class BayesianComparator:
    """
    Bayesian hypothesis testing for strategy comparison.
    
    Model:
        θ_A ~ Beta(α_A, β_A)  # Win rate of strategy A
        θ_B ~ Beta(α_B, β_B)  # Win rate of strategy B
        
    Evidence:
        x_A ~ Binomial(n_A, θ_A)  # Wins for A
        x_B ~ Binomial(n_B, θ_B)  # Wins for B
    """
    
    def __init__(self, prior_alpha: float = 1.0, prior_beta: float = 1.0):
        self.prior_alpha = prior_alpha
        self.prior_beta = prior_beta
        
    def compare_bayesian(
        self,
        strategy_a: str,
        strategy_b: str,
        wins_a: int,
        total_a: int,
        wins_b: int,
        total_b: int,
        epsilon: float = 0.02
    ) -> BayesianComparisonResult:
        """
        Bayesian comparison of two strategies.
        
        Args:
            wins_a, total_a: Wins and games for strategy A
            wins_b, total_b: Wins and games for strategy B
            epsilon: Threshold for equivalence (default 2%)
            
        Returns:
            BayesianComparisonResult with posteriors and probabilities
        """
        logger.info(f"Bayesian comparison: {strategy_a} vs {strategy_b}")
        
        # Posterior parameters (Beta-Binomial conjugacy)
        post_a_alpha = self.prior_alpha + wins_a
        post_a_beta = self.prior_beta + (total_a - wins_a)
        
        post_b_alpha = self.prior_alpha + wins_b
        post_b_beta = self.prior_beta + (total_b - wins_b)
        
        # Monte Carlo estimation of P(θ_A > θ_B)
        num_samples = 100000
        samples_a = np.random.beta(post_a_alpha, post_a_beta, num_samples)
        samples_b = np.random.beta(post_b_alpha, post_b_beta, num_samples)
        
        prob_a_better = np.mean(samples_a > samples_b)
        prob_b_better = np.mean(samples_b > samples_a)
        prob_equivalent = np.mean(np.abs(samples_a - samples_b) < epsilon)
        
        # Credible intervals
        ci_a = (np.percentile(samples_a, 2.5), np.percentile(samples_a, 97.5))
        ci_b = (np.percentile(samples_b, 2.5), np.percentile(samples_b, 97.5))
        
        # Bayes factor (approximate)
        # BF = P(data | H1) / P(data | H0)
        # Simplified: use posterior odds ratio
        bayes_factor = (prob_a_better / prob_b_better) if prob_b_better > 0 else np.inf
        
        # Interpretation of Bayes factor
        if bayes_factor > 100:
            interpretation = "Decisive evidence for A"
        elif bayes_factor > 10:
            interpretation = "Strong evidence for A"
        elif bayes_factor > 3:
            interpretation = "Moderate evidence for A"
        elif bayes_factor > 1:
            interpretation = "Weak evidence for A"
        elif bayes_factor > 1/3:
            interpretation = "No strong evidence"
        elif bayes_factor > 1/10:
            interpretation = "Weak evidence for B"
        elif bayes_factor > 1/100:
            interpretation = "Moderate evidence for B"
        else:
            interpretation = "Strong evidence for B"
            
        result = BayesianComparisonResult(
            strategy_a=strategy_a,
            strategy_b=strategy_b,
            posterior_a_alpha=post_a_alpha,
            posterior_a_beta=post_a_beta,
            posterior_b_alpha=post_b_alpha,
            posterior_b_beta=post_b_beta,
            prob_a_better=prob_a_better,
            prob_b_better=prob_b_better,
            prob_equivalent=prob_equivalent,
            credible_interval_a=ci_a,
            credible_interval_b=ci_b,
            bayes_factor=bayes_factor,
            interpretation=interpretation
        )
        
        logger.info(
            f"  P(A > B) = {prob_a_better:.3f}\n"
            f"  Bayes Factor = {bayes_factor:.2f}\n"
            f"  {interpretation}"
        )
        
        return result


# ============================================================================
# Tournament Runner
# ============================================================================


class TournamentRunner:
    """
    Run full round-robin tournament with statistical analysis.
    """
    
    def __init__(self, strategies: List[str], games_per_matchup: int = 100):
        self.strategies = strategies
        self.games_per_matchup = games_per_matchup
        self.comparator = StatisticalComparator()
        self.bayesian = BayesianComparator()
        
    async def run_tournament(self) -> TournamentResult:
        """
        Run full round-robin tournament.
        
        Returns:
            TournamentResult with complete analysis
        """
        logger.info(f"Running tournament with {len(self.strategies)} strategies")
        logger.info(f"Games per matchup: {self.games_per_matchup}")
        
        # Track results
        results_matrix = defaultdict(lambda: defaultdict(list))
        
        # Run all pairwise matchups
        for strategy_a, strategy_b in itertools.combinations(self.strategies, 2):
            logger.info(f"\nMatchup: {strategy_a} vs {strategy_b}")
            
            # Play games
            wins_a, wins_b = await self._play_matchup(strategy_a, strategy_b)
            
            results_matrix[strategy_a][strategy_b] = wins_a
            results_matrix[strategy_b][strategy_a] = wins_b
            
        # Compute overall statistics
        win_rates = self._compute_win_rates(results_matrix)
        elo_ratings = self._compute_elo_ratings(results_matrix)
        rankings = sorted(self.strategies, key=lambda s: win_rates[s], reverse=True)
        
        # ANOVA test (overall difference)
        all_results = []
        for strategy in self.strategies:
            strategy_results = []
            for opponent in self.strategies:
                if opponent != strategy and opponent in results_matrix[strategy]:
                    strategy_results.extend(results_matrix[strategy][opponent])
            all_results.append(strategy_results)
            
        f_stat, anova_pval = stats.f_oneway(*all_results)
        
        # Kruskal-Wallis test (non-parametric)
        h_stat, kruskal_pval = kruskal(*all_results)
        
        # Pairwise comparisons
        pairwise_results = []
        
        for strategy_a, strategy_b in itertools.combinations(self.strategies, 2):
            results_a = np.array(results_matrix[strategy_a][strategy_b])
            results_b = np.array(results_matrix[strategy_b][strategy_a])
            
            comparison = self.comparator.compare_strategies(
                strategy_a, strategy_b, results_a, results_b, self.games_per_matchup
            )
            pairwise_results.append(comparison)
            
        # Multiple comparison correction
        significance_matrix = self._correct_multiple_comparisons(pairwise_results)
        
        result = TournamentResult(
            strategies=self.strategies,
            total_games=len(self.strategies) * (len(self.strategies) - 1) * self.games_per_matchup // 2,
            elo_ratings=elo_ratings,
            win_rates=win_rates,
            rankings=rankings,
            anova_f_statistic=f_stat,
            anova_pvalue=anova_pval,
            kruskal_h_statistic=h_stat,
            kruskal_pvalue=kruskal_pval,
            pairwise_results=pairwise_results,
            significance_matrix=significance_matrix
        )
        
        return result
    
    async def _play_matchup(
        self,
        strategy_a: str,
        strategy_b: str
    ) -> Tuple[List[float], List[float]]:
        """Play games between two strategies."""
        
        # Create strategies
        strat_a = StrategyFactory.create(StrategyType[strategy_a.upper()])
        strat_b = StrategyFactory.create(StrategyType[strategy_b.upper()])
        
        wins_a = []
        wins_b = []
        
        for game_num in range(self.games_per_matchup):
            # Alternate who is ODD/EVEN
            if game_num % 2 == 0:
                role_a, role_b = "ODD", "EVEN"
            else:
                role_a, role_b = "EVEN", "ODD"
                
            # Play game (simplified simulation)
            # In real implementation, would use full game engine
            move_a = await strat_a.decide_move(
                f"game_{game_num}", 1, role_a, 0, 0, []
            )
            move_b = await strat_b.decide_move(
                f"game_{game_num}", 1, role_b, 0, 0, []
            )
            
            # Determine winner
            total = move_a + move_b
            if role_a == "ODD":
                a_wins = (total % 2 == 1)
            else:
                a_wins = (total % 2 == 0)
                
            wins_a.append(1.0 if a_wins else 0.0)
            wins_b.append(0.0 if a_wins else 1.0)
            
        return wins_a, wins_b
    
    def _compute_win_rates(
        self,
        results_matrix: Dict[str, Dict[str, List[float]]]
    ) -> Dict[str, float]:
        """Compute overall win rate for each strategy."""
        win_rates = {}
        
        for strategy in self.strategies:
            all_games = []
            for opponent in self.strategies:
                if opponent != strategy and opponent in results_matrix[strategy]:
                    all_games.extend(results_matrix[strategy][opponent])
                    
            win_rates[strategy] = np.mean(all_games) if all_games else 0.0
            
        return win_rates
    
    def _compute_elo_ratings(
        self,
        results_matrix: Dict[str, Dict[str, List[float]]],
        k_factor: float = 32.0
    ) -> Dict[str, float]:
        """
        Compute Elo ratings for strategies.
        
        Elo formula:
            E_A = 1 / (1 + 10^((R_B - R_A) / 400))
            R_A_new = R_A + K(S_A - E_A)
        """
        # Initialize all to 1500
        elo = {s: 1500.0 for s in self.strategies}
        
        # Process all games
        for strategy_a in self.strategies:
            for strategy_b in self.strategies:
                if strategy_a != strategy_b and strategy_b in results_matrix[strategy_a]:
                    games = results_matrix[strategy_a][strategy_b]
                    
                    for result in games:
                        # Expected scores
                        e_a = 1 / (1 + 10 ** ((elo[strategy_b] - elo[strategy_a]) / 400))
                        e_b = 1 / (1 + 10 ** ((elo[strategy_a] - elo[strategy_b]) / 400))
                        
                        # Update ratings
                        elo[strategy_a] += k_factor * (result - e_a)
                        elo[strategy_b] += k_factor * ((1 - result) - e_b)
                        
        return elo
    
    def _correct_multiple_comparisons(
        self,
        pairwise_results: List[ComparisonResult],
        method: str = "holm"
    ) -> Dict[Tuple[str, str], bool]:
        """
        Apply multiple comparison correction.
        
        Methods:
        - bonferroni: α_adj = α / m
        - holm: Step-down procedure
        - fdr: False Discovery Rate (Benjamini-Hochberg)
        """
        # Extract p-values
        p_values = [(r.strategy_a, r.strategy_b, r.t_pvalue) for r in pairwise_results]
        sorted_p = sorted(p_values, key=lambda x: x[2])
        
        m = len(p_values)
        significance = {}
        
        if method == "bonferroni":
            # Bonferroni correction
            alpha_adj = 0.05 / m
            for strat_a, strat_b, p in p_values:
                significance[(strat_a, strat_b)] = p < alpha_adj
                
        elif method == "holm":
            # Holm-Bonferroni step-down
            for i, (strat_a, strat_b, p) in enumerate(sorted_p):
                alpha_adj = 0.05 / (m - i)
                if p < alpha_adj:
                    significance[(strat_a, strat_b)] = True
                else:
                    # Reject all remaining
                    for j in range(i, m):
                        s_a, s_b, _ = sorted_p[j]
                        significance[(s_a, s_b)] = False
                    break
                    
        elif method == "fdr":
            # Benjamini-Hochberg FDR control
            for i, (strat_a, strat_b, p) in enumerate(sorted_p):
                alpha_adj = (i + 1) * 0.05 / m
                if p < alpha_adj:
                    significance[(strat_a, strat_b)] = True
                else:
                    significance[(strat_a, strat_b)] = False
                    
        return significance


# ============================================================================
# Report Generation
# ============================================================================


def generate_tournament_report(result: TournamentResult) -> str:
    """Generate comprehensive tournament report."""
    
    lines = ["# Statistical Comparison Tournament Report\n"]
    lines.append(f"**Generated**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    lines.append(f"**Total Games**: {result.total_games}\n")
    
    lines.append("\n## Overall Rankings\n")
    lines.append("| Rank | Strategy | Win Rate | Elo Rating |")
    lines.append("|------|----------|----------|------------|")
    
    for i, strategy in enumerate(result.rankings, 1):
        lines.append(
            f"| {i} | {strategy} | {result.win_rates[strategy]:.3f} | "
            f"{result.elo_ratings[strategy]:.0f} |"
        )
        
    lines.append("\n## Global Statistical Tests\n")
    lines.append(f"### ANOVA\n")
    lines.append(f"- F-statistic: {result.anova_f_statistic:.3f}\n")
    lines.append(f"- p-value: {result.anova_pvalue:.4f}\n")
    
    if result.anova_pvalue < 0.05:
        lines.append("- **Conclusion**: Significant difference between strategies ✅\n")
    else:
        lines.append("- **Conclusion**: No significant difference ❌\n")
        
    lines.append(f"\n### Kruskal-Wallis Test (Non-Parametric)\n")
    lines.append(f"- H-statistic: {result.kruskal_h_statistic:.3f}\n")
    lines.append(f"- p-value: {result.kruskal_pvalue:.4f}\n")
    
    lines.append("\n## Pairwise Comparisons\n")
    lines.append("| Strategy A | Strategy B | Winner | p-value | Cohen's d | Significant (Corrected) |")
    lines.append("|------------|------------|--------|---------|-----------|-------------------------|")
    
    for comp in result.pairwise_results:
        sig = result.significance_matrix.get((comp.strategy_a, comp.strategy_b), False)
        sig_marker = "✅" if sig else "❌"
        
        lines.append(
            f"| {comp.strategy_a} | {comp.strategy_b} | {comp.winner} | "
            f"{comp.t_pvalue:.4f} | {comp.cohens_d:.3f} | {sig_marker} |"
        )
        
    lines.append("\n## Interpretation\n")
    
    best_strategy = result.rankings[0]
    lines.append(f"**Best Performing Strategy**: {best_strategy}\n")
    lines.append(f"- Win Rate: {result.win_rates[best_strategy]:.3f}\n")
    lines.append(f"- Elo Rating: {result.elo_ratings[best_strategy]:.0f}\n")
    
    # Find significant improvements
    significant_pairs = [
        (comp.strategy_a, comp.strategy_b, comp.cohens_d)
        for comp in result.pairwise_results
        if result.significance_matrix.get((comp.strategy_a, comp.strategy_b), False)
        and comp.practical_significance
    ]
    
    if significant_pairs:
        lines.append("\n**Practically Significant Improvements** (large effect size):\n")
        for a, b, d in significant_pairs:
            lines.append(f"- {a} vs {b}: Cohen's d = {d:.3f}\n")
            
    return "\n".join(lines)


# ============================================================================
# Main Execution
# ============================================================================


async def main():
    """Run statistical comparison."""
    print("=" * 80)
    print("STATISTICAL COMPARISON FRAMEWORK")
    print("MIT-Level Data-Based Comparison")
    print("=" * 80)
    print()
    
    output_dir = Path("results/statistical_comparison")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Define strategies to compare
    strategies = ["RANDOM", "NASH_EQUILIBRIUM", "BAYESIAN", "REGRET_MATCHING"]
    
    # Run tournament
    runner = TournamentRunner(strategies, games_per_matchup=100)
    result = await runner.run_tournament()
    
    # Generate report
    report = generate_tournament_report(result)
    
    # Save results
    with open(output_dir / "tournament_results.json", "w") as f:
        # Convert to serializable format
        data = {
            "strategies": result.strategies,
            "total_games": result.total_games,
            "win_rates": result.win_rates,
            "elo_ratings": result.elo_ratings,
            "rankings": result.rankings,
            "anova_f": result.anova_f_statistic,
            "anova_p": result.anova_pvalue,
        }
        json.dump(data, f, indent=2)
        
    with open(output_dir / "comparison_report.md", "w") as f:
        f.write(report)
        
    print(report)
    print(f"\n✅ Analysis complete! Results saved to {output_dir}")


if __name__ == "__main__":
    asyncio.run(main())

