"""Unit tests for the schemas module."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.knowledge.schemas import ChunkMetadata, ManifestEntry


def test_chunk_metadata_citation_single_page():
    """Citation format for a single page."""
    meta = ChunkMetadata(
        source_file="Funktionale_Sicherheit.pdf",
        page_start=42,
        page_end=42,
        section_header="3.2 ASIL",
    )
    assert meta.citation() == "[Quelle: Funktionale_Sicherheit.pdf, Seite 42]"


def test_chunk_metadata_citation_multi_page():
    """Citation format for a multi-page span."""
    meta = ChunkMetadata(
        source_file="Bussysteme.pdf",
        page_start=10,
        page_end=12,
    )
    assert meta.citation() == "[Quelle: Bussysteme.pdf, Seiten 10–12]"


def test_chunk_metadata_to_store():
    """to_store_metadata returns a flat dict for ChromaDB."""
    meta = ChunkMetadata(
        source_file="test.pdf",
        page_start=1,
        page_end=1,
    )
    store = meta.to_store_metadata()
    assert isinstance(store, dict)
    assert store["source_file"] == "test.pdf"
    assert store["page_start"] == 1


def test_manifest_entry():
    """ManifestEntry model works correctly."""
    entry = ManifestEntry(
        filename="test.pdf",
        file_hash="abc123",
        num_chunks=50,
        last_ingested="2026-03-27T14:00:00+00:00",
    )
    assert entry.filename == "test.pdf"
    assert entry.num_chunks == 50
