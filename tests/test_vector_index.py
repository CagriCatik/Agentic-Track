from __future__ import annotations

import unittest
from pathlib import Path

from projects.rag_app.loaders import SourceDocument
from projects.rag_app.vector_index import _chunk_source_document, _source_key


class VectorIndexTests(unittest.TestCase):
    def test_source_key_is_environment_independent(self) -> None:
        windows_root = Path("C:/Users/test/corbus")
        docker_root = Path("/app/corbus")

        windows_path = windows_root / "nested" / "Book.pdf"
        docker_path = docker_root / "nested" / "Book.pdf"

        self.assertEqual(_source_key(windows_root, windows_path), "nested/Book.pdf")
        self.assertEqual(_source_key(docker_root, docker_path), "nested/Book.pdf")

    def test_chunk_source_document_preserves_corpus_metadata(self) -> None:
        source_document = SourceDocument(
            source_key="notes/architecture.md",
            source_name="architecture.md",
            source_path="notes/architecture.md",
            source_type="md",
            title="Architecture Notes",
            author="",
            segments=[
                "This document explains how zonal controllers reduce wiring complexity.",
            ],
        )

        documents, ids = _chunk_source_document(
            source_document,
            chunk_size=80,
            chunk_overlap=0,
        )

        self.assertEqual(len(documents), 1)
        self.assertEqual(len(ids), 1)
        self.assertEqual(documents[0].metadata["title"], "Architecture Notes")
        self.assertEqual(documents[0].metadata["source_type"], "md")
        self.assertEqual(documents[0].metadata["page"], 1)
        self.assertIn("zonal controllers", documents[0].page_content)


if __name__ == "__main__":
    unittest.main()
