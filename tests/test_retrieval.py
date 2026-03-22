from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from langchain_core.documents import Document

from projects.rag_app.catalog import get_catalog_path, upsert_documents
from projects.rag_app.retrieval import HybridRetriever, build_match_expressions, plan_query


class _FakeVectorStore:
    def __init__(self, results: list[tuple[Document, float]]) -> None:
        self._results = results

    def similarity_search_with_relevance_scores(
        self,
        query: str,
        k: int = 4,
    ) -> list[tuple[Document, float]]:
        return self._results[:k]


class HybridRetrieverTests(unittest.TestCase):
    def test_short_entity_query_prefers_exact_catalog_match(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vector_db_dir = Path(temp_dir)
            relevant_doc = Document(
                page_content="Basiswissen Softwaretest covers software testing fundamentals.",
                metadata={
                    "chunk_id": "catalog-title",
                    "source_key": "books/Basiswissen_Softwaretest.pdf",
                    "source_path": "books/Basiswissen_Softwaretest.pdf",
                    "source_name": "Basiswissen_Softwaretest.pdf",
                    "title": "Basiswissen Softwaretest",
                    "author": "Andreas Spillner, Tilo Linz",
                    "page": 1,
                    "chunk": 0,
                },
            )
            upsert_documents(
                get_catalog_path(vector_db_dir),
                ["catalog-title"],
                [relevant_doc],
            )

            fake_vector_store = _FakeVectorStore(
                [
                    (
                        Document(
                            page_content="Irrelevant content about deployment automation.",
                            metadata={
                                "chunk_id": "sem-1",
                                "source_key": "irrelevant.txt",
                                "source_path": "irrelevant.txt",
                                "source_name": "irrelevant.txt",
                                "page": 1,
                                "chunk": 0,
                            },
                        ),
                        0.92,
                    )
                ]
            )

            retriever = HybridRetriever(
                vector_store=fake_vector_store,
                vector_db_dir=vector_db_dir,
                top_k=3,
                semantic_k=3,
                lexical_k=3,
            )

            docs = retriever.invoke("Basiswissen Softwaretest")

            self.assertEqual(docs[0].metadata["title"], "Basiswissen Softwaretest")
            self.assertGreater(docs[0].metadata["term_overlap"], 0.5)

    def test_query_plan_keeps_quoted_phrases_and_acronyms(self) -> None:
        plan = plan_query('Explain "Open Diagnostic Data Exchange" and ODX connectors')
        expressions = build_match_expressions(
            'Explain "Open Diagnostic Data Exchange" and ODX connectors',
            plan,
        )

        self.assertIn("ODX", expressions)
        self.assertIn('"Open Diagnostic Data Exchange"', expressions)
        self.assertIn("connectors", plan.keywords)

    def test_source_filename_lookup_uses_normalized_filename_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vector_db_dir = Path(temp_dir)
            relevant_doc = Document(
                page_content="Basiswissen Softwaretest is a testing reference.",
                metadata={
                    "chunk_id": "catalog-file",
                    "source_key": "books/Basiswissen_Softwaretest.pdf",
                    "source_path": "books/Basiswissen_Softwaretest.pdf",
                    "source_name": "Basiswissen_Softwaretest.pdf",
                    "title": "Basiswissen Softwaretest",
                    "author": "Andreas Spillner, Tilo Linz",
                    "page": 1,
                    "chunk": 0,
                },
            )
            upsert_documents(
                get_catalog_path(vector_db_dir),
                ["catalog-file"],
                [relevant_doc],
            )

            retriever = HybridRetriever(
                vector_store=_FakeVectorStore([]),
                vector_db_dir=vector_db_dir,
                top_k=1,
                semantic_k=1,
                lexical_k=6,
            )

            docs = retriever.invoke(
                "What is the exact title of the indexed source file `Basiswissen_Softwaretest.pdf`?"
            )

            self.assertEqual(docs[0].metadata["source_name"], "Basiswissen_Softwaretest.pdf")


if __name__ == "__main__":
    unittest.main()
