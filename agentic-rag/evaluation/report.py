"""Report generator — outputs evaluation results as JSON and Markdown."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from evaluation.metrics import EvalReport


def save_report(report: EvalReport, output_dir: str = "./evaluation/reports") -> None:
    """Save evaluation report as JSON and Markdown."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")

    # JSON report
    json_path = out / f"eval_report_{timestamp}.json"
    json_data = {
        "timestamp": timestamp,
        "summary": report.summary(),
        "queries": [q.to_dict() for q in report.query_results],
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    # Markdown report
    md_path = out / f"eval_report_{timestamp}.md"
    summary = report.summary()

    lines = [
        f"# Evaluation Report — {timestamp}",
        "",
        "## Summary",
        "",
        "| Metric | Value | Target |",
        "|--------|-------|--------|",
        f"| Precision@K | {summary['avg_precision_at_k']:.3f} | ≥ 0.70 |",
        f"| Source Accuracy | {summary['source_accuracy']:.3f} | ≥ 0.90 |",
        f"| Faithfulness | {summary['faithfulness_rate']:.3f} | ≥ 0.85 |",
        f"| Answer Relevance | {summary['relevance_rate']:.3f} | ≥ 0.80 |",
        f"| Avg E2E Latency | {summary['avg_e2e_latency_s']:.1f}s | < 30s |",
        f"| Avg Retrieval Latency | {summary['avg_retrieval_latency_s']:.1f}s | < 2s |",
        "",
        "## Per-Query Results",
        "",
        "| # | Question | Source Hit | Faithful | Relevant | Latency |",
        "|---|----------|-----------|----------|----------|---------|",
    ]

    for i, q in enumerate(report.query_results):
        lines.append(
            f"| {i+1} | {q.question[:50]}... | "
            f"{'✅' if q.source_hit else '❌'} | "
            f"{'✅' if q.faithfulness == 'yes' else '❌'} | "
            f"{'✅' if q.answer_relevance == 'yes' else '❌'} | "
            f"{q.e2e_latency_s:.1f}s |"
        )

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n📄 Reports saved:")
    print(f"   JSON: {json_path}")
    print(f"   MD:   {md_path}")
