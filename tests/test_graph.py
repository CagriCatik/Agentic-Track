from __future__ import annotations

import unittest

from langchain_core.documents import Document

from projects.rag_app.graph import NO_ANSWER_DE, NO_ANSWER_EN, assess_support, localize_no_answer
from projects.rag_app.retrieval import bundle_from_documents


class GraphSupportTests(unittest.TestCase):
    def test_assess_support_accepts_strong_overlap(self) -> None:
        bundle = bundle_from_documents(
            "What is zonal architecture?",
            [
                Document(
                    page_content="Zonal architecture groups vehicle functions by physical zone and reduces wiring complexity.",
                    metadata={"title": "Vehicle Architecture", "source_name": "arch.txt", "page": 1},
                )
            ],
        )

        support = assess_support(bundle)

        self.assertEqual(support.status, "supported")
        self.assertGreaterEqual(support.confidence, 0.6)

    def test_assess_support_rejects_weak_overlap(self) -> None:
        bundle = bundle_from_documents(
            "What is zonal architecture?",
            [
                Document(
                    page_content="This chapter discusses software deployment pipelines and release checklists.",
                    metadata={"title": "Deployment", "source_name": "deploy.txt", "page": 1},
                )
            ],
        )

        support = assess_support(bundle)

        self.assertEqual(support.status, "unsupported")

    def test_assess_support_rejects_single_term_match_for_two_term_query(self) -> None:
        bundle = bundle_from_documents(
            "Who wrote Moby Dick?",
            [
                Document(
                    page_content="The battery stack becomes thick under heavy packaging constraints.",
                    metadata={"title": "Battery Design", "source_name": "battery.txt", "page": 1},
                )
            ],
        )

        support = assess_support(bundle)

        self.assertEqual(support.status, "unsupported")

    def test_assess_support_accepts_creator_query_with_exact_terms(self) -> None:
        bundle = bundle_from_documents(
            "Who is the creator of this app?",
            [
                Document(
                    page_content="The creator of this app is Cagri Catik.",
                    metadata={"title": "Agentic Track App Notes", "source_name": "test.md", "page": 1},
                )
            ],
        )

        support = assess_support(bundle)

        self.assertEqual(support.status, "supported")
        self.assertGreaterEqual(support.confidence, 0.6)

    def test_localize_no_answer_uses_question_language(self) -> None:
        self.assertEqual(localize_no_answer("Was ist ODX?"), NO_ANSWER_DE)
        self.assertEqual(localize_no_answer("What is ODX?"), NO_ANSWER_EN)


if __name__ == "__main__":
    unittest.main()
