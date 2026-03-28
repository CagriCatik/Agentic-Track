#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    from evaluation.eval_lib import answer_is_abstention, load_answers, normalize
except ModuleNotFoundError:  # pragma: no cover
    from eval_lib import answer_is_abstention, load_answers, normalize


def _contains_any(answer: str, values: list[str]) -> bool:
    normalized_answer = normalize(answer)
    return any(normalize(value) in normalized_answer for value in values if value)


def _has_citation(answer: str) -> bool:
    return "**📚 Quellen:**" in answer


def score_case(case: dict[str, Any], answer: str) -> dict[str, Any]:
    checks = list(case.get("checks", []))
    check_results: list[dict[str, Any]] = []
    score = 0
    max_score = 0

    for check in checks:
        kind = str(check.get("kind", "")).strip()
        passed = False
        weight = 1
        note = kind

        if kind == "contains_any":
            values = [str(value) for value in check.get("values", [])]
            passed = _contains_any(answer, values)
            note = f"contains_any={values}"
            weight = 2
        elif kind == "citation":
            passed = _has_citation(answer)
            note = "citation"
            weight = 1
        elif kind == "abstain":
            passed = answer_is_abstention(answer)
            note = "abstain"
            weight = 3
        else:
            raise ValueError(f"Unsupported check kind: {kind}")

        max_score += weight
        if passed:
            score += weight
        check_results.append({"kind": kind, "passed": passed, "weight": weight, "note": note})

    return {
        "id": case.get("id", ""),
        "type": case.get("type", "unknown"),
        "prompt": case.get("prompt", ""),
        "score": score,
        "max_score": max_score,
        "passed": score == max_score,
        "answer": answer,
        "checks": check_results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Score corpus-agnostic evaluation answers.")
    parser.add_argument("--pack", default="evaluation/corpus_eval_pack.json", help="Evaluation pack JSON path")
    parser.add_argument("--answers", required=True, help="Answers JSONL/JSON path")
    parser.add_argument("--out", default="evaluation/eval_scores.json", help="Output score JSON path")
    args = parser.parse_args()

    pack_path = Path(args.pack)
    answers_path = Path(args.answers)
    if not pack_path.exists():
        print(f"Error: pack file not found: {pack_path}", file=sys.stderr)
        return 2
    if not answers_path.exists():
        print(f"Error: answers file not found: {answers_path}", file=sys.stderr)
        return 2

    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    answers = load_answers(answers_path)

    per_case = []
    total_score = 0
    max_score = 0
    answered = 0

    for case in pack.get("cases", []):
        case_id = str(case.get("id", "")).strip()
        answer = answers.get(case_id, "")
        if answer:
            answered += 1
        scored = score_case(case, answer)
        per_case.append(scored)
        total_score += scored["score"]
        max_score += scored["max_score"]

    percentage = round((total_score / max_score) * 100, 2) if max_score else 0.0
    payload = {
        "pack_id": pack.get("pack_id", "unknown_pack"),
        "version": pack.get("version", "unknown"),
        "case_count": len(pack.get("cases", [])),
        "answered": answered,
        "total_score": total_score,
        "max_score": max_score,
        "percentage": percentage,
        "per_case": per_case,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Score: {total_score} / {max_score} ({percentage}%)")
    print(f"Saved scores to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
