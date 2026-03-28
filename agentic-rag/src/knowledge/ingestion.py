"""Ingestion Orchestrator — Bronze → Silver → Gold → ChromaDB pipeline.

This module is the single entry point for all ingestion.
It delegates each stage to the dedicated layer module.
"""

from __future__ import annotations

from pathlib import Path

from src.config import get_settings, resolve_path
from src.knowledge.bronze import (
    load_bronze,
    process_md_to_bronze,
    process_pdf_to_bronze,
    save_bronze,
)
from src.knowledge.gold import load_gold, process_silver_to_gold, save_gold
from src.knowledge.silver import (
    load_silver,
    process_bronze_to_silver,
    save_silver,
)
from src.knowledge.versioning import (
    _hash_file,
    get_changed_files,
    load_manifest,
    save_manifest,
    update_manifest_entry,
)
from src.retrieval.vector_store import index_gold_into_chromadb


def run_ingestion(force: bool = False) -> dict:
    """Execute the full Bronze → Silver → Gold → ChromaDB ingestion pipeline.

    Args:
        force: If True, re-ingest all files even if unchanged.

    Returns:
        Summary dict: {"parsed": int, "silver": int, "gold": int, "vectors": int}
    """
    settings = get_settings()
    bronze_dir = resolve_path(settings.data.bronze_dir)
    silver_dir = resolve_path(settings.data.silver_dir)
    gold_json_dir = resolve_path("./data/gold/json")
    
    # NEW: Scan both locations
    corpus_dir = resolve_path("../corpus")
    site_dir = resolve_path("../site")
    search_dirs = [corpus_dir, site_dir]

    # ── 1. Determine which files need processing ───────────────────
    if force:
        source_files = get_changed_files(search_dirs) # This will return all if manifest is empty or we force it logic-wise
        # Actually get_changed_files already checks hashes. If we want FORCE, we need to bypass hash check.
        source_files = []
        for sdir in search_dirs:
            if sdir.exists():
                for ext in ["*.pdf", "*.md", "*.html", "*.htm"]:
                    source_files.extend(list(sdir.rglob(ext)))
    else:
        source_files = get_changed_files(search_dirs)

    if not source_files:
        print("✅ All files are up-to-date. No ingestion needed.")
        return {"parsed": 0, "silver": 0, "gold": 0, "vectors": 0}

    print(f"📄 Found {len(source_files)} file(s) to process.")
    manifest = load_manifest()
    total_silver = 0
    total_gold_per_file: list = []

    # ── 2. Per-file: Bronze → Silver → Gold (JSON) ─────────────────
    from src.knowledge.bronze import process_html_to_bronze

    for src_path in source_files:
        print(f"\n  🥉 [Bronze] Extracting: {src_path.name}")
        try:
            ext = src_path.suffix.lower()
            if ext == ".pdf":
                bronze = process_pdf_to_bronze(src_path)
            elif ext in [".html", ".htm"]:
                bronze = process_html_to_bronze(src_path)
            else:
                bronze = process_md_to_bronze(src_path)
        except Exception as e:
            print(f"     ⚠️  Bronze extraction failed: {e}")
            continue

        save_bronze(bronze, bronze_dir)
        print(f"     → {bronze.page_count} pages | doc_id={bronze.doc_id}")

        print(f"  🥈 [Silver] Structuring: {src_path.name}")
        silver_records = process_bronze_to_silver(bronze)
        save_silver(silver_records, src_path.name, silver_dir)
        total_silver += len(silver_records)
        print(f"     → {len(silver_records)} Silver records")

        print(f"  🥇 [Gold] Chunking: {src_path.name}")
        gold_records = process_silver_to_gold(silver_records, bronze)
        save_gold(gold_records, src_path.name, gold_json_dir)
        total_gold_per_file.extend(gold_records)
        print(f"     → {len(gold_records)} Gold chunks")

        # Update manifest using absolute path as key
        file_hash = _hash_file(src_path)
        manifest_key = str(src_path.absolute())
        manifest[manifest_key] = update_manifest_entry(src_path.name, file_hash, len(gold_records))

    save_manifest(manifest)

    # ── 3. Rebuild ChromaDB index from ALL Gold records ────────────
    print(f"\n🔢 Loading full Gold store for ChromaDB rebuild...")
    all_gold = load_gold(gold_json_dir)

    if not all_gold:
        print("⚠️  No Gold records found — skipping ChromaDB indexing.")
        return {"parsed": len(source_files), "silver": total_silver, "gold": 0, "vectors": 0}

    print(f"   → {len(all_gold)} Gold records total")
    print("🔗 [Chroma] Building vector index from Gold...")
    index_gold_into_chromadb(all_gold)

    summary = {
        "parsed": len(source_files),
        "silver": total_silver,
        "gold": len(all_gold),
        "vectors": len(all_gold),
    }
    print(f"\n✅ Ingestion complete: {summary}")
    return summary
