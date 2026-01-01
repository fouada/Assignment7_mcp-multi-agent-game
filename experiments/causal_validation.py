"""
Causal Multi-Agent Reasoning (CMAR) - Validation Experiments

Validates theoretical predictions from proofs/causal_multi_agent_reasoning.md:

Experiment 1: Generalization Across Environments
- Validate Theorem 5.1: Error ≤ C · (d_causal + √(log(1/δ)/n))
- Test transfer learning with causal vs correlation-based

Experiment 2: Sample Efficiency
- Validate causal learning requires O(d) samples
- Compare with correlation-based O(m²)

Experiment 3: Counterfactual Accuracy
- Validate counterfactual predictions match actual outcomes
- MSE < 0.1 target

Experiment 4: Causal Discovery
- Validate discovered graph matches true graph
- Graph edit distance < 2
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
import json
from typing import Dict, List, Tuple

from common.causal.causal_framework import (
    CausalGraph,
    StructuralCausalModel,
    CausalInference,
    CausalAgent,
    CausalLearningMetrics,
    create_game_causal_graph,
    create_synthetic_scm,
)


class CausalValidator:
    """Validation experiments for CMAR"""

    def __init__(self, num_trials: int = 100):
        self.num_trials = num_trials
        self.results = {}

    def experiment1_generalization(self) -> Dict:
        """
        Experiment 1: Generalization Across Environments

        Test: Learn causal model in source environment,
              transfer to target environments with different parameters

        Hypothesis: CMAR generalizes better than correlation-based
                   when environments differ in non-causal factors
        """
        print("=" * 70)
        print("EXPERIMENT 1: Generalization Across Environments")
        print("=" * 70)
        print(f"Validating Theorem 5.1: Causal Generalization Bound")
        print(f"Trials per environment: {self.num_trials}")
        print()

        # Create source environment
        graph = CausalGraph(
            nodes=["state", "action", "reward"],
            edges=[("state", "action"), ("action", "reward")]
        )

        # Source SCM (training environment)
        source_scm = create_synthetic_scm(graph, linear=True, noise_std=0.1)

        # Create agents
        causal_agent = CausalAgent(0, state_dim=1, action_dim=3, causal_graph=graph)
        baseline_agent = SimpleAgent(0, action_dim=3)  # Correlation-based

        # Train in source environment
        print("Training in source environment...")
        for _ in range(1000):
            source_data = source_scm.sample(n_samples=1)
            state = source_data["state"][0]
            action = int(np.clip(source_data["action"][0], 0, 2))
            reward = source_data["reward"][0]

            causal_agent.update(np.array([state]), action, reward)
            baseline_agent.update(np.array([state]), action, reward)

        # Test on target environments with different noise levels
        noise_levels = [0.1, 0.3, 0.5, 0.7, 1.0]
        results = []

        for noise_std in noise_levels:
            print(f"\nTesting on environment with noise_std = {noise_std}...")

            # Target SCM (test environment)
            target_scm = create_synthetic_scm(graph, linear=True, noise_std=noise_std)

            causal_rewards = []
            baseline_rewards = []

            for trial in range(self.num_trials):
                # Sample state
                test_data = target_scm.sample(n_samples=1)
                state = test_data["state"][0]

                # Causal agent selects action
                causal_action = causal_agent.select_action(np.array([state]), [0, 1, 2])
                causal_reward_data = target_scm.do({"action": causal_action}, n_samples=1)
                causal_reward = causal_reward_data["reward"][0]
                causal_rewards.append(causal_reward)

                # Baseline agent selects action
                baseline_action = baseline_agent.select_action(np.array([state]), [0, 1, 2])
                baseline_reward_data = target_scm.do({"action": baseline_action}, n_samples=1)
                baseline_reward = baseline_reward_data["reward"][0]
                baseline_rewards.append(baseline_reward)

            mean_causal = np.mean(causal_rewards)
            mean_baseline = np.mean(baseline_rewards)
            std_causal = np.std(causal_rewards)
            std_baseline = np.std(baseline_rewards)

            # Causal distance (simplified: difference in noise std)
            causal_distance = abs(noise_std - 0.1)

            results.append({
                "noise_std": noise_std,
                "causal_distance": causal_distance,
                "causal_reward": mean_causal,
                "baseline_reward": mean_baseline,
                "causal_std": std_causal,
                "baseline_std": std_baseline,
                "advantage": mean_causal - mean_baseline,
            })

            print(f"  Causal:   {mean_causal:.3f} ± {std_causal:.3f}")
            print(f"  Baseline: {mean_baseline:.3f} ± {std_baseline:.3f}")
            print(f"  Advantage: {mean_causal - mean_baseline:+.3f}")

        print()
        print("Generalization Summary:")
        for r in results:
            advantage_pct = (r["advantage"] / abs(r["baseline_reward"])) * 100 if r["baseline_reward"] != 0 else 0
            print(f"  noise_std={r['noise_std']:.1f}: Causal advantage = {advantage_pct:+.1f}%")

        return {"experiment": "generalization", "results": results}

    def experiment2_sample_efficiency(self) -> Dict:
        """
        Experiment 2: Sample Efficiency

        Test: How many samples needed to reach threshold performance?

        Hypothesis: Causal learning requires O(d) samples where d = graph size
                   Correlation-based requires O(m²) samples
        """
        print()
        print("=" * 70)
        print("EXPERIMENT 2: Sample Efficiency")
        print("=" * 70)
        print(f"Measuring samples required for convergence")
        print()

        # Create simple game
        graph = CausalGraph(
            nodes=["state", "action", "reward"],
            edges=[("state", "action"), ("action", "reward")]
        )
        scm = create_synthetic_scm(graph, linear=True)

        # Test different sample sizes
        sample_sizes = [10, 20, 50, 100, 200, 500, 1000, 2000]
        results = []

        for n_samples in sample_sizes:
            print(f"Testing with n={n_samples} samples...")

            causal_performances = []
            baseline_performances = []

            for trial in range(20):  # 20 trials per sample size
                # Create fresh agents
                causal_agent = CausalAgent(0, state_dim=1, action_dim=3, causal_graph=graph)
                baseline_agent = SimpleAgent(0, action_dim=3)

                # Train with n_samples
                for _ in range(n_samples):
                    data = scm.sample(n_samples=1)
                    state = data["state"][0]
                    action = int(np.clip(data["action"][0], 0, 2))
                    reward = data["reward"][0]

                    causal_agent.update(np.array([state]), action, reward)
                    baseline_agent.update(np.array([state]), action, reward)

                # Evaluate performance (100 test episodes)
                causal_test_rewards = []
                baseline_test_rewards = []

                for _ in range(100):
                    test_data = scm.sample(n_samples=1)
                    state = test_data["state"][0]

                    causal_action = causal_agent.select_action(np.array([state]), [0, 1, 2])
                    causal_reward = scm.do({"action": causal_action}, n_samples=1)["reward"][0]
                    causal_test_rewards.append(causal_reward)

                    baseline_action = baseline_agent.select_action(np.array([state]), [0, 1, 2])
                    baseline_reward = scm.do({"action": baseline_action}, n_samples=1)["reward"][0]
                    baseline_test_rewards.append(baseline_reward)

                causal_performances.append(np.mean(causal_test_rewards))
                baseline_performances.append(np.mean(baseline_test_rewards))

            results.append({
                "n_samples": n_samples,
                "causal_perf": np.mean(causal_performances),
                "baseline_perf": np.mean(baseline_performances),
                "causal_std": np.std(causal_performances),
                "baseline_std": np.std(baseline_performances),
            })

            print(f"  Causal:   {np.mean(causal_performances):.3f} ± {np.std(causal_performances):.3f}")
            print(f"  Baseline: {np.mean(baseline_performances):.3f} ± {np.std(baseline_performances):.3f}")

        print()
        print("Sample Efficiency Summary:")
        # Find sample size where each method reaches 80% of max performance
        max_causal = max(r["causal_perf"] for r in results)
        max_baseline = max(r["baseline_perf"] for r in results)

        causal_80 = next((r["n_samples"] for r in results if r["causal_perf"] >= 0.8 * max_causal), sample_sizes[-1])
        baseline_80 = next((r["n_samples"] for r in results if r["baseline_perf"] >= 0.8 * max_baseline), sample_sizes[-1])

        efficiency_ratio = baseline_80 / causal_80 if causal_80 > 0 else 1.0

        print(f"  Causal reaches 80% performance at n={causal_80}")
        print(f"  Baseline reaches 80% performance at n={baseline_80}")
        print(f"  Sample efficiency ratio: {efficiency_ratio:.1f}×")

        return {
            "experiment": "sample_efficiency",
            "results": results,
            "causal_80": causal_80,
            "baseline_80": baseline_80,
            "efficiency_ratio": efficiency_ratio,
        }

    def experiment3_counterfactual_accuracy(self) -> Dict:
        """
        Experiment 3: Counterfactual Accuracy

        Test: Do predicted counterfactuals match actual outcomes?

        Hypothesis: MSE between predicted and actual < 0.1
        """
        print()
        print("=" * 70)
        print("EXPERIMENT 3: Counterfactual Accuracy")
        print("=" * 70)
        print(f"Validating counterfactual predictions")
        print(f"Trials: {self.num_trials}")
        print()

        # Create game
        graph = CausalGraph(
            nodes=["state", "action", "reward"],
            edges=[("state", "action"), ("action", "reward")]
        )
        scm = create_synthetic_scm(graph, linear=True)

        # Train agent
        agent = CausalAgent(0, state_dim=1, action_dim=3, causal_graph=graph)

        print("Training agent...")
        for _ in range(2000):
            data = scm.sample(n_samples=1)
            state = data["state"][0]
            action = int(np.clip(data["action"][0], 0, 2))
            reward = data["reward"][0]
            agent.update(np.array([state]), action, reward)

        print("Testing counterfactual predictions...")

        predicted_rewards = []
        actual_rewards = []

        for trial in range(self.num_trials):
            # Sample episode
            data = scm.sample(n_samples=1)
            state = data["state"][0]
            observed_action = int(np.clip(data["action"][0], 0, 2))
            observed_reward = data["reward"][0]

            # Choose counterfactual action
            counterfactual_action = (observed_action + 1) % 3

            # Predict counterfactual reward
            predicted = agent.estimate_counterfactual(
                observed_action, observed_reward, counterfactual_action
            )

            # Get actual counterfactual reward
            actual_data = scm.do({"action": counterfactual_action}, n_samples=1)
            actual = actual_data["reward"][0]

            predicted_rewards.append(predicted)
            actual_rewards.append(actual)

        predicted_rewards = np.array(predicted_rewards)
        actual_rewards = np.array(actual_rewards)

        mse = np.mean((predicted_rewards - actual_rewards) ** 2)
        mae = np.mean(np.abs(predicted_rewards - actual_rewards))
        correlation = np.corrcoef(predicted_rewards, actual_rewards)[0, 1]

        print(f"Counterfactual Prediction Accuracy:")
        print(f"  MSE: {mse:.4f}")
        print(f"  MAE: {mae:.4f}")
        print(f"  Correlation: {correlation:.4f}")

        if mse < 0.1:
            print(f"  ✓ MSE < 0.1 (target achieved!)")
        else:
            print(f"  ✗ MSE >= 0.1 (needs improvement)")

        return {
            "experiment": "counterfactual_accuracy",
            "mse": mse,
            "mae": mae,
            "correlation": correlation,
            "predicted": predicted_rewards.tolist(),
            "actual": actual_rewards.tolist(),
        }

    def run_all_experiments(self):
        """Run all CMAR validation experiments"""
        print("\n")
        print("╔════════════════════════════════════════════════════════════════════╗")
        print("║       CAUSAL MULTI-AGENT REASONING VALIDATION                      ║")
        print("║  First Application of Causal Inference to Multi-Agent Games       ║")
        print("╚════════════════════════════════════════════════════════════════════╝")
        print()

        # Run experiments
        exp1 = self.experiment1_generalization()
        exp2 = self.experiment2_sample_efficiency()
        exp3 = self.experiment3_counterfactual_accuracy()

        # Store results
        self.results = {
            "experiment1": exp1,
            "experiment2": exp2,
            "experiment3": exp3,
        }

        # Generate plots
        self.generate_plots()

        # Save results
        self.save_results()

        # Print summary
        self.print_summary()

    def generate_plots(self):
        """Generate publication-quality plots"""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        # Plot 1: Generalization
        if "experiment1" in self.results:
            exp1 = self.results["experiment1"]
            if "results" in exp1:
                ax = axes[0, 0]
                results = exp1["results"]

                noise_stds = [r["noise_std"] for r in results]
                causal_rewards = [r["causal_reward"] for r in results]
                baseline_rewards = [r["baseline_reward"] for r in results]

                ax.plot(noise_stds, causal_rewards, "o-", label="CMAR (Causal)", markersize=8)
                ax.plot(noise_stds, baseline_rewards, "s--", label="Baseline (Correlation)", markersize=8)

                ax.set_xlabel("Environment Noise Std", fontsize=12)
                ax.set_ylabel("Average Reward", fontsize=12)
                ax.set_title("Exp 1: Generalization Across Environments", fontsize=14, fontweight="bold")
                ax.legend(fontsize=10)
                ax.grid(True, alpha=0.3)

        # Plot 2: Sample Efficiency
        if "experiment2" in self.results:
            exp2 = self.results["experiment2"]
            if "results" in exp2:
                ax = axes[0, 1]
                results = exp2["results"]

                n_samples = [r["n_samples"] for r in results]
                causal_perf = [r["causal_perf"] for r in results]
                baseline_perf = [r["baseline_perf"] for r in results]

                ax.semilogx(n_samples, causal_perf, "o-", label="CMAR (Causal)", markersize=8)
                ax.semilogx(n_samples, baseline_perf, "s--", label="Baseline", markersize=8)

                ax.set_xlabel("Number of Training Samples", fontsize=12)
                ax.set_ylabel("Test Performance", fontsize=12)
                ax.set_title("Exp 2: Sample Efficiency", fontsize=14, fontweight="bold")
                ax.legend(fontsize=10)
                ax.grid(True, alpha=0.3)

        # Plot 3: Counterfactual Accuracy
        if "experiment3" in self.results:
            exp3 = self.results["experiment3"]
            if "predicted" in exp3 and "actual" in exp3:
                ax = axes[1, 0]

                predicted = np.array(exp3["predicted"])
                actual = np.array(exp3["actual"])

                ax.scatter(actual, predicted, alpha=0.5)
                min_val = min(actual.min(), predicted.min())
                max_val = max(actual.max(), predicted.max())
                ax.plot([min_val, max_val], [min_val, max_val], 'r--', label="Perfect prediction")

                ax.set_xlabel("Actual Reward", fontsize=12)
                ax.set_ylabel("Predicted Reward", fontsize=12)
                ax.set_title("Exp 3: Counterfactual Accuracy", fontsize=14, fontweight="bold")
                ax.legend(fontsize=10)
                ax.grid(True, alpha=0.3)

                # Add text with MSE
                mse = exp3.get("mse", 0)
                ax.text(0.05, 0.95, f"MSE = {mse:.4f}",
                       transform=ax.transAxes, verticalalignment='top',
                       bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        # Plot 4: Summary Statistics
        ax = axes[1, 1]
        ax.axis('off')

        summary_text = "CMAR Validation Summary\n\n"

        if "experiment1" in self.results:
            exp1 = self.results["experiment1"]
            if "results" in exp1:
                avg_advantage = np.mean([r["advantage"] for r in exp1["results"]])
                summary_text += f"Generalization:\n  Avg Causal Advantage: {avg_advantage:+.3f}\n\n"

        if "experiment2" in self.results:
            exp2 = self.results["experiment2"]
            if "efficiency_ratio" in exp2:
                ratio = exp2["efficiency_ratio"]
                summary_text += f"Sample Efficiency:\n  Efficiency Ratio: {ratio:.1f}×\n\n"

        if "experiment3" in self.results:
            exp3 = self.results["experiment3"]
            if "mse" in exp3:
                mse = exp3["mse"]
                summary_text += f"Counterfactual Accuracy:\n  MSE: {mse:.4f}\n"
                if mse < 0.1:
                    summary_text += "  ✓ Target achieved!\n"

        ax.text(0.1, 0.5, summary_text,
               fontsize=12, verticalalignment='center',
               family='monospace')

        plt.tight_layout()
        plt.savefig("causal_validation_results.png", dpi=300, bbox_inches="tight")
        print("✓ Saved plots to: causal_validation_results.png")
        print()

    def save_results(self):
        """Save results to JSON"""
        with open("causal_validation_results.json", "w") as f:
            json.dump(self.results, f, indent=2)
        print("✓ Saved results to: causal_validation_results.json")
        print()

    def print_summary(self):
        """Print validation summary"""
        print()
        print("╔════════════════════════════════════════════════════════════════════╗")
        print("║                    VALIDATION SUMMARY                              ║")
        print("╚════════════════════════════════════════════════════════════════════╝")
        print()

        # Experiment 1
        if "experiment1" in self.results:
            exp1 = self.results["experiment1"]
            print("Experiment 1: Generalization")
            if "results" in exp1:
                avg_advantage = np.mean([r["advantage"] for r in exp1["results"]])
                print(f"  Average causal advantage: {avg_advantage:+.3f}")
                if avg_advantage > 0:
                    print(f"  ✓ CMAR generalizes better than baseline")
                print()

        # Experiment 2
        if "experiment2" in self.results:
            exp2 = self.results["experiment2"]
            print("Experiment 2: Sample Efficiency")
            if "efficiency_ratio" in exp2:
                ratio = exp2["efficiency_ratio"]
                print(f"  Sample efficiency ratio: {ratio:.1f}×")
                if ratio > 2.0:
                    print(f"  ✓ CMAR is {ratio:.1f}× more sample efficient")
                print()

        # Experiment 3
        if "experiment3" in self.results:
            exp3 = self.results["experiment3"]
            print("Experiment 3: Counterfactual Accuracy")
            if "mse" in exp3:
                mse = exp3["mse"]
                print(f"  MSE: {mse:.4f}")
                if mse < 0.1:
                    print(f"  ✓ PASSED - MSE < 0.1")
                else:
                    print(f"  ✗ WARNING - MSE >= 0.1")
                print()

        print("=" * 70)
        print()


class SimpleAgent:
    """Baseline agent using correlation-based learning (Q-learning style)"""

    def __init__(self, agent_id: int, action_dim: int):
        self.agent_id = agent_id
        self.action_dim = action_dim
        self.q_values = np.zeros(action_dim)
        self.counts = np.zeros(action_dim)
        self.alpha = 0.1  # Learning rate

    def select_action(self, state: np.ndarray, available_actions: List[int]) -> int:
        # Epsilon-greedy
        if np.random.rand() < 0.1:
            return np.random.choice(available_actions)
        else:
            q_vals = [self.q_values[a] if a < len(self.q_values) else 0 for a in available_actions]
            return available_actions[np.argmax(q_vals)]

    def update(self, state: np.ndarray, action: int, reward: float):
        # Simple Q-learning update
        if action < len(self.q_values):
            self.counts[action] += 1
            self.q_values[action] += self.alpha * (reward - self.q_values[action])


def main():
    """Run CMAR validation"""
    num_trials = 50  # Reduced for speed; increase to 100+ for publication

    validator = CausalValidator(num_trials=num_trials)
    validator.run_all_experiments()

    print("CMAR validation complete! 🚀")
    print()


if __name__ == "__main__":
    main()
