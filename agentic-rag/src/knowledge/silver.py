"""Silver Layer — structured, cleaned, provenance-rich records from Bronze."""

from __future__ import annotations

import json
import re
from pathlib import Path

from langchain_core.documents import Document

from src.knowledge.schemas import BronzeRecord, FigureRecord, SilverRecord, _sha256


# ── Markdown structure helpers ──────────────────────────────────

_HEADER_RE = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
_FIGURE_CAPTION_RE = re.compile(r"(Figure|Abbildung|Abb\.)\s*[\d\.]+[:\.]?\s*(.+)", re.IGNORECASE)
_TABLE_RE = re.compile(r"^\|.+\|$", re.MULTILINE)


def _extract_section_header(text: str, previous_header: str) -> str:
    """Return the closest section header above this text block."""
    for _, title in _HEADER_RE.findall(text):
        return title.strip()
    return previous_header


def _extract_figures(text: str) -> list[FigureRecord]:
    figures = []
    for match in _FIGURE_CAPTION_RE.finditer(text):
        figures.append(FigureRecord(label=match.group(1), caption=match.group(2).strip()))
    return figures


def _detect_chunk_type(text: str) -> str:
    if _TABLE_RE.search(text):
        return "table"
    if _FIGURE_CAPTION_RE.search(text):
        return "figure_caption"
    return "body_text"


def _clean_text(raw: str) -> str:
    """Remove null bytes, collapse excessive blank lines."""
    text = raw.replace("\x00", "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ── Main transformation ─────────────────────────────────────────

def process_bronze_to_silver(bronze: BronzeRecord) -> list[SilverRecord]:
    """Transform one Bronze record into a list of structured Silver records (per page)."""
    silver_records: list[SilverRecord] = []

    # Use page_chunks if available (PDFs); fall back to splitting whole markdown for .md files
    pages: list[dict] = bronze.raw_json or [{"text": bronze.raw_markdown, "metadata": {"page": 1}}]

    current_section = ""
    current_subsection = ""

    for i, page_data in enumerate(pages):
        raw_text: str = page_data.get("text", "").strip()
        if not raw_text:
            continue

        page_num: int = page_data.get("metadata", {}).get("page_number", i + 1)

        # Update section tracking
        for level, header_text in _HEADER_RE.findall(raw_text):
            if level == "#":
                current_section = header_text.strip()
                current_subsection = ""
            elif level == "##":
                current_subsection = header_text.strip()

        section_path = " / ".join(filter(None, [current_section, current_subsection]))
        clean = _clean_text(raw_text)
        figures = _extract_figures(raw_text)
        chunk_type = _detect_chunk_type(raw_text)

        record = SilverRecord(
            chunk_id=f"sil_{bronze.doc_id}_{i:04d}",
            chunk_index=i,
            chunk_hash=_sha256(clean),
            raw_text=raw_text,
            clean_text=clean,
            text_for_embedding=(f"{section_path}\n{clean}").strip() if section_path else clean,
            section_path=section_path,
            section_header=current_section,
            subsection_header=current_subsection,
            pdf_page_start=page_num,
            pdf_page_end=page_num,
            doc_page_start=page_num,
            doc_page_end=page_num,
            chunk_type=chunk_type,
            contains_figure=bool(figures),
            contains_table=chunk_type == "table",
            contains_ocr_image_text=False,
            figures=figures,
        )
        silver_records.append(record)

    return silver_records


# ── Persistence ─────────────────────────────────────────────────

def save_silver(records: list[SilverRecord], source_file: str, silver_dir: Path) -> Path:
    """Persist Silver records to disk as JSON."""
    silver_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(source_file).stem
    out = silver_dir / f"{stem}.silver.json"
    payload = [r.model_dump() for r in records]
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def load_silver(silver_dir: Path) -> list[SilverRecord]:
    """Load all Silver records from disk."""
    records: list[SilverRecord] = []
    for f in sorted(silver_dir.glob("*.silver.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        for item in data:
            records.append(SilverRecord(**item))
    return records


def silver_to_langchain_docs(records: list[SilverRecord]) -> list[Document]:
    """Convert Silver records into LangChain Documents (for chunking or legacy compat)."""
    docs = []
    for r in records:
        docs.append(Document(
            page_content=r.text_for_embedding,
            metadata={
                "source_file": r.chunk_id.split("_")[1] if "_" in r.chunk_id else r.chunk_id,
                "page_start": r.pdf_page_start,
                "page_end": r.pdf_page_end,
                "section_header": r.section_header,
                "chunk_type": r.chunk_type,
                "silver_chunk_id": r.chunk_id,
            },
        ))
    return docs
