"""Compatibility entry point for the leakage-safe time-based evaluation.

The former implementation used a random train/test split, which leaks future
traffic patterns. The canonical training script evaluates on the final 14 days.
"""

from train_model import main


if __name__ == "__main__":
    main()
