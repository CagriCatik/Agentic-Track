#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from projects.rag_app.citations import normalize_inline_citations
from projects.rag_app.config import AppConfig, build_parser
from projects.rag_app.graph import build_graph
from projects.rag_app.models import discover_ollama_models, select_models
from projects.rag_app.vector_index import build_retriever, index_corpus, index_requires_rebuild

try:
    from evaluation.eval_lib import write_answers_jsonl
    from evaluation.generate_eval_pack import build_pack
except ModuleNotFoundError:  # pragma: no cover
    from eval_lib import write_answers_jsonl
    from generate_eval_pack import build_pack


def main() -> int:
    parser = build_parser()
    parser.description = "Run the LangGraph RAG agent against a corpus-agnostic evaluation pack"
    parser.add_argument("--pack", default=str(repo_root / "evaluation" / "corpus_eval_pack.json"), help="Evaluation pack JSON path")
    parser.add_argument("--out", default=str(repo_root / "evaluation" / "eval_answers.jsonl"), help="Output answers JSONL path")
    parser.add_argument("--generate-pack", action="store_true", help="Generate the evaluation pack before running")
    parser.add_argument("--max-sources", type=int, default=4, help="When generating a pack, maximum number of sources to sample")
    args = parser.parse_args()

    config = AppConfig.from_sources(args)
    pack_path = Path(args.pack)

    if args.generate_pack or not pack_path.exists():
        pack = build_pack(corpus_dir=Path(config.corpus_dir), max_sources=max(1, args.max_sources))
        pack_path.parent.mkdir(parents=True, exist_ok=True)
        pack_path.write_text(json.dumps(pack, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Generated evaluation pack at {pack_path}")

    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    cases = pack.get("cases", [])
    if not cases:
        print(f"Error: no cases found in {pack_path}", file=sys.stderr)
        return 2

    available_models = discover_ollama_models(base_url=config.ollama_base_url)
    if not available_models:
        print("Error: no Ollama models discovered.", file=sys.stderr)
        return 2

    chat_model, embedding_model = select_models(
        available_models,
        forced_chat=config.chat_model,
        forced_embedding=config.embedding_model,
    )
    if not chat_model or not embedding_model:
        print("Error: could not resolve chat and embedding models.", file=sys.stderr)
        return 2

    rebuild_required = index_requires_rebuild(config.vector_db_dir)
    if config.index_on_start or config.reindex or rebuild_required:
        print("Indexing corpus if needed...")
        index_corpus(
            embedding_model=embedding_model,
            corpus_dir=config.corpus_dir,
            vector_db_dir=config.vector_db_dir,
            collection_name=config.collection_name,
            ollama_base_url=config.ollama_base_url,
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            force_reindex=(config.reindex or rebuild_required),
        )

    retriever = build_retriever(
        embedding_model=embedding_model,
        vector_db_dir=config.vector_db_dir,
        collection_name=config.collection_name,
        ollama_base_url=config.ollama_base_url,
        top_k=config.top_k,
        retrieval_candidates=config.retrieval_candidates,
        reranker_enabled=config.reranker_enabled,
        reranker_mode=config.reranker_mode,
        reranker_model=config.reranker_model or chat_model,
        reranker_top_n=config.reranker_top_n,
    )
    app = build_graph(
        chat_model=chat_model,
        temperature=config.temperature,
        system_prompt=config.system_prompt,
        retriever=retriever,
        ollama_base_url=config.ollama_base_url,
    )

    print(f"Running {len(cases)} evaluation cases...")
    answers: list[dict[str, object]] = []
    for index, case in enumerate(cases, start=1):
        prompt = str(case.get("prompt", "")).strip()
        case_id = str(case.get("id", index))
        print(f"[{index}/{len(cases)}] {case_id}: {prompt}")
        final_state = app.invoke({"question": prompt, "history": "", "revision_count": 0})
        answer, cited_indices = normalize_inline_citations(str(final_state.get("generation", "")).strip())
        answers.append(
            {
                "id": case_id,
                "type": case.get("type", "unknown"),
                "prompt": prompt,
                "answer": answer,
                "cited_indices": cited_indices,
                "support_status": final_state.get("support_status", "unknown"),
                "support_confidence": final_state.get("support_confidence", 0.0),
            }
        )

    out_path = Path(args.out)
    write_answers_jsonl(out_path, answers)
    print(f"Saved answers to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
