#!/usr/bin/env python3
import json
import argparse
from pathlib import Path
import sys
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

def main():
    parser = argparse.ArgumentParser(description="Visualize evaluation scores.")
    parser.add_argument(
        "--scores",
        default="evaluation/eval_scores.json",
        help="Path to the JSON scores file (default: evaluation/eval_scores.json)",
    )
    parser.add_argument(
        "--out",
        default="evaluation/eval_scores.png",
        help="Output image path (default: evaluation/eval_scores.png)",
    )
    args = parser.parse_args()

    scores_path = Path(args.scores)
    if not scores_path.exists():
        print(f"Error: Scores file not found at {scores_path}")
        return 1

    with open(scores_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Prepare data for plotting
    questions = []
    scores = []
    second_metric = []

    rows = data.get("per_case", []) or data.get("per_question", [])
    if not rows:
        print("Error: score file contains no per-case/per-question rows")
        return 1
    for row in rows:
        questions.append(row["id"])
        scores.append(row["score"])
        if "matched_groups" in row:
            second_metric.append(row["matched_groups"])
        else:
            second_metric.append(row.get("max_score", 0))

    df = pd.DataFrame({
        "Case": questions,
        "Score": scores,
        "Secondary Metric": second_metric
    })

    # Set up the plot style
    sns.set_theme(style="whitegrid")
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    fig.suptitle(f"Evaluation Results: {data.get('pack_id', 'Unknown Pack')}\nOverall Score: {data.get('total_score', 0)} / {data.get('max_score', 0)} ({data.get('percentage', 0)}%)", fontsize=16)

    # Plot 1: Scores per question
    sns.barplot(data=df, x="Case", y="Score", ax=ax1, palette="viridis", hue="Case", legend=False)
    ax1.set_title("Score per Case", fontsize=14)
    ax1.set_ylabel("Score")
    ax1.set_ylim(0, max(3.2, max(scores, default=0) + 0.5))
    ax1.tick_params(axis='x', rotation=45)

    # Plot 2: Secondary metric
    sns.barplot(data=df, x="Case", y="Secondary Metric", ax=ax2, palette="plasma", hue="Case", legend=False)
    ax2.set_title("Secondary Metric per Case", fontsize=14)
    ax2.set_ylabel("Value")
    ax2.set_ylim(0, max(5.2, max(second_metric, default=0) + 0.5))
    ax2.tick_params(axis='x', rotation=45)

    plt.tight_layout()
    
    # Save the plot
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    print(f"Plot successfully saved to {out_path}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
