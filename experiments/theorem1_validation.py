#!/usr/bin/env python3
"""
Theorem 1 Validation Experiments

Run this script to validate Theorem 1.1 (Quantum Convergence) empirically.

Usage:
    python experiments/theorem1_validation.py

Expected runtime: 10-15 minutes
Expected outcome: Validates O(√n) convergence and √n speedup
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from common.theory.quantum_convergence import (
    ConvergenceExperiment,
    QuantumConvergenceAnalyzer,
)


def main():
    """Run complete validation suite for Theorem 1."""

    print("=" * 70)
    print("THEOREM 1 EXPERIMENTAL VALIDATION")
    print("=" * 70)
    print("\nThis will validate:")
    print("  1. O(√n) convergence scaling")
    print("  2. √n speedup over classical methods")
    print("  3. 1-δ success probability guarantee")
    print("\nEstimated runtime: 10-15 minutes\n")

    # Initialize experiment
    experiment = ConvergenceExperiment(epsilon=0.1, delta=0.05)

    # ========================================
    # Experiment 1: Convergence Scaling
    # ========================================
    print("\n" + "=" * 70)
    print("EXPERIMENT 1: Convergence Scaling")
    print("=" * 70)
    print("\nVariation: n ∈ {2, 5, 10, 20, 50}")
    print("Hypothesis: T(n) = O(√n)")
    print("Validation: Log-log plot slope ≈ 0.5")

    n_values = [2, 5, 10, 20, 50]
    num_trials = 100

    results = experiment.run_experiment_varying_n(n_values, num_trials)

    # Generate plot
    print("\n📊 Generating convergence scaling plot...")
    experiment.plot_convergence_scaling("theorem1_convergence_scaling.png")

    # ========================================
    # Experiment 2: Speedup Validation
    # ========================================
    print("\n" + "=" * 70)
    print("EXPERIMENT 2: Speedup Validation")
    print("=" * 70)

    print("\n| n  | Quantum T | Classical T | Speedup | Theory (√n) | Normalized |")
    print("|" + "-" * 68 + "|")

    for n in n_values:
        r = results[n]
        print(
            f"| {n:2d} | {r['quantum']['mean']:7.1f}   | "
            f"{r['classical']['mean']:9.1f}   | "
            f"{r['speedup']['empirical']:5.2f}× | "
            f"{r['speedup']['theoretical']:7.2f}    | "
            f"{r['speedup']['normalized']:8.3f}   |"
        )

    print("\nInterpretation:")
    print("  - Normalized speedup ≈ 1.0 means empirical matches theory")
    print("  - Values 0.8-1.2 are excellent (within 20% of theory)")

    # ========================================
    # Experiment 3: Probability Guarantee
    # ========================================
    print("\n" + "=" * 70)
    print("EXPERIMENT 3: Probability Guarantee")
    print("=" * 70)
    print("\nHypothesis: Failure rate ≤ δ = 0.05")
    print("Method: Run 1000 trials, count failures\n")

    prob_results = experiment.verify_probability_guarantee(num_trials=1000)

    # ========================================
    # Final Summary
    # ========================================
    print("\n" + "=" * 70)
    print("SUMMARY: Theorem 1 Validation")
    print("=" * 70)

    # Check Experiment 1
    # Get slope from last experiment
    import numpy as np

    log_n = np.log(n_values)
    quantum_means = [results[n]["quantum"]["mean"] for n in n_values]
    log_q = np.log(quantum_means)
    slope, _ = np.polyfit(log_n, log_q, 1)

    exp1_pass = 0.4 <= slope <= 0.6  # Within 20% of 0.5

    print(f"\n✅ Experiment 1: Convergence Scaling")
    print(f"   Measured slope: {slope:.3f}")
    print(f"   Expected slope: 0.500")
    print(f"   Status: {'PASSED ✓' if exp1_pass else 'FAILED ✗'}")

    # Check Experiment 2
    avg_normalized = np.mean([results[n]["speedup"]["normalized"] for n in n_values])
    exp2_pass = 0.8 <= avg_normalized <= 1.2

    print(f"\n✅ Experiment 2: Speedup Validation")
    print(f"   Avg normalized speedup: {avg_normalized:.3f}")
    print(f"   Expected: 1.000")
    print(f"   Status: {'PASSED ✓' if exp2_pass else 'FAILED ✗'}")

    # Check Experiment 3
    exp3_pass = prob_results["passed"]

    print(f"\n✅ Experiment 3: Probability Guarantee")
    print(f"   Failure rate: {prob_results['failure_rate']:.3f}")
    print(f"   Threshold (δ): {prob_results['delta_threshold']:.3f}")
    print(f"   Status: {'PASSED ✓' if exp3_pass else 'FAILED ✗'}")

    # Overall result
    all_passed = exp1_pass and exp2_pass and exp3_pass

    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 ALL EXPERIMENTS PASSED!")
        print("\nTheorem 1.1 is VALIDATED:")
        print("  ✅ O(√n) convergence confirmed")
        print("  ✅ √n speedup confirmed")
        print("  ✅ 1-δ probability guarantee confirmed")
        print("\n👉 Ready to include in paper!")
    else:
        print("⚠️  SOME EXPERIMENTS FAILED")
        print("\nAction items:")
        if not exp1_pass:
            print(f"  - Review convergence scaling (slope={slope:.3f}, expected=0.5)")
        if not exp2_pass:
            print(f"  - Review speedup calculation (normalized={avg_normalized:.3f})")
        if not exp3_pass:
            print("  - Review probability guarantees implementation")

    print("=" * 70)

    # Save results to JSON
    import json

    output_data = {
        "experiment_1": {
            "n_values": n_values,
            "results": {
                str(n): {
                    "quantum_mean": float(results[n]["quantum"]["mean"]),
                    "classical_mean": float(results[n]["classical"]["mean"]),
                    "speedup": float(results[n]["speedup"]["empirical"]),
                }
                for n in n_values
            },
            "slope": float(slope),
            "passed": exp1_pass,
        },
        "experiment_2": {
            "avg_normalized_speedup": float(avg_normalized),
            "passed": exp2_pass,
        },
        "experiment_3": prob_results,
        "overall": {"all_passed": all_passed},
    }

    with open("theorem1_validation_results.json", "w") as f:
        json.dump(output_data, f, indent=2)

    print("\n📁 Results saved to: theorem1_validation_results.json")
    print("📊 Plot saved to: theorem1_convergence_scaling.png")


if __name__ == "__main__":
    main()
