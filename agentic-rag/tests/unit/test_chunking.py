"""Unit tests for the chunking module."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from langchain_core.documents import Document
from src.knowledge.chunking import chunk_documents


def test_chunks_are_created():
    """Chunking produces output from input documents."""
    docs = [
        Document(
            page_content="A" * 2000,
            metadata={"source_file": "test.pdf", "page_start": 1, "page_end": 1, "section_header": "Intro"},
        )
    ]
    chunks = chunk_documents(docs)
    assert len(chunks) > 1, "A 2000-char doc should produce multiple chunks"


def test_metadata_inherited():
    """Each chunk inherits metadata from its parent document."""
    docs = [
        Document(
            page_content="Dies ist ein langer Testtext. " * 100,
            metadata={"source_file": "safety.pdf", "page_start": 42, "page_end": 42, "section_header": "ASIL"},
        )
    ]
    chunks = chunk_documents(docs)
    for chunk in chunks:
        assert chunk.metadata["source_file"] == "safety.pdf"
        assert chunk.metadata["page_start"] == 42
        assert chunk.metadata["section_header"] == "ASIL"


def test_chunk_hash_unique():
    """Each chunk gets a unique content hash."""
    docs = [
        Document(
            page_content="Abschnitt eins. " * 50 + "Abschnitt zwei. " * 50,
            metadata={"source_file": "test.pdf", "page_start": 1, "page_end": 1, "section_header": ""},
        )
    ]
    chunks = chunk_documents(docs)
    hashes = [c.metadata["chunk_hash"] for c in chunks]
    assert len(hashes) == len(set(hashes)), "Chunk hashes should be unique"


def test_empty_input():
    """Chunking handles empty input gracefully."""
    chunks = chunk_documents([])
    assert chunks == []
