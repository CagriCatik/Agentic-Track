"""Bronze Layer — raw PDF ingestion. Source of truth; never cleaned."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from src.knowledge.schemas import BronzeRecord


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def process_pdf_to_bronze(pdf_path: Path) -> BronzeRecord:
    """Ingest a PDF into Bronze — extract raw Markdown via pymupdf4llm."""
    import pymupdf4llm

    raw_bytes = pdf_path.read_bytes()
    file_hash = hashlib.sha256(raw_bytes).hexdigest()
    doc_id = f"doc_{file_hash[:12]}"

    # RAW extraction — page_chunks=True to preserve page boundaries
    page_chunks: list[dict] = pymupdf4llm.to_markdown(str(pdf_path), page_chunks=True)
    raw_markdown = "\n\n".join(c.get("text", "") for c in page_chunks)

    return BronzeRecord(
        doc_id=doc_id,
        source_file=pdf_path.name,
        source_path=str(pdf_path.resolve()),
        file_hash=file_hash,
        file_size_bytes=len(raw_bytes),
        ingestion_timestamp=datetime.now(timezone.utc).isoformat(),
        raw_markdown=raw_markdown,
        raw_json=page_chunks,
        page_count=len(page_chunks),
    )


def process_md_to_bronze(md_path: Path) -> BronzeRecord:
    """Ingest a Markdown file into Bronze (no extractor needed)."""
    raw_bytes = md_path.read_bytes()
    file_hash = hashlib.sha256(raw_bytes).hexdigest()
    doc_id = f"doc_{file_hash[:12]}"
    text = raw_bytes.decode("utf-8", errors="replace")

    return BronzeRecord(
        doc_id=doc_id,
        source_file=md_path.name,
        source_path=str(md_path.resolve()),
        file_hash=file_hash,
        file_size_bytes=len(raw_bytes),
        ingestion_timestamp=datetime.now(timezone.utc).isoformat(),
        extraction_method="native_markdown",
        raw_markdown=text,
        raw_json=None,
        page_count=1,
    )


def process_html_to_bronze(html_path: Path) -> BronzeRecord:
    """Ingest an HTML file into Bronze — convert to Markdown via MarkItDown."""
    from markitdown import MarkItDown

    raw_bytes = html_path.read_bytes()
    file_hash = hashlib.sha256(raw_bytes).hexdigest()
    doc_id = f"doc_{file_hash[:12]}"

    md = MarkItDown()
    result = md.convert(str(html_path))
    raw_markdown = result.text_content

    return BronzeRecord(
        doc_id=doc_id,
        source_file=html_path.name,
        source_path=str(html_path.resolve()),
        file_hash=file_hash,
        file_size_bytes=len(raw_bytes),
        ingestion_timestamp=datetime.now(timezone.utc).isoformat(),
        extraction_method="markitdown_html",
        raw_markdown=raw_markdown,
        raw_json=None,
        page_count=1,
    )


def save_bronze(record: BronzeRecord, bronze_dir: Path) -> Path:
    """Persist Bronze record to disk as JSON."""
    bronze_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(record.source_file).stem
    out = bronze_dir / f"{stem}.bronze.json"
    out.write_text(record.model_dump_json(indent=2), encoding="utf-8")
    return out


def load_bronze(bronze_dir: Path) -> list[BronzeRecord]:
    """Load all Bronze records from disk."""
    records = []
    for f in sorted(bronze_dir.glob("*.bronze.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        records.append(BronzeRecord(**data))
    return records
