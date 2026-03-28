#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

try:
    from evaluation.eval_lib import write_answers_jsonl
except ModuleNotFoundError:
    from eval_lib import write_answers_jsonl

from src.orchestration.graph import app

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.description = "Run the LangGraph RAG agent against a corpus-agnostic evaluation pack"
    parser.add_argument("--pack", default=str(repo_root / "evaluation" / "corpus_eval_pack.json"), help="Evaluation pack JSON path")
    parser.add_argument("--out", default=str(repo_root / "evaluation" / "eval_answers.jsonl"), help="Output answers JSONL path")
    args = parser.parse_args()

    pack_path = Path(args.pack)
    if not pack_path.exists():
        print(f"Error: {pack_path} not found. Please provide a valid pack.", file=sys.stderr)
        return 2

    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    cases = pack.get("cases", [])[:3]
    if not cases:
        print(f"Error: no cases found in {pack_path}", file=sys.stderr)
        return 2

    print(f"Running {len(cases)} evaluation cases against Agentic RAG graph...")
    answers: list[dict[str, object]] = []
    
    for index, case in enumerate(cases, start=1):
        prompt = str(case.get("prompt", "")).strip()
        case_id = str(case.get("id", index))
        print(f"[{index}/{len(cases)}] {case_id}: {prompt}")
        
        initial_state = {
            "question": prompt,
            "generation": "",
            "documents": [],
            "datasource": "",
            "is_safe": "",
            "web_search_needed": "no",
            "retry_count": 0,
        }
        
        final_state = app.invoke(initial_state)
        answer = str(final_state.get("generation", "")).strip()
        documents = final_state.get("documents", [])
        
        # Collect underlying cited sources
        sources = list({doc.metadata.get("source_file", "?") for doc in documents})
        
        answers.append(
            {
                "id": case_id,
                "type": case.get("type", "unknown"),
                "prompt": prompt,
                "answer": answer,
                "cited_indices": sources,
                "support_status": final_state.get("datasource", "unknown"),
                "support_confidence": final_state.get("retry_count", 0),
            }
        )

    out_path = Path(args.out)
    write_answers_jsonl(out_path, answers)
    print(f"Saved answers to {out_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
