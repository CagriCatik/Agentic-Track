from __future__ import annotations

import unittest

from langchain_core.documents import Document

from projects.rag_app.reranker import FeatureReranker, PipelineReranker, RerankerConfig
from projects.rag_app.retrieval import QueryPlan, RankedDocument, RetrievalBundle


class _FakeJudge:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text

    def invoke(self, input, config=None):  # noqa: ANN001
        class _Response:
            def __init__(self, content: str) -> None:
                self.content = content

        return _Response(self.response_text)


class FeatureRerankerTests(unittest.TestCase):
    def test_reranker_promotes_stronger_term_alignment(self) -> None:
        plan = QueryPlan(
            raw_query="What is zonal architecture?",
            keywords=["zonal", "architecture"],
            quoted_phrases=[],
            uppercase_terms=[],
            token_count=4,
            is_short_query=True,
        )
        weak = RankedDocument(
            document=Document(
                page_content="This text discusses software delivery pipelines.",
                metadata={"title": "Deployment Notes", "source_name": "deploy.txt"},
            ),
            fused_score=0.04,
            overlap=0.0,
            lexical_rank=1,
        )
        strong = RankedDocument(
            document=Document(
                page_content="Zonal architecture groups vehicle functions by physical zone.",
                metadata={"title": "Zonal Architecture", "source_name": "arch.txt"},
            ),
            fused_score=0.03,
            overlap=1.0,
            semantic_rank=2,
            semantic_score=0.8,
        )
        bundle = RetrievalBundle(query=plan.raw_query, plan=plan, hits=[weak, strong])

        reranked = FeatureReranker().rerank(bundle)

        self.assertEqual(reranked.hits[0].document.metadata["title"], "Zonal Architecture")
        self.assertGreater(reranked.hits[0].rerank_score or 0.0, reranked.hits[1].rerank_score or 0.0)

    def test_pipeline_reranker_uses_llm_stage_to_break_close_candidates(self) -> None:
        plan = QueryPlan(
            raw_query="What is the deployment owner for the catalog service?",
            keywords=["deployment", "owner", "catalog", "service"],
            quoted_phrases=[],
            uppercase_terms=[],
            token_count=8,
            is_short_query=False,
        )
        close_hits = [
            RankedDocument(
                document=Document(
                    page_content="Catalog deployment notes mention rollout status but not ownership.",
                    metadata={"title": "Deployment Notes", "source_name": "deploy.txt"},
                ),
                fused_score=0.05,
                overlap=0.5,
                semantic_rank=1,
                semantic_score=0.82,
            ),
            RankedDocument(
                document=Document(
                    page_content="The catalog service owner is the platform team.",
                    metadata={"title": "Service Inventory", "source_name": "inventory.xlsx"},
                ),
                fused_score=0.048,
                overlap=0.75,
                semantic_rank=2,
                semantic_score=0.8,
            ),
        ]
        bundle = RetrievalBundle(query=plan.raw_query, plan=plan, hits=close_hits)
        reranker = PipelineReranker(
            config=RerankerConfig(mode="llm", llm_top_n=2, llm_weight=0.75),
            judge=_FakeJudge(
                '{"ranking": [{"candidate": 1, "score": 0.96, "reason": "explicit owner statement"}, '
                '{"candidate": 2, "score": 0.31, "reason": "deployment context only"}]}'
            ),
        )

        reranked = reranker.rerank(bundle)

        self.assertEqual(reranked.hits[0].document.metadata["title"], "Service Inventory")
        self.assertIn("explicit owner statement", reranked.hits[0].document.metadata["llm_rerank_reason"])
        self.assertGreater(
            reranked.hits[0].document.metadata["llm_rerank_score"],
            reranked.hits[1].document.metadata["llm_rerank_score"],
        )


if __name__ == "__main__":
    unittest.main()
