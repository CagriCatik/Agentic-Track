"""Evaluation runner — processes eval_dataset.json through the full pipeline."""

from __future__ import annotations

import json
import sys
import time
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evaluation.metrics import QueryMetrics, EvalReport
from evaluation.judge import judge_faithfulness, judge_relevance
from evaluation.report import save_report


def run_evaluation(dataset_path: str) -> EvalReport:
    """Run the evaluation pipeline on a golden dataset."""
    from src.orchestration.graph import app

    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    report = EvalReport()

    print(f"\n📊 Running evaluation on {len(dataset)} queries...\n")

    for i, entry in enumerate(dataset):
        question = entry["question"]
        expected_source = entry.get("expected_source", "")
        expected_keywords = entry.get("expected_keywords", [])

        print(f"  [{i+1}/{len(dataset)}] {question}")

        qm = QueryMetrics(
            question=question,
            expected_source=expected_source,
            expected_keywords=expected_keywords,
        )

        # Time the full pipeline
        start = time.time()

        initial_state = {
            "question": question,
            "generation": "",
            "documents": [],
            "datasource": "",
            "is_safe": "",
            "web_search_needed": "no",
            "retry_count": 0,
        }

        result = app.invoke(initial_state)
        qm.e2e_latency_s = time.time() - start

        # Extract results
        qm.generation = result.get("generation", "")
        documents = result.get("documents", [])

        # Retrieval metrics
        qm.retrieved_sources = [
            doc.metadata.get("source_file", "") for doc in documents
        ]
        if expected_source:
            qm.source_hit = expected_source in qm.retrieved_sources
            relevant = sum(1 for s in qm.retrieved_sources if s == expected_source)
            qm.precision_at_k = relevant / len(qm.retrieved_sources) if qm.retrieved_sources else 0.0

        # Generation metrics (via LLM-as-Judge)
        if documents and qm.generation:
            doc_texts = "\n\n".join(d.page_content for d in documents)
            qm.faithfulness = judge_faithfulness(doc_texts, qm.generation)
            qm.answer_relevance = judge_relevance(question, qm.generation)
            qm.citation_found = expected_source in qm.generation

        print(f"    → source_hit={qm.source_hit}, faithful={qm.faithfulness}, "
              f"relevant={qm.answer_relevance}, latency={qm.e2e_latency_s:.1f}s")

        report.query_results.append(qm)

    # Print summary
    summary = report.summary()
    print(f"\n{'=' * 50}")
    print("📊 EVALUATION SUMMARY")
    print(f"{'=' * 50}")
    for key, val in summary.items():
        print(f"  {key}: {val}")

    return report


def main():
    parser = argparse.ArgumentParser(description="Run RAG evaluation")
    parser.add_argument(
        "--dataset",
        required=True,
        help="Path to eval_dataset.json",
    )
    parser.add_argument(
        "--output-dir",
        default="./evaluation/reports",
        help="Directory for evaluation reports",
    )
    args = parser.parse_args()

    report = run_evaluation(args.dataset)
    save_report(report, args.output_dir)


if __name__ == "__main__":
    main()
