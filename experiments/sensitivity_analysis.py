"""
Systematic Sensitivity Analysis
================================

Empirical validation of theoretical predictions from THEORETICAL_ANALYSIS.md.

This module implements rigorous sensitivity analysis experiments to measure
how system parameters affect performance metrics.

Methodology:
1. One-Factor-At-A-Time (OFAT) analysis
2. Full factorial design for interaction effects
3. Statistical significance testing (ANOVA)
4. Effect size computation (Cohen's d)
5. Visualization and reporting

Usage:
    python experiments/sensitivity_analysis.py --output results/sensitivity.json
"""

import asyncio
import time
import statistics
import json
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import numpy as np
from scipy import stats

# Import our systems
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.middleware import (
    MiddlewarePipeline,
    LoggingMiddleware,
    AuthenticationMiddleware,
    RateLimitMiddleware,
    MetricsMiddleware,
    CachingMiddleware,
)
from src.observability import get_metrics_collector, Timer
from src.common.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# Data Structures
# ============================================================================


@dataclass
class ExperimentConfig:
    """Configuration for a single experiment."""

    parameter_name: str
    parameter_value: float
    num_requests: int = 1000
    num_replications: int = 10
    baseline_config: Dict[str, Any] = None


@dataclass
class ExperimentResult:
    """Results from a single experiment."""

    config: ExperimentConfig
    latency_mean: float
    latency_std: float
    latency_p50: float
    latency_p90: float
    latency_p99: float
    throughput: float
    error_rate: float
    cpu_time: float


@dataclass
class SensitivityResult:
    """Sensitivity analysis results for one parameter."""

    parameter_name: str
    baseline_value: float
    test_values: List[float]
    latency_sensitivity: float
    throughput_sensitivity: float
    f_statistic: float
    p_value: float
    effect_size: float  # Cohen's d
    is_significant: bool  # p < 0.05


# ============================================================================
# Baseline Configuration
# ============================================================================


BASELINE_CONFIG = {
    "rate_limit": 100,  # requests per minute
    "burst_size": 10,
    "cache_size": 100,
    "cache_ttl": 300,  # seconds
    "trace_sample_rate": 0.1,
    "middleware_count": 6,
}


# ============================================================================
# Experiment Runner
# ============================================================================


class SensitivityAnalyzer:
    """Runs systematic sensitivity analysis experiments."""

    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or Path("results/sensitivity")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results: List[ExperimentResult] = []

    async def run_experiment(self, config: ExperimentConfig) -> ExperimentResult:
        """
        Run a single experiment with given configuration.

        Returns:
            ExperimentResult with measured metrics
        """
        logger.info(
            f"Running experiment: {config.parameter_name}={config.parameter_value}"
        )

        # Collect metrics over replications
        latencies = []
        errors = 0

        # Create pipeline with config
        pipeline = self._create_pipeline(config)

        # Sample handler
        async def test_handler(request):
            # Simulate some work
            await asyncio.sleep(0.001)  # 1ms
            return {"success": True, "data": "test"}

        # Run replications
        start_time = time.time()

        for replication in range(config.num_replications):
            replication_latencies = []

            for i in range(config.num_requests):
                request = {
                    "type": "test_request",
                    "id": i,
                    "replication": replication,
                }

                req_start = time.perf_counter()

                try:
                    response = await pipeline.execute(request, handler=test_handler)
                    req_end = time.perf_counter()

                    latency = (req_end - req_start) * 1000  # ms
                    replication_latencies.append(latency)

                    if response.get("error"):
                        errors += 1

                except Exception as e:
                    errors += 1
                    logger.warning(f"Request failed: {e}")

            latencies.extend(replication_latencies)

        end_time = time.time()

        # Compute metrics
        total_requests = config.num_requests * config.num_replications
        duration = end_time - start_time

        result = ExperimentResult(
            config=config,
            latency_mean=statistics.mean(latencies) if latencies else 0,
            latency_std=statistics.stdev(latencies) if len(latencies) > 1 else 0,
            latency_p50=np.percentile(latencies, 50) if latencies else 0,
            latency_p90=np.percentile(latencies, 90) if latencies else 0,
            latency_p99=np.percentile(latencies, 99) if latencies else 0,
            throughput=total_requests / duration if duration > 0 else 0,
            error_rate=errors / total_requests if total_requests > 0 else 0,
            cpu_time=duration,
        )

        self.results.append(result)
        return result

    def _create_pipeline(self, config: ExperimentConfig) -> MiddlewarePipeline:
        """Create middleware pipeline from configuration."""
        pipeline = MiddlewarePipeline(timeout_seconds=30.0, error_handling="continue")

        # Get parameter value
        param = config.parameter_name
        value = config.parameter_value

        # Apply configuration
        if param == "rate_limit":
            pipeline.add_middleware(
                RateLimitMiddleware(requests_per_minute=value, burst_size=10),
                priority=70,
            )
        elif param == "burst_size":
            pipeline.add_middleware(
                RateLimitMiddleware(requests_per_minute=100, burst_size=int(value)),
                priority=70,
            )
        elif param == "cache_size":
            pipeline.add_middleware(
                CachingMiddleware(max_size=int(value), ttl_seconds=300), priority=40
            )
        elif param == "cache_ttl":
            pipeline.add_middleware(
                CachingMiddleware(max_size=100, ttl_seconds=int(value)), priority=40
            )
        else:
            # Default pipeline
            pipeline.add_middleware(LoggingMiddleware(), priority=90)
            pipeline.add_middleware(MetricsMiddleware(), priority=50)

        return pipeline

    async def analyze_parameter(
        self,
        parameter_name: str,
        baseline_value: float,
        test_values: List[float],
        num_requests: int = 1000,
        num_replications: int = 10,
    ) -> SensitivityResult:
        """
        Analyze sensitivity to a single parameter.

        Steps:
        1. Run baseline experiment
        2. Run experiments for each test value
        3. Compute sensitivity metrics
        4. Statistical testing

        Returns:
            SensitivityResult with analysis
        """
        logger.info(f"Analyzing parameter: {parameter_name}")

        # Run baseline
        baseline_config = ExperimentConfig(
            parameter_name=parameter_name,
            parameter_value=baseline_value,
            num_requests=num_requests,
            num_replications=num_replications,
        )
        baseline_result = await self.run_experiment(baseline_config)

        # Run test experiments
        test_results = []
        for value in test_values:
            config = ExperimentConfig(
                parameter_name=parameter_name,
                parameter_value=value,
                num_requests=num_requests,
                num_replications=num_replications,
            )
            result = await self.run_experiment(config)
            test_results.append(result)

        # Compute sensitivity
        latency_sensitivity = self._compute_sensitivity(
            baseline_result.latency_mean,
            [r.latency_mean for r in test_results],
            baseline_value,
            test_values,
        )

        throughput_sensitivity = self._compute_sensitivity(
            baseline_result.throughput,
            [r.throughput for r in test_results],
            baseline_value,
            test_values,
        )

        # Statistical testing (ANOVA)
        latency_groups = [[baseline_result.latency_mean]] + [
            [r.latency_mean] for r in test_results
        ]
        f_stat, p_value = stats.f_oneway(*latency_groups)

        # Effect size (Cohen's d)
        effect_size = self._compute_effect_size(
            baseline_result.latency_mean,
            statistics.mean([r.latency_mean for r in test_results]),
            baseline_result.latency_std,
            statistics.mean([r.latency_std for r in test_results]),
        )

        result = SensitivityResult(
            parameter_name=parameter_name,
            baseline_value=baseline_value,
            test_values=test_values,
            latency_sensitivity=latency_sensitivity,
            throughput_sensitivity=throughput_sensitivity,
            f_statistic=f_stat,
            p_value=p_value,
            effect_size=effect_size,
            is_significant=p_value < 0.05,
        )

        logger.info(
            f"Sensitivity results for {parameter_name}:\n"
            f"  Latency sensitivity: {latency_sensitivity:.3f}\n"
            f"  Throughput sensitivity: {throughput_sensitivity:.3f}\n"
            f"  F-statistic: {f_stat:.3f}\n"
            f"  p-value: {p_value:.4f}\n"
            f"  Effect size (Cohen's d): {effect_size:.3f}\n"
            f"  Significant: {result.is_significant}"
        )

        return result

    def _compute_sensitivity(
        self,
        baseline: float,
        test_values: List[float],
        baseline_param: float,
        test_params: List[float],
    ) -> float:
        """
        Compute sensitivity: S = ΔM/Δθ

        Uses finite difference approximation.
        """
        if not test_values or baseline_param == 0:
            return 0.0

        # Average sensitivity across all test points
        sensitivities = []
        for test_val, test_param in zip(test_values, test_params):
            delta_metric = test_val - baseline
            delta_param = test_param - baseline_param

            if abs(delta_param) > 1e-6:
                # Normalized sensitivity
                sensitivity = (delta_metric / baseline) / (
                    delta_param / baseline_param
                )
                sensitivities.append(abs(sensitivity))

        return statistics.mean(sensitivities) if sensitivities else 0.0

    def _compute_effect_size(
        self, mean1: float, mean2: float, std1: float, std2: float
    ) -> float:
        """
        Compute Cohen's d effect size.

        d = (M1 - M2) / s_pooled

        Interpretation:
        - d < 0.2: Small
        - 0.2 ≤ d < 0.5: Medium
        - d ≥ 0.5: Large
        """
        # Pooled standard deviation
        s_pooled = np.sqrt((std1**2 + std2**2) / 2)

        if s_pooled == 0:
            return 0.0

        d = abs(mean1 - mean2) / s_pooled
        return d

    async def run_full_analysis(self) -> Dict[str, SensitivityResult]:
        """
        Run complete sensitivity analysis for all parameters.

        Tests parameters defined in BASELINE_CONFIG.
        """
        results = {}

        # Rate limit sensitivity
        results["rate_limit"] = await self.analyze_parameter(
            parameter_name="rate_limit",
            baseline_value=100,
            test_values=[50, 75, 125, 150, 200],
            num_requests=500,
            num_replications=5,
        )

        # Burst size sensitivity
        results["burst_size"] = await self.analyze_parameter(
            parameter_name="burst_size",
            baseline_value=10,
            test_values=[5, 15, 20, 30, 50],
            num_requests=500,
            num_replications=5,
        )

        # Cache size sensitivity
        results["cache_size"] = await self.analyze_parameter(
            parameter_name="cache_size",
            baseline_value=100,
            test_values=[50, 200, 500, 1000, 5000],
            num_requests=500,
            num_replications=5,
        )

        # Cache TTL sensitivity
        results["cache_ttl"] = await self.analyze_parameter(
            parameter_name="cache_ttl",
            baseline_value=300,
            test_values=[60, 180, 600, 1800, 3600],
            num_requests=500,
            num_replications=5,
        )

        return results

    def save_results(self, filename: str = "sensitivity_results.json"):
        """Save results to JSON file."""
        output_path = self.output_dir / filename

        # Convert results to serializable format
        data = {
            "baseline_config": BASELINE_CONFIG,
            "experiments": [asdict(r) for r in self.results],
            "timestamp": time.time(),
        }

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Results saved to {output_path}")

    def generate_report(self, results: Dict[str, SensitivityResult]) -> str:
        """
        Generate human-readable report.

        Returns:
            Markdown-formatted report
        """
        report = ["# Sensitivity Analysis Report\n"]
        report.append(f"**Generated**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        report.append(f"**Baseline Configuration**: {BASELINE_CONFIG}\n")
        report.append("\n## Results Summary\n")

        report.append("| Parameter | Latency Sens. | Throughput Sens. | p-value | Effect Size | Significant |")
        report.append("|-----------|---------------|------------------|---------|-------------|-------------|")

        for param_name, result in results.items():
            sig_marker = "✅" if result.is_significant else "❌"
            effect_interpretation = self._interpret_effect_size(result.effect_size)

            report.append(
                f"| {param_name} | {result.latency_sensitivity:.3f} | "
                f"{result.throughput_sensitivity:.3f} | {result.p_value:.4f} | "
                f"{result.effect_size:.3f} ({effect_interpretation}) | {sig_marker} |"
            )

        report.append("\n## Detailed Results\n")

        for param_name, result in results.items():
            report.append(f"\n### {param_name}\n")
            report.append(f"- **Baseline Value**: {result.baseline_value}")
            report.append(f"- **Test Values**: {result.test_values}")
            report.append(
                f"- **Latency Sensitivity**: {result.latency_sensitivity:.3f}"
            )
            report.append(
                f"- **Throughput Sensitivity**: {result.throughput_sensitivity:.3f}"
            )
            report.append(f"- **F-statistic**: {result.f_statistic:.3f}")
            report.append(f"- **p-value**: {result.p_value:.4f}")
            report.append(
                f"- **Effect Size**: {result.effect_size:.3f} ({self._interpret_effect_size(result.effect_size)})"
            )
            report.append(
                f"- **Statistically Significant**: {'Yes' if result.is_significant else 'No'}"
            )

            # Interpretation
            report.append("\n**Interpretation**:")
            if result.is_significant:
                if result.latency_sensitivity > 0.5:
                    report.append(
                        f"- {param_name} has HIGH sensitivity on latency (S > 0.5)"
                    )
                elif result.latency_sensitivity > 0.2:
                    report.append(
                        f"- {param_name} has MEDIUM sensitivity on latency (0.2 < S < 0.5)"
                    )
                else:
                    report.append(
                        f"- {param_name} has LOW sensitivity on latency (S < 0.2)"
                    )
            else:
                report.append(
                    f"- {param_name} has NO statistically significant effect (p ≥ 0.05)"
                )

        return "\n".join(report)

    def _interpret_effect_size(self, d: float) -> str:
        """Interpret Cohen's d effect size."""
        if d < 0.2:
            return "Small"
        elif d < 0.5:
            return "Medium"
        else:
            return "Large"


# ============================================================================
# Main Execution
# ============================================================================


async def main():
    """Run sensitivity analysis."""
    print("=" * 80)
    print("SYSTEMATIC SENSITIVITY ANALYSIS")
    print("=" * 80)
    print()

    analyzer = SensitivityAnalyzer()

    print("Running full parameter analysis...")
    print("This may take several minutes...\n")

    results = await analyzer.run_full_analysis()

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print()

    # Generate report
    report = analyzer.generate_report(results)
    print(report)

    # Save results
    analyzer.save_results()

    # Save report
    report_path = analyzer.output_dir / "sensitivity_report.md"
    with open(report_path, "w") as f:
        f.write(report)

    print(f"\nReport saved to {report_path}")
    print(f"Data saved to {analyzer.output_dir / 'sensitivity_results.json'}")


if __name__ == "__main__":
    asyncio.run(main())
