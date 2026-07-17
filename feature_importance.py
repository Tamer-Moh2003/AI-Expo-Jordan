"""Create per-horizon and combined feature-importance charts for Task 31."""

from pathlib import Path
import json
from html import escape

import lightgbm as lgb
import numpy as np
import pandas as pd

try:
    import matplotlib.pyplot as plt
except ModuleNotFoundError:
    plt = None


HORIZONS = ("15m", "30m", "60m")
TOP_FEATURES = 12


def load_importance(horizon):
    model_path = Path(f"model_{horizon}.txt")
    metadata_path = Path(f"model_{horizon}_metadata.json")
    if not model_path.exists() or not metadata_path.exists():
        raise FileNotFoundError(
            f"Missing {model_path} or {metadata_path}. Run train_model.py first."
        )

    model = lgb.Booster(model_file=str(model_path))
    with metadata_path.open(encoding="utf-8") as file:
        metadata = json.load(file)

    features = metadata["features"]
    gains = model.feature_importance(importance_type="gain")
    if len(features) != len(gains):
        raise ValueError(
            f"Feature mismatch for {horizon}: metadata has {len(features)}, "
            f"model has {len(gains)}. Retrain the models."
        )

    frame = pd.DataFrame({"feature": features, "gain": gains})
    total_gain = frame["gain"].sum()
    frame["importance_pct"] = (
        100 * frame["gain"] / total_gain if total_gain else np.zeros(len(frame))
    )
    return frame.sort_values("importance_pct", ascending=False)


def save_chart(frame, title, output_path, color):
    plot_data = frame.head(TOP_FEATURES).sort_values("importance_pct")
    if plt is None:
        # Dependency-free vector fallback for clean/demo machines.
        output_path = str(Path(output_path).with_suffix(".svg"))
        width, height, left, top, row_h, chart_w = 1100, 720, 260, 90, 46, 720
        max_value = max(float(plot_data["importance_pct"].max()), 1.0)
        elements = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '<rect width="100%" height="100%" fill="#101820"/>',
            f'<text x="{width/2}" y="42" text-anchor="middle" fill="white" font-family="Arial" font-size="24" font-weight="bold">{escape(title)}</text>',
        ]
        for index, row in enumerate(plot_data.itertuples(index=False)):
            y = top + index * row_h
            bar_width = float(row.importance_pct) / max_value * chart_w
            elements.extend([
                f'<text x="{left-15}" y="{y+20}" text-anchor="end" fill="#dbe7ef" font-family="Arial" font-size="16">{escape(str(row.feature))}</text>',
                f'<rect x="{left}" y="{y}" width="{bar_width:.1f}" height="28" rx="4" fill="{color}"/>',
                f'<text x="{left+bar_width+10:.1f}" y="{y+20}" fill="white" font-family="Arial" font-size="15">{row.importance_pct:.1f}%</text>',
            ])
        elements.append('</svg>')
        Path(output_path).write_text("\n".join(elements), encoding="utf-8")
        return output_path

    fig, ax = plt.subplots(figsize=(11, 7))
    bars = ax.barh(plot_data["feature"], plot_data["importance_pct"], color=color)
    ax.bar_label(bars, fmt="%.1f%%", padding=4, fontsize=9)
    ax.set_title(title, fontsize=15, weight="bold", pad=14)
    ax.set_xlabel("Share of total model gain (%)")
    ax.set_ylabel("Feature")
    ax.grid(axis="x", alpha=0.2)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_xlim(0, max(plot_data["importance_pct"].max() * 1.18, 1))
    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return output_path


def main():
    print("Generating feature-importance charts (Task 31)...")
    colors = {"15m": "#00b4d8", "30m": "#ffb703", "60m": "#fb8500"}
    all_importance = []

    for horizon in HORIZONS:
        importance = load_importance(horizon)
        importance["horizon"] = horizon
        all_importance.append(importance)
        output = save_chart(
            importance,
            f"What drives the {horizon} traffic forecast?",
            f"feature_importance_{horizon}.png",
            colors[horizon],
        )
        print(f"  Saved {output}")

    detail = pd.concat(all_importance, ignore_index=True)
    detail.to_csv("feature_importance.csv", index=False)

    # Normalize each horizon first so one model's raw gain scale cannot dominate.
    combined = (
        detail.groupby("feature", as_index=False)["importance_pct"]
        .mean()
        .sort_values("importance_pct", ascending=False)
    )
    output = save_chart(
        combined,
        "What drives traffic forecasts across all horizons?",
        "feature_importance.png",
        "#00b4d8",
    )
    print(f"  Saved {output} (combined slide chart)")
    print("  Saved feature_importance.csv (full numeric results)")


if __name__ == "__main__":
    main()
