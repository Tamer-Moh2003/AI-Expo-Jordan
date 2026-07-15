"""Run the complete reproducible forecasting workflow in the correct order."""

from pathlib import Path
import subprocess
import sys


STEPS = (
    ("Generate synthetic data", "synthetic_generator.py"),
    ("Build approach forecasting feature table", "feature_engineering.py"),
    ("Evaluate naive baseline", "baseline_model.py"),
    ("Train and evaluate LightGBM", "train_model.py"),
    ("Generate feature-importance charts", "feature_importance.py"),
)


def main():
    root = Path(__file__).resolve().parent
    for number, (description, script) in enumerate(STEPS, start=1):
        print(f"\n{'=' * 70}\n[{number}/{len(STEPS)}] {description}\n{'=' * 70}", flush=True)
        subprocess.run([sys.executable, str(root / script)], cwd=root, check=True)

    print("\nPipeline completed successfully.")
    print("Main results: forecast_evaluation.csv and feature_importance.png/.svg")


if __name__ == "__main__":
    main()
