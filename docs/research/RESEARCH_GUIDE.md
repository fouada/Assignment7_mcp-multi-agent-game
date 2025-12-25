# Research Framework Guide
## MIT-Level Systematic Research Infrastructure

**Version**: 2.0  
**Date**: December 2025  
**Status**: Production-Ready

---

## 🎓 Overview

This document provides a comprehensive guide to the research infrastructure implemented in the MCP Game League project. The framework enables publication-quality research with systematic sensitivity analysis, rigorous statistical comparison, and mathematical proofs.

---

## 📋 Table of Contents

1. [Research Components](#research-components)
2. [Quick Start](#quick-start)
3. [Advanced Sensitivity Analysis](#advanced-sensitivity-analysis)
4. [Statistical Comparison](#statistical-comparison)
5. [Mathematical Proofs](#mathematical-proofs)
6. [Visualization](#visualization)
7. [Paper Generation](#paper-generation)
8. [Complete Pipeline](#complete-pipeline)
9. [Best Practices](#best-practices)

---

## 1. Research Components

The research framework consists of six integrated modules:

### 1.1 Advanced Sensitivity Analysis
**Location**: `experiments/advanced_sensitivity.py`

**Methods**:
- **Sobol Variance-Based Analysis**: First-order and total-order sensitivity indices
- **Morris Screening**: Parameter importance and interaction detection
- **Monte Carlo Simulation**: Uncertainty quantification
- **Latin Hypercube Sampling**: Efficient parameter space exploration

**Key Features**:
- Variance decomposition with confidence intervals
- Interaction effect quantification
- Statistical significance testing (ANOVA)
- Bootstrap confidence intervals

### 1.2 Statistical Comparison
**Location**: `experiments/statistical_comparison.py`

**Methods**:
- **Frequentist Testing**: t-test, Mann-Whitney U, ANOVA, Kruskal-Wallis
- **Bayesian Comparison**: Beta-Binomial model with posterior probabilities
- **Effect Size**: Cohen's d, Cliff's delta
- **Multiple Comparison Correction**: Bonferroni, Holm-Bonferroni, FDR

**Key Features**:
- A/B testing with power analysis
- ELO rating system
- Tournament round-robin
- Significance matrix after correction

### 1.3 Performance Benchmarking
**Location**: `experiments/benchmarks.py`

**Benchmarks**:
- Strategy algorithm comparison (Nash, Bayesian, Regret, etc.)
- Middleware configuration comparison
- Event bus vs direct calls
- Plugin loading approaches

**Key Features**:
- Repeated measurements with warmup
- Confidence intervals (95%)
- Statistical significance testing
- Performance profiling

### 1.4 Mathematical Proofs
**Location**: `docs/research/MATHEMATICAL_PROOFS.md`

**Proofs For**:
- Nash Equilibrium optimality
- Regret Matching convergence (O(1/√T))
- Bayesian posterior concentration
- UCB regret bound
- Thompson Sampling regret bound
- Complexity analysis

### 1.5 Visualization
**Location**: `experiments/visualization.py`

**Visualizations**:
- Sensitivity tornado diagrams
- Morris screening scatter plots
- Strategy comparison heatmaps
- Performance distributions (violin plots)
- Convergence plots with confidence bands
- ELO evolution
- Bayesian posterior distributions
- Effect size plots
- Interactive HTML dashboards

### 1.6 Research Paper Generator
**Location**: `experiments/research_paper_generator.py`

**Features**:
- LaTeX paper generation
- Automatic figure integration
- Results table generation
- Bibliography management
- IEEE/ACM formatting

---

## 2. Quick Start

### 2.1 Installation

```bash
# Install dependencies
uv sync --all-extras

# Verify installation
python -c "import scipy; import numpy; import pandas; import matplotlib; print('✅ Dependencies OK')"
```

### 2.2 Run Quick Analysis

```bash
# Run complete pipeline in quick mode (~10 minutes)
python experiments/run_complete_research.py --mode quick

# Results will be in: research_output/
```

### 2.3 View Results

```bash
# Open HTML dashboard
open research_output/figures/dashboard.html

# View paper (after compiling)
cd research_output/paper
pdflatex paper.tex
open paper.pdf
```

---

## 3. Advanced Sensitivity Analysis

### 3.1 Sobol Analysis

**Theory**:
```
Variance decomposition:
V(Y) = Σᵢ Vᵢ + Σᵢ<ⱼ Vᵢⱼ + ... + V₁₂...ₖ

First-order index:
Sᵢ = Vᵢ / V(Y) = V[E(Y|Xᵢ)] / V(Y)

Total-order index:
STᵢ = 1 - V[E(Y|X₋ᵢ)] / V(Y)
```

**Usage**:
```python
from experiments.advanced_sensitivity import SobolAnalyzer, PARAMETER_SPACE

# Create analyzer
sobol = SobolAnalyzer(PARAMETER_SPACE, num_samples=1024)

# Compute indices
results = await sobol.compute_sobol_indices()

for idx in results:
    print(f"{idx.parameter_name}:")
    print(f"  S₁  = {idx.first_order:.3f}")
    print(f"  ST  = {idx.total_order:.3f}")
    print(f"  Int = {idx.total_order - idx.first_order:.3f}")
```

**Interpretation**:
- **S₁ > 0.1**: High sensitivity (parameter important)
- **ST - S₁ > 0.05**: Strong interactions
- **ST < 0.05**: Negligible effect

### 3.2 Morris Screening

**Theory**:
```
Elementary effect:
EEᵢ = [f(x + Δeᵢ) - f(x)] / Δ

Metrics:
μ*ᵢ = mean of |EEᵢ| - importance
σᵢ = std of EEᵢ - non-linearity/interaction
```

**Classification**:
| μ* | σ | Interpretation |
|----|---|----------------|
| High | High | Non-linear or interacting |
| High | Low | Important and additive |
| Low | High | Interactions with others |
| Low | Low | Negligible effect |

**Usage**:
```python
from experiments.advanced_sensitivity import MorrisScreening

morris = MorrisScreening(PARAMETER_SPACE, num_trajectories=20)

async def model_func(params):
    # Your model evaluation
    return metric

results = await morris.compute_morris_measures(model_func)
```

---

## 4. Statistical Comparison

### 4.1 Tournament Setup

```python
from experiments.statistical_comparison import TournamentRunner

# Define strategies
strategies = ["NASH_EQUILIBRIUM", "BAYESIAN", "REGRET_MATCHING", "UCB"]

# Create tournament
runner = TournamentRunner(strategies, games_per_matchup=100)

# Run tournament
result = await runner.run_tournament()

# View results
print(f"Winner: {result.rankings[0]}")
print(f"Win rate: {result.win_rates[result.rankings[0]]:.3f}")
```

### 4.2 Pairwise Comparison

```python
from experiments.statistical_comparison import StatisticalComparator
import numpy as np

comparator = StatisticalComparator(alpha=0.05, power=0.8)

# Results for two strategies (1 = win, 0 = loss)
results_a = np.array([1, 1, 0, 1, 0, 1, ...])
results_b = np.array([0, 0, 1, 0, 1, 0, ...])

comparison = comparator.compare_strategies(
    "Strategy_A", "Strategy_B",
    results_a, results_b,
    num_games=100
)

print(f"Winner: {comparison.winner}")
print(f"p-value: {comparison.t_pvalue:.4f}")
print(f"Cohen's d: {comparison.cohens_d:.3f}")
print(f"Practically significant: {comparison.practical_significance}")
```

### 4.3 Bayesian Comparison

```python
from experiments.statistical_comparison import BayesianComparator

bayesian = BayesianComparator(prior_alpha=1.0, prior_beta=1.0)

result = bayesian.compare_bayesian(
    "Strategy_A", "Strategy_B",
    wins_a=58, total_a=100,
    wins_b=52, total_b=100
)

print(f"P(A > B) = {result.prob_a_better:.3f}")
print(f"Bayes Factor = {result.bayes_factor:.2f}")
print(f"{result.interpretation}")
```

**Bayes Factor Interpretation**:
| BF | Evidence |
|----|----------|
| > 100 | Decisive |
| 10-100 | Strong |
| 3-10 | Moderate |
| 1-3 | Weak |

---

## 5. Mathematical Proofs

### 5.1 Available Proofs

Location: `docs/research/MATHEMATICAL_PROOFS.md`

**Theorems Proved**:
1. **Nash Equilibrium Optimality** (Theorem 2.1)
2. **Nash Minimax Property** (Theorem 2.2)
3. **Regret Matching Convergence** (Theorem 3.1)
4. **Regret Matching Rate** (Theorem 3.2): O(1/√T)
5. **Bayesian Posterior Update** (Theorem 4.1)
6. **Bayesian Optimal Action** (Theorem 4.2)
7. **Bayesian Posterior Concentration** (Theorem 4.3)
8. **Fictitious Play Convergence** (Theorem 5.1)
9. **UCB Regret Bound** (Theorem 6.1): O(√(T ln T))
10. **Thompson Sampling Regret** (Theorem 7.1): O(√(T ln T))

### 5.2 Complexity Analysis

**Time Complexity**:
| Algorithm | Per-Decision | Total (T rounds) |
|-----------|--------------|------------------|
| Nash | O(1) | O(T) |
| Regret Matching | O(\|A\|) | O(T·\|A\|) |
| Bayesian | O(1) | O(T) |
| UCB | O(\|A\|) | O(T·\|A\|) |

**Sample Complexity to ε-Nash**:
| Algorithm | Samples |
|-----------|---------|
| Regret Matching | O(1/ε²) |
| UCB | O(log(1/ε)/ε²) |

---

## 6. Visualization

### 6.1 Create Visualizations

```python
from experiments.visualization import ResearchVisualizer
from pathlib import Path

visualizer = ResearchVisualizer(Path("figures"))

# 1. Sensitivity tornado
visualizer.plot_sensitivity_tornado(sobol_results)

# 2. Morris screening
visualizer.plot_sensitivity_scatter(morris_results)

# 3. Strategy heatmap
visualizer.plot_strategy_comparison_heatmap(win_matrix, strategy_names)

# 4. Performance distributions
visualizer.plot_performance_distributions(results_by_strategy)

# 5. Convergence
visualizer.plot_convergence(convergence_data)

# 6. ELO evolution
visualizer.plot_elo_evolution(elo_history)

# 7. Bayesian posteriors
visualizer.plot_bayesian_posteriors(posterior_params)

# 8. HTML dashboard
visualizer.generate_html_dashboard(results_dir)
```

### 6.2 Publication-Quality Settings

Already configured:
- **DPI**: 300 (publication standard)
- **Font**: Serif (LaTeX-compatible)
- **Format**: PDF (vector graphics)
- **Style**: Seaborn whitegrid
- **Colors**: ColorBlind-friendly palette

---

## 7. Paper Generation

### 7.1 Generate LaTeX Paper

```python
from experiments.research_paper_generator import ResearchPaperGenerator

generator = ResearchPaperGenerator(Path("paper"))

# Prepare results
results = {
    'best_strategy': 'Bayesian',
    'total_experiments': 10000,
    'sobol_indices': [...],
    'tournament': {...},
}

# Generate paper
latex = generator.generate_paper(
    title="Your Research Title",
    authors=["Author 1", "Author 2"],
    affiliation="Your Institution",
    results=results
)

# Save
generator.save_paper(latex)
```

### 7.2 Compile Paper

```bash
cd paper/
pdflatex paper.tex
bibtex paper
pdflatex paper.tex
pdflatex paper.tex
```

### 7.3 Paper Structure

- **Abstract**: Auto-generated from results
- **Introduction**: Motivation and contributions
- **Methodology**: Game formalization, algorithms, experimental design
- **Results**: Tables, figures, statistical tests
- **Discussion**: Interpretation, limitations
- **Conclusion**: Summary and future work
- **References**: 11 key papers cited

---

## 8. Complete Pipeline

### 8.1 Run Full Pipeline

```bash
# Full pipeline (may take hours)
python experiments/run_complete_research.py --mode full --output my_research

# Quick pipeline (~10 minutes)
python experiments/run_complete_research.py --mode quick --output quick_test

# Paper only (from existing results)
python experiments/run_complete_research.py --mode paper-only --output my_research
```

### 8.2 Pipeline Phases

**Phase 1: Sensitivity Analysis**
- Sobol variance-based analysis
- Morris screening
- Monte Carlo simulation
- Duration: 30-60 minutes (full mode)

**Phase 2: Statistical Comparison**
- Round-robin tournament
- Pairwise comparisons
- Multiple comparison correction
- Duration: 15-30 minutes

**Phase 3: Performance Benchmarking**
- Strategy benchmarks
- Middleware benchmarks
- Event bus benchmarks
- Duration: 10-20 minutes

**Phase 4: Visualization**
- All plots generated
- HTML dashboard created
- Duration: 2-5 minutes

**Phase 5: Paper Generation**
- LaTeX paper generated
- Figures integrated
- Tables populated
- Duration: 1 minute

### 8.3 Output Structure

```
research_output/
├── results/
│   ├── sensitivity_analysis.json
│   ├── tournament_results.json
│   ├── benchmark_results.json
│   └── master_results.json
├── figures/
│   ├── sensitivity_tornado.pdf
│   ├── sensitivity_scatter.pdf
│   ├── strategy_heatmap.pdf
│   ├── performance_distributions.pdf
│   ├── convergence.pdf
│   ├── elo_evolution.pdf
│   ├── bayesian_posteriors.pdf
│   ├── effect_sizes.pdf
│   └── dashboard.html
└── paper/
    ├── paper.tex
    ├── paper.pdf (after compilation)
    └── paper.bib
```

---

## 9. Best Practices

### 9.1 Sample Size Selection

**Sobol Analysis**:
- Quick test: 64-256 samples
- Research: 1024-4096 samples
- Publication: 8192+ samples

**Morris Screening**:
- Quick test: 5-10 trajectories
- Research: 20-50 trajectories
- Publication: 50-100 trajectories

**Tournament**:
- Quick test: 50 games per matchup
- Research: 100-500 games
- Publication: 1000+ games

### 9.2 Statistical Rigor

**Always Include**:
1. Multiple comparison correction
2. Effect size measurement
3. Confidence intervals
4. Power analysis
5. Non-parametric tests (when assumptions violated)

**Report**:
- p-value AND effect size
- Confidence intervals
- Sample sizes
- Test assumptions and violations

### 9.3 Reproducibility

**Essential**:
```python
# Set random seeds
np.random.seed(42)
random.seed(42)

# Log all parameters
config = {
    'sobol_samples': 1024,
    'morris_trajectories': 20,
    'tournament_games': 100,
    'alpha': 0.05,
    'power': 0.8,
}

# Save with results
with open('config.json', 'w') as f:
    json.dump(config, f)
```

### 9.4 Visualization Guidelines

**For Papers**:
- Use vector formats (PDF, SVG)
- Minimum 300 DPI
- ColorBlind-friendly palettes
- Clear axis labels and legends
- Consistent fonts across figures

**For Presentations**:
- Larger fonts (16pt+)
- High contrast colors
- Simplified legends
- Focus on key results

---

## 📚 References

1. **Sobol, I. M. (1993)**. "Sensitivity estimates for nonlinear mathematical models." *Mathematical Modelling and Computational Experiments*.

2. **Saltelli et al. (2008)**. *Global Sensitivity Analysis: The Primer*. John Wiley & Sons.

3. **Morris, M. D. (1991)**. "Factorial sampling plans for preliminary computational experiments." *Technometrics*.

4. **Cohen, J. (1988)**. *Statistical Power Analysis for the Behavioral Sciences*. Lawrence Erlbaum Associates.

5. **Kruschke, J. K. (2013)**. "Bayesian estimation supersedes the t test." *Journal of Experimental Psychology*.

---

## 🤝 Contributing

To extend the research framework:

1. Add new sensitivity methods to `advanced_sensitivity.py`
2. Add new statistical tests to `statistical_comparison.py`
3. Add new visualizations to `visualization.py`
4. Update proofs in `MATHEMATICAL_PROOFS.md`
5. Extend paper template in `research_paper_generator.py`

---

## 📄 License

MIT License - See LICENSE file

---

**Document Version**: 2.0  
**Last Updated**: December 2025  
**Maintainers**: MCP Game League Research Team

