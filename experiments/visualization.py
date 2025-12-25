"""
Research-Grade Visualization Framework
=======================================

Publication-ready visualizations for research papers:
1. Strategy comparison heatmaps
2. Sensitivity analysis plots (tornado diagrams, scatter plots)
3. Convergence plots with confidence bands
4. Performance distributions (violin plots, box plots)
5. ELO rating evolution over time
6. Bayesian posterior distributions
7. Interactive HTML dashboards

Uses matplotlib, seaborn, and plotly for static and interactive plots.

Usage:
    python experiments/visualization.py --results results/ --output figures/
"""

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import json
from typing import Dict, List, Any, Optional
import pandas as pd
from scipy import stats

# Set publication-quality defaults
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.size'] = 10
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['xtick.labelsize'] = 10
plt.rcParams['ytick.labelsize'] = 10
plt.rcParams['legend.fontsize'] = 10
plt.rcParams['figure.titlesize'] = 16

# Color palettes
STRATEGY_COLORS = {
    'nash': '#1f77b4',
    'bayesian': '#ff7f0e',
    'regret_matching': '#2ca02c',
    'fictitious_play': '#d62728',
    'ucb': '#9467bd',
    'thompson': '#8c564b',
    'random': '#7f7f7f',
}


class ResearchVisualizer:
    """
    Create publication-ready visualizations for research papers.
    """
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Use seaborn style
        sns.set_style("whitegrid")
        sns.set_palette("husl")
        
    def plot_sensitivity_tornado(
        self,
        sobol_results: List[Dict],
        filename: str = "sensitivity_tornado.pdf"
    ):
        """
        Create tornado diagram for Sobol indices.
        
        Shows first-order and total-order indices side-by-side.
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Extract data
        params = [r['parameter_name'] for r in sobol_results]
        s1 = [r['first_order'] for r in sobol_results]
        st = [r['total_order'] for r in sobol_results]
        
        # Sort by total order
        sorted_indices = sorted(range(len(st)), key=lambda i: st[i], reverse=True)
        params = [params[i] for i in sorted_indices]
        s1 = [s1[i] for i in sorted_indices]
        st = [st[i] for i in sorted_indices]
        
        # Create horizontal bars
        y_pos = np.arange(len(params))
        
        ax.barh(y_pos - 0.2, s1, height=0.4, label='First-order ($S_1$)', 
                color='#1f77b4', alpha=0.8)
        ax.barh(y_pos + 0.2, st, height=0.4, label='Total-order ($S_T$)', 
                color='#ff7f0e', alpha=0.8)
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels(params)
        ax.set_xlabel('Sobol Index')
        ax.set_title('Parameter Sensitivity Analysis (Sobol Indices)')
        ax.legend(loc='lower right')
        ax.grid(axis='x', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / filename, bbox_inches='tight')
        plt.close()
        
        print(f"✅ Saved: {filename}")
        
    def plot_sensitivity_scatter(
        self,
        morris_results: List[Dict],
        filename: str = "sensitivity_scatter.pdf"
    ):
        """
        Create Morris screening scatter plot.
        
        μ* vs σ with classification regions.
        """
        fig, ax = plt.subplots(figsize=(8, 8))
        
        # Extract data
        params = [r['parameter_name'] for r in morris_results]
        mu_star = [r['mu_star'] for r in morris_results]
        sigma = [r['sigma'] for r in morris_results]
        
        # Plot points
        scatter = ax.scatter(mu_star, sigma, s=200, alpha=0.7, 
                           c=range(len(params)), cmap='viridis')
        
        # Add labels
        for i, param in enumerate(params):
            ax.annotate(param, (mu_star[i], sigma[i]), 
                       xytext=(5, 5), textcoords='offset points',
                       fontsize=9, alpha=0.8)
        
        # Add classification regions
        ax.axvline(x=10, color='red', linestyle='--', alpha=0.5, 
                  label='High importance threshold')
        ax.axhline(y=5, color='blue', linestyle='--', alpha=0.5, 
                  label='High non-linearity threshold')
        
        ax.set_xlabel('$\\mu^*$ (Importance)', fontsize=12)
        ax.set_ylabel('$\\sigma$ (Non-linearity/Interaction)', fontsize=12)
        ax.set_title('Morris Screening: Parameter Classification')
        ax.legend()
        ax.grid(alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / filename, bbox_inches='tight')
        plt.close()
        
        print(f"✅ Saved: {filename}")
        
    def plot_strategy_comparison_heatmap(
        self,
        win_matrix: np.ndarray,
        strategy_names: List[str],
        filename: str = "strategy_heatmap.pdf"
    ):
        """
        Create heatmap of pairwise win rates.
        
        Args:
            win_matrix: (n, n) matrix where [i,j] = win rate of i vs j
            strategy_names: List of strategy names
        """
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Create mask for diagonal
        mask = np.eye(len(strategy_names), dtype=bool)
        
        # Plot heatmap
        sns.heatmap(win_matrix, 
                   mask=mask,
                   annot=True, 
                   fmt='.3f',
                   cmap='RdYlGn',
                   center=0.5,
                   vmin=0, 
                   vmax=1,
                   xticklabels=strategy_names,
                   yticklabels=strategy_names,
                   cbar_kws={'label': 'Win Rate'},
                   ax=ax)
        
        ax.set_title('Strategy Head-to-Head Win Rates')
        ax.set_xlabel('Opponent Strategy')
        ax.set_ylabel('Player Strategy')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / filename, bbox_inches='tight')
        plt.close()
        
        print(f"✅ Saved: {filename}")
        
    def plot_performance_distributions(
        self,
        results_by_strategy: Dict[str, List[float]],
        filename: str = "performance_distributions.pdf"
    ):
        """
        Create violin plots of performance distributions.
        """
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Prepare data
        data = []
        strategies = []
        for strategy, results in results_by_strategy.items():
            data.extend(results)
            strategies.extend([strategy] * len(results))
            
        df = pd.DataFrame({'Strategy': strategies, 'Win Rate': data})
        
        # Create violin plot
        sns.violinplot(data=df, x='Strategy', y='Win Rate', ax=ax, 
                      inner='box', palette='Set2')
        
        # Add mean markers
        means = df.groupby('Strategy')['Win Rate'].mean()
        ax.scatter(range(len(means)), means, color='red', s=100, 
                  zorder=10, label='Mean', marker='D')
        
        ax.set_title('Performance Distribution by Strategy')
        ax.set_ylabel('Win Rate')
        ax.axhline(y=0.5, color='gray', linestyle='--', alpha=0.5, 
                  label='Random baseline')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / filename, bbox_inches='tight')
        plt.close()
        
        print(f"✅ Saved: {filename}")
        
    def plot_convergence(
        self,
        convergence_data: Dict[str, List[Tuple[int, float, float]]],
        filename: str = "convergence.pdf"
    ):
        """
        Plot strategy convergence with confidence bands.
        
        Args:
            convergence_data: {strategy: [(round, mean, std), ...]}
        """
        fig, ax = plt.subplots(figsize=(12, 6))
        
        for strategy, data in convergence_data.items():
            rounds = [d[0] for d in data]
            means = [d[1] for d in data]
            stds = [d[2] for d in data]
            
            color = STRATEGY_COLORS.get(strategy.lower(), None)
            
            # Plot mean line
            ax.plot(rounds, means, label=strategy, linewidth=2, color=color)
            
            # Plot confidence band (95% CI assuming normal)
            means_arr = np.array(means)
            stds_arr = np.array(stds)
            ci_upper = means_arr + 1.96 * stds_arr
            ci_lower = means_arr - 1.96 * stds_arr
            
            ax.fill_between(rounds, ci_lower, ci_upper, alpha=0.2, color=color)
            
        ax.set_xlabel('Round Number')
        ax.set_ylabel('Cumulative Win Rate')
        ax.set_title('Strategy Convergence Over Time')
        ax.axhline(y=0.5, color='gray', linestyle='--', alpha=0.5, 
                  label='Nash Equilibrium')
        ax.legend(loc='best')
        ax.grid(alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / filename, bbox_inches='tight')
        plt.close()
        
        print(f"✅ Saved: {filename}")
        
    def plot_elo_evolution(
        self,
        elo_history: Dict[str, List[Tuple[int, float]]],
        filename: str = "elo_evolution.pdf"
    ):
        """
        Plot ELO rating evolution over games.
        """
        fig, ax = plt.subplots(figsize=(12, 6))
        
        for strategy, history in elo_history.items():
            games = [h[0] for h in history]
            ratings = [h[1] for h in history]
            
            color = STRATEGY_COLORS.get(strategy.lower(), None)
            ax.plot(games, ratings, label=strategy, linewidth=2, color=color)
            
        ax.set_xlabel('Game Number')
        ax.set_ylabel('ELO Rating')
        ax.set_title('ELO Rating Evolution')
        ax.axhline(y=1500, color='gray', linestyle='--', alpha=0.5, 
                  label='Initial Rating')
        ax.legend(loc='best')
        ax.grid(alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / filename, bbox_inches='tight')
        plt.close()
        
        print(f"✅ Saved: {filename}")
        
    def plot_bayesian_posteriors(
        self,
        posterior_params: Dict[str, Tuple[float, float]],
        filename: str = "bayesian_posteriors.pdf"
    ):
        """
        Plot Beta posterior distributions for strategies.
        
        Args:
            posterior_params: {strategy: (alpha, beta)}
        """
        fig, ax = plt.subplots(figsize=(12, 6))
        
        x = np.linspace(0, 1, 1000)
        
        for strategy, (alpha, beta) in posterior_params.items():
            # Beta distribution
            y = stats.beta.pdf(x, alpha, beta)
            
            color = STRATEGY_COLORS.get(strategy.lower(), None)
            ax.plot(x, y, label=f'{strategy} (α={alpha:.1f}, β={beta:.1f})', 
                   linewidth=2, color=color)
            
            # Add mean line
            mean = alpha / (alpha + beta)
            ax.axvline(mean, color=color, linestyle='--', alpha=0.5, linewidth=1)
            
        ax.set_xlabel('Win Rate θ')
        ax.set_ylabel('Posterior Density p(θ | data)')
        ax.set_title('Bayesian Posterior Distributions')
        ax.legend(loc='best')
        ax.grid(alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / filename, bbox_inches='tight')
        plt.close()
        
        print(f"✅ Saved: {filename}")
        
    def plot_effect_sizes(
        self,
        comparisons: List[Dict],
        filename: str = "effect_sizes.pdf"
    ):
        """
        Plot effect sizes for pairwise comparisons.
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # Extract data
        labels = [f"{c['strategy_a']}\nvs\n{c['strategy_b']}" 
                 for c in comparisons]
        cohens_d = [c['cohens_d'] for c in comparisons]
        cliffs_delta = [c['cliffs_delta'] for c in comparisons]
        
        # Cohen's d
        colors_d = ['green' if abs(d) >= 0.8 else 'orange' if abs(d) >= 0.5 
                   else 'yellow' if abs(d) >= 0.2 else 'gray' 
                   for d in cohens_d]
        
        ax1.barh(range(len(labels)), cohens_d, color=colors_d, alpha=0.7)
        ax1.set_yticks(range(len(labels)))
        ax1.set_yticklabels(labels, fontsize=8)
        ax1.set_xlabel("Cohen's d")
        ax1.set_title("Cohen's d Effect Size")
        ax1.axvline(0.2, color='gray', linestyle='--', alpha=0.5)
        ax1.axvline(0.5, color='orange', linestyle='--', alpha=0.5)
        ax1.axvline(0.8, color='red', linestyle='--', alpha=0.5)
        ax1.axvline(0, color='black', linestyle='-', linewidth=0.5)
        ax1.grid(axis='x', alpha=0.3)
        
        # Cliff's delta
        colors_cliff = ['green' if abs(d) >= 0.474 else 'orange' if abs(d) >= 0.33 
                       else 'yellow' if abs(d) >= 0.147 else 'gray' 
                       for d in cliffs_delta]
        
        ax2.barh(range(len(labels)), cliffs_delta, color=colors_cliff, alpha=0.7)
        ax2.set_yticks(range(len(labels)))
        ax2.set_yticklabels(labels, fontsize=8)
        ax2.set_xlabel("Cliff's Delta")
        ax2.set_title("Cliff's Delta Effect Size")
        ax2.axvline(0.147, color='gray', linestyle='--', alpha=0.5)
        ax2.axvline(0.33, color='orange', linestyle='--', alpha=0.5)
        ax2.axvline(0.474, color='red', linestyle='--', alpha=0.5)
        ax2.axvline(0, color='black', linestyle='-', linewidth=0.5)
        ax2.grid(axis='x', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / filename, bbox_inches='tight')
        plt.close()
        
        print(f"✅ Saved: {filename}")
        
    def create_multi_panel_figure(
        self,
        panels: List[Tuple[str, str]],  # [(title, filepath), ...]
        filename: str = "multi_panel.pdf",
        layout: Tuple[int, int] = (2, 2)
    ):
        """
        Combine multiple plots into a single multi-panel figure.
        """
        fig, axes = plt.subplots(*layout, figsize=(16, 12))
        axes = axes.flatten() if isinstance(axes, np.ndarray) else [axes]
        
        for ax, (title, filepath) in zip(axes, panels):
            # Load and display image
            img = plt.imread(filepath)
            ax.imshow(img)
            ax.set_title(title, fontsize=12, fontweight='bold')
            ax.axis('off')
            
        # Hide unused subplots
        for ax in axes[len(panels):]:
            ax.axis('off')
            
        plt.tight_layout()
        plt.savefig(self.output_dir / filename, bbox_inches='tight', dpi=300)
        plt.close()
        
        print(f"✅ Saved: {filename}")
        
    def generate_html_dashboard(
        self,
        results_dir: Path,
        filename: str = "dashboard.html"
    ):
        """
        Generate interactive HTML dashboard with all visualizations.
        """
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>Research Results Dashboard</title>
    <style>
        body {
            font-family: 'Arial', sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        h1 {
            color: #333;
            text-align: center;
            border-bottom: 3px solid #1f77b4;
            padding-bottom: 10px;
        }
        h2 {
            color: #555;
            margin-top: 30px;
            border-bottom: 1px solid #ccc;
            padding-bottom: 5px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        .figure {
            margin: 20px 0;
            text-align: center;
        }
        .figure img {
            max-width: 100%;
            border: 1px solid #ddd;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .caption {
            font-style: italic;
            color: #666;
            margin-top: 10px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 30px;
            margin: 20px 0;
        }
        .metrics {
            background-color: #f9f9f9;
            padding: 15px;
            border-left: 4px solid #1f77b4;
            margin: 20px 0;
        }
        .metrics h3 {
            margin-top: 0;
            color: #1f77b4;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎓 MIT-Level Research Results Dashboard</h1>
        <p style="text-align: center; color: #666;">
            Multi-Agent Game League: Comprehensive Statistical Analysis
        </p>
        
        <div class="metrics">
            <h3>Executive Summary</h3>
            <p><strong>Total Experiments:</strong> [TOTAL_EXPERIMENTS]</p>
            <p><strong>Statistical Power:</strong> [POWER]</p>
            <p><strong>Significance Level:</strong> α = 0.05</p>
            <p><strong>Generated:</strong> [TIMESTAMP]</p>
        </div>
        
        <h2>📊 1. Sensitivity Analysis</h2>
        <div class="grid">
            <div class="figure">
                <img src="sensitivity_tornado.pdf" alt="Sensitivity Tornado">
                <div class="caption">Figure 1a: Sobol Sensitivity Indices</div>
            </div>
            <div class="figure">
                <img src="sensitivity_scatter.pdf" alt="Morris Screening">
                <div class="caption">Figure 1b: Morris Screening Method</div>
            </div>
        </div>
        
        <h2>🎮 2. Strategy Comparison</h2>
        <div class="grid">
            <div class="figure">
                <img src="strategy_heatmap.pdf" alt="Strategy Heatmap">
                <div class="caption">Figure 2a: Head-to-Head Win Rates</div>
            </div>
            <div class="figure">
                <img src="performance_distributions.pdf" alt="Performance Distributions">
                <div class="caption">Figure 2b: Performance Distributions</div>
            </div>
        </div>
        
        <h2>📈 3. Convergence Analysis</h2>
        <div class="grid">
            <div class="figure">
                <img src="convergence.pdf" alt="Convergence">
                <div class="caption">Figure 3a: Strategy Convergence Over Time</div>
            </div>
            <div class="figure">
                <img src="elo_evolution.pdf" alt="ELO Evolution">
                <div class="caption">Figure 3b: ELO Rating Evolution</div>
            </div>
        </div>
        
        <h2>🔬 4. Bayesian Analysis</h2>
        <div class="figure">
            <img src="bayesian_posteriors.pdf" alt="Bayesian Posteriors">
            <div class="caption">Figure 4: Posterior Distributions</div>
        </div>
        
        <h2>📏 5. Effect Sizes</h2>
        <div class="figure">
            <img src="effect_sizes.pdf" alt="Effect Sizes">
            <div class="caption">Figure 5: Pairwise Effect Sizes</div>
        </div>
        
        <div class="metrics">
            <h3>Key Findings</h3>
            <ul>
                <li>Best performing strategy: <strong>[BEST_STRATEGY]</strong></li>
                <li>Statistically significant differences detected: <strong>[SIG_DIFFS]</strong></li>
                <li>Largest effect size: <strong>[MAX_EFFECT]</strong></li>
                <li>Most sensitive parameter: <strong>[MOST_SENSITIVE]</strong></li>
            </ul>
        </div>
        
        <footer style="text-align: center; margin-top: 50px; color: #999; border-top: 1px solid #ddd; padding-top: 20px;">
            <p>Generated by MCP Game League Research Framework</p>
            <p>© 2025 MIT-Level Research</p>
        </footer>
    </div>
</body>
</html>
"""
        
        with open(self.output_dir / filename, 'w') as f:
            f.write(html)
            
        print(f"✅ Saved: {filename}")


# ============================================================================
# Example Usage
# ============================================================================


def main():
    """Generate example visualizations."""
    print("=" * 80)
    print("RESEARCH VISUALIZATION FRAMEWORK")
    print("=" * 80)
    print()
    
    visualizer = ResearchVisualizer(Path("figures"))
    
    # Example 1: Sensitivity tornado
    sobol_results = [
        {'parameter_name': 'rate_limit', 'first_order': 0.45, 'total_order': 0.62},
        {'parameter_name': 'cache_size', 'first_order': 0.23, 'total_order': 0.35},
        {'parameter_name': 'cache_ttl', 'first_order': 0.18, 'total_order': 0.28},
        {'parameter_name': 'burst_size', 'first_order': 0.08, 'total_order': 0.12},
    ]
    visualizer.plot_sensitivity_tornado(sobol_results)
    
    # Example 2: Morris screening
    morris_results = [
        {'parameter_name': 'rate_limit', 'mu_star': 15.2, 'sigma': 8.3},
        {'parameter_name': 'cache_size', 'mu_star': 8.1, 'sigma': 3.2},
        {'parameter_name': 'cache_ttl', 'mu_star': 5.4, 'sigma': 2.1},
        {'parameter_name': 'burst_size', 'mu_star': 2.3, 'sigma': 1.1},
    ]
    visualizer.plot_sensitivity_scatter(morris_results)
    
    # Example 3: Strategy heatmap
    win_matrix = np.array([
        [0.5, 0.62, 0.58, 0.55],
        [0.38, 0.5, 0.52, 0.48],
        [0.42, 0.48, 0.5, 0.51],
        [0.45, 0.52, 0.49, 0.5]
    ])
    strategies = ['Nash', 'Bayesian', 'Regret', 'UCB']
    visualizer.plot_strategy_comparison_heatmap(win_matrix, strategies)
    
    # Example 4: Performance distributions
    results_by_strategy = {
        'Nash': np.random.normal(0.50, 0.05, 100).clip(0, 1),
        'Bayesian': np.random.normal(0.58, 0.06, 100).clip(0, 1),
        'Regret': np.random.normal(0.55, 0.05, 100).clip(0, 1),
        'UCB': np.random.normal(0.53, 0.07, 100).clip(0, 1),
    }
    visualizer.plot_performance_distributions(results_by_strategy)
    
    # Example 5: Convergence
    convergence_data = {
        'Nash': [(i, 0.50, 0.05) for i in range(1, 101)],
        'Bayesian': [(i, 0.50 + 0.08 * (1 - np.exp(-i/20)), 0.05) for i in range(1, 101)],
        'Regret': [(i, 0.50 + 0.05 * (1 - np.exp(-i/30)), 0.05) for i in range(1, 101)],
    }
    visualizer.plot_convergence(convergence_data)
    
    print("\n✅ All visualizations generated!")
    print(f"📁 Saved to: figures/")


if __name__ == "__main__":
    main()

