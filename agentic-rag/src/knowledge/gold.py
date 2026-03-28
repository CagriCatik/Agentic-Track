"""Gold Layer — canonical retrieval-ready chunks with full lineage."""

from __future__ import annotations

import json
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import get_settings
from src.knowledge.schemas import BronzeRecord, GoldRecord, SilverRecord, _sha256


# ── Silver → Gold chunking ──────────────────────────────────────

def _split_silver(silver: SilverRecord, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Split a Silver record's text into retrieval-sized pieces."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return [t for t in splitter.split_text(silver.text_for_embedding) if t.strip()]


def process_silver_to_gold(
    silver_records: list[SilverRecord],
    bronze: BronzeRecord,
) -> list[GoldRecord]:
    """Transform Silver records into canonical Gold chunks.

    One Silver page can fan-out into multiple Gold chunks if it exceeds
    the configured chunk_size.
    """
    settings = get_settings()
    chunk_size = settings.ingestion.chunk_size
    chunk_overlap = settings.ingestion.chunk_overlap

    gold_records: list[GoldRecord] = []
    title = bronze.source_file.removesuffix(".pdf").removesuffix(".md").replace("_", " ")

    for silver in silver_records:
        # Fan-out large pages into multiple Gold chunks
        text_splits = _split_silver(silver, chunk_size, chunk_overlap)

        for split_idx, split_text in enumerate(text_splits):
            retrieval_text = (
                f"Quelle: {bronze.source_file}\n"
                f"Seite: {silver.pdf_page_start}\n"
                f"Abschnitt: {silver.section_header or 'Allgemein'}\n\n"
                f"{split_text}"
            )
            gold_hash = _sha256(retrieval_text)
            gold_chunk_id = f"gld_{gold_hash[:16]}"
            parent = (
                silver.section_path.split(" / ")[0]
                if " / " in silver.section_path
                else silver.section_path
            )

            rec = GoldRecord(
                gold_chunk_id=gold_chunk_id,
                doc_id=bronze.doc_id,
                source_file=bronze.source_file,
                retrieval_text=retrieval_text,
                display_text=split_text,
                title=title,
                section_path=silver.section_path,
                parent_section=parent,
                pdf_page_start=silver.pdf_page_start,
                pdf_page_end=silver.pdf_page_end,
                doc_page_start=silver.doc_page_start,
                doc_page_end=silver.doc_page_end,
                chunk_type=silver.chunk_type,
                contains_figure=silver.contains_figure or (split_idx == 0 and bool(silver.figures)),
                contains_table=silver.contains_table,
                token_count=len(split_text.split()),
                char_count=len(split_text),
                silver_chunk_ids=[silver.chunk_id],
                bronze_doc_id=bronze.doc_id,
                gold_hash=gold_hash,
                citation_label=f"{bronze.source_file}, Seite {silver.pdf_page_start}",
                citation_anchor=f"{silver.chunk_id}_{split_idx}",
            )
            gold_records.append(rec)

    return gold_records


# ── Persistence ─────────────────────────────────────────────────

def save_gold(records: list[GoldRecord], source_file: str, gold_dir: Path) -> Path:
    """Persist Gold records to disk as JSON (vendor-neutral)."""
    gold_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(source_file).stem
    out = gold_dir / f"{stem}.gold.json"
    payload = [r.model_dump() for r in records]
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def load_gold(gold_json_dir: Path) -> list[GoldRecord]:
    """Load all Gold records from the JSON Gold store (not ChromaDB)."""
    records: list[GoldRecord] = []
    for f in sorted(gold_json_dir.glob("*.gold.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        for item in data:
            records.append(GoldRecord(**item))
    return records
