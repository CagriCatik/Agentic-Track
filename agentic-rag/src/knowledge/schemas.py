"""Medallion Architecture Pydantic schemas — Bronze → Silver → Gold — provenance never lost."""

from __future__ import annotations

import hashlib
from typing import Any, List, Optional

from pydantic import BaseModel, Field


# ── Shared Helpers ──────────────────────────────────────────────

def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class ManifestEntry(BaseModel):
    """Tracks ingest state per source file for incremental re-ingestion."""

    filename: str
    file_hash: str
    num_chunks: int
    last_ingested: str


# ══════════════════════════════════════════════════════════════
# BRONZE — Raw ingestion artifacts
# ══════════════════════════════════════════════════════════════

class BronzeRecord(BaseModel):
    """Raw ingestion record. Source of truth; never cleaned or normalised."""

    doc_id: str = Field(..., description="Deterministic: sha256(file_hash)[:12]")
    source_file: str = Field(..., description="Original filename, e.g. Funktionale_Sicherheit.pdf")
    source_path: str
    file_hash: str = Field(..., description="SHA-256 of raw PDF bytes")
    file_size_bytes: int
    ingestion_timestamp: str = Field(..., description="ISO-8601 UTC")
    extraction_method: str = "pymupdf4llm"
    extractor_version: str = "1.0"
    raw_markdown: str = Field(..., description="Full doc markdown — no cleaning applied")
    raw_json: Optional[List[dict[str, Any]]] = Field(
        default=None, description="Raw page_chunks list from pymupdf4llm"
    )
    page_count: int


# ══════════════════════════════════════════════════════════════
# SILVER — Structured, cleaned, provenance-rich
# ══════════════════════════════════════════════════════════════

class FigureRecord(BaseModel):
    """A figure block extracted from a page."""

    label: str = ""
    caption: str = ""
    ocr_text: str = ""


class SilverRecord(BaseModel):
    """One page-or-block of structured, cleaned content with provenance."""

    # Identity
    chunk_id: str = Field(..., description="Deterministic: doc_id + chunk_index")
    chunk_index: int
    chunk_hash: str = Field(..., description="SHA-256 of clean_text")

    # Text
    raw_text: str
    clean_text: str
    text_for_embedding: str

    # Structure
    section_path: str = ""
    section_header: str = ""
    subsection_header: str = ""

    # Provenance
    pdf_page_start: int = 1
    pdf_page_end: int = 1
    doc_page_start: int = 1
    doc_page_end: int = 1

    # Content typing
    chunk_type: str = "body_text"  # body_text | table | figure_caption | figure_ocr
    contains_figure: bool = False
    contains_table: bool = False
    contains_ocr_image_text: bool = False
    figures: List[FigureRecord] = Field(default_factory=list)

    @classmethod
    def from_page(
        cls,
        doc_id: str,
        chunk_index: int,
        raw_text: str,
        page_num: int,
        section_header: str = "",
    ) -> "SilverRecord":
        clean = raw_text.replace("\x00", "").strip()
        contains_tbl = "|" in clean and "---" in clean
        chunk_id = f"sil_{doc_id}_{chunk_index}"
        return cls(
            chunk_id=chunk_id,
            chunk_index=chunk_index,
            chunk_hash=_sha256(clean),
            raw_text=raw_text,
            clean_text=clean,
            text_for_embedding=(f"{section_header}\n{clean}").strip(),
            section_path=section_header,
            section_header=section_header,
            pdf_page_start=page_num,
            pdf_page_end=page_num,
            doc_page_start=page_num,
            doc_page_end=page_num,
            chunk_type="table" if contains_tbl else "body_text",
            contains_table=contains_tbl,
        )


# ══════════════════════════════════════════════════════════════
# GOLD — Canonical retrieval-ready chunks
# ══════════════════════════════════════════════════════════════

class GoldRecord(BaseModel):
    """Final retrieval-ready chunk — vendor-neutral, lineage complete."""

    # Identity
    gold_chunk_id: str = Field(..., description="Deterministic: sha256(retrieval_text)[:16]")
    doc_id: str
    source_file: str

    # Retrieval fields
    retrieval_text: str = Field(..., description="What is stored in ChromaDB as the document text")
    display_text: str = Field(..., description="Human-readable answer text shown to user")
    title: str

    # Structure
    section_path: str = ""
    parent_section: str = ""

    # Provenance
    pdf_page_start: int
    pdf_page_end: int
    doc_page_start: int
    doc_page_end: int

    # Metadata for filtering
    chunk_type: str
    contains_figure: bool
    contains_table: bool
    token_count: int
    char_count: int
    language: str = "de"

    # Lineage (never lose this)
    silver_chunk_ids: List[str]
    bronze_doc_id: str
    gold_hash: str
    build_version: str = "v2.0"

    # Citation
    citation_label: str = Field(..., description="E.g. Funktionale_Sicherheit.pdf, Seite 42")
    citation_anchor: str = Field(..., description="Unique anchor for deep-linking")

    def to_chroma_metadata(self) -> dict[str, Any]:
        """Flat dict accepted by ChromaDB as metadata (no nested objects)."""
        return {
            "doc_id": self.doc_id,
            "source_file": self.source_file,
            "section_path": self.section_path,
            "chunk_type": self.chunk_type,
            "pdf_page_start": self.pdf_page_start,
            "pdf_page_end": self.pdf_page_end,
            "contains_figure": self.contains_figure,
            "contains_table": self.contains_table,
            "citation_label": self.citation_label,
            "citation_anchor": self.citation_anchor,
            "build_version": self.build_version,
        }

    @classmethod
    def from_silver(cls, silver: "SilverRecord", bronze: "BronzeRecord") -> "GoldRecord":
        title = bronze.source_file.removesuffix(".pdf").replace("_", " ")
        retrieval_text = (
            f"Quelle: {bronze.source_file}\n"
            f"Seite: {silver.pdf_page_start}\n"
            f"Abschnitt: {silver.section_header}\n\n"
            f"{silver.text_for_embedding}"
        )
        gold_hash = _sha256(retrieval_text)
        gold_id = f"gld_{gold_hash[:16]}"
        parent = silver.section_path.split(" / ")[0] if " / " in silver.section_path else silver.section_path

        return cls(
            gold_chunk_id=gold_id,
            doc_id=bronze.doc_id,
            source_file=bronze.source_file,
            retrieval_text=retrieval_text,
            display_text=silver.clean_text,
            title=title,
            section_path=silver.section_path,
            parent_section=parent,
            pdf_page_start=silver.pdf_page_start,
            pdf_page_end=silver.pdf_page_end,
            doc_page_start=silver.doc_page_start,
            doc_page_end=silver.doc_page_end,
            chunk_type=silver.chunk_type,
            contains_figure=silver.contains_figure,
            contains_table=silver.contains_table,
            token_count=len(silver.clean_text.split()),
            char_count=len(silver.clean_text),
            silver_chunk_ids=[silver.chunk_id],
            bronze_doc_id=bronze.doc_id,
            gold_hash=gold_hash,
            citation_label=f"{bronze.source_file}, Seite {silver.pdf_page_start}",
            citation_anchor=silver.chunk_id,
        )


# ── Legacy compat shim  ─────────────────────────────────────────
# The retrieval layer and citation formatter still read 'source_file' and 'page_start'
# from ChromaDB metadata. GoldRecord.to_chroma_metadata() writes 'pdf_page_start',
# so we also inject 'page_start' as an alias to avoid breaking existing node code.
_GOLD_CHROMA_ALIASES = {"page_start": "pdf_page_start"}
