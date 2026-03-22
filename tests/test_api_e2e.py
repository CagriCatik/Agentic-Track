from __future__ import annotations

import importlib
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from langchain_core.documents import Document


class _FakeChain:
    def __init__(
        self,
        *,
        answer: str,
        docs: list[Document],
        support_status: str = "supported",
        support_confidence: float = 0.9,
    ) -> None:
        self.answer = answer
        self.docs = docs
        self.support_status = support_status
        self.support_confidence = support_confidence
        self.calls: list[tuple[dict, dict | None]] = []

    def invoke(self, payload, config=None):  # noqa: ANN001
        self.calls.append((payload, config))
        return {
            "generation": self.answer,
            "docs": self.docs,
            "support_status": self.support_status,
            "support_confidence": self.support_confidence,
        }


class ApiE2ETests(unittest.TestCase):
    def setUp(self) -> None:
        self.env = patch.dict(
            os.environ,
            {
                "RAG_SKIP_STARTUP_BUILD": "true",
                "RAG_API_KEY": "test-key",
            },
            clear=False,
        )
        self.env.start()
        module = importlib.import_module("projects.rag_app.openai_compatible_api")
        self.api = importlib.reload(module)

    def tearDown(self) -> None:
        self.env.stop()

    def _make_state(self, chain: _FakeChain):
        return self.api.RuntimeState(
            model_id="agentic-rag",
            chat_model="gpt-oss:120b-cloud",
            embedding_model="nomic-embed-text:latest",
            temperature=0.2,
            top_k=3,
            retrieval_candidates=12,
            reranker_enabled=True,
            reranker_mode="llm",
            reranker_model="gpt-oss:120b-cloud",
            reranker_top_n=6,
            ollama_base_url="http://localhost:11434",
            retriever=object(),
            chain=chain,
            available_models=["gpt-oss:120b-cloud", "nomic-embed-text:latest"],
            corpus_dir="corbus",
            vector_db_dir="data/chroma",
            collection_name="agentic_rag_docs",
            index_stats={"total_chunks_in_index": 3},
            last_request_trace=None,
            startup_error=None,
        )

    def test_models_endpoint_requires_key_and_lists_rag_model(self) -> None:
        self.api.APP_STATE = self._make_state(_FakeChain(answer="unused", docs=[]))
        client = TestClient(self.api.app)

        unauthorized = client.get("/v1/models")
        authorized = client.get("/v1/models", headers={"Authorization": "Bearer test-key"})

        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(authorized.status_code, 200)
        self.assertEqual(authorized.json()["data"][0]["id"], "agentic-rag")

    def test_chat_completions_returns_grounded_answer_with_compact_cited_sources(self) -> None:
        chain = _FakeChain(
            answer="ODX means Open Diagnostic Data Exchange [1].",
            docs=[
                Document(
                    page_content="Open Diagnostic Data Exchange (ODX) defines diagnostic data exchange.",
                    metadata={
                        "title": "Diagnostic Standards",
                        "author": "ACME",
                        "source_name": "diag.pdf",
                        "page": 4,
                    },
                )
            ],
        )
        self.api.APP_STATE = self._make_state(chain)
        client = TestClient(self.api.app)

        response = client.post(
            "/v1/chat/completions",
            headers={"Authorization": "Bearer test-key"},
            json={
                "model": "agentic-rag",
                "messages": [{"role": "user", "content": "What is ODX?"}],
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        answer = payload["choices"][0]["message"]["content"]
        self.assertIn("Open Diagnostic Data Exchange", answer)
        self.assertIn("Sources:", answer)
        self.assertIn("diag.pdf", answer)
        self.assertEqual(chain.calls[0][0]["question"], "What is ODX?")
        self.assertEqual(self.api.APP_STATE.last_request_trace["support_status"], "supported")
        self.assertEqual(self.api.APP_STATE.last_request_trace["reranker_mode"], "llm")

    def test_chat_completions_skips_reference_suffix_when_support_is_unsupported(self) -> None:
        chain = _FakeChain(
            answer="I don't know based on the indexed sources.",
            docs=[
                Document(
                    page_content="This document is unrelated.",
                    metadata={"title": "Other", "source_name": "other.txt", "page": 1},
                )
            ],
            support_status="unsupported",
            support_confidence=0.12,
        )
        self.api.APP_STATE = self._make_state(chain)
        client = TestClient(self.api.app)

        response = client.post(
            "/v1/chat/completions",
            headers={"Authorization": "Bearer test-key"},
            json={
                "model": "agentic-rag",
                "messages": [{"role": "user", "content": "Who wrote Moby Dick?"}],
            },
        )

        self.assertEqual(response.status_code, 200)
        answer = response.json()["choices"][0]["message"]["content"]
        self.assertNotIn("Cited Sources", answer)
        self.assertEqual(self.api.APP_STATE.last_request_trace["support_status"], "unsupported")

    def test_chat_completions_normalizes_citations_and_shows_only_cited_sources(self) -> None:
        chain = _FakeChain(
            answer="The creator of this app is Cagri\u202fCatik \u30101\u2020L1-L2\u3011.",
            docs=[
                Document(
                    page_content="The application was created by Cagri Catik.",
                    metadata={"title": "Agentic Track App Notes", "source_name": "test.md", "page": 1},
                ),
                Document(
                    page_content="Irrelevant information about software testing.",
                    metadata={"title": "Basiswissen Softwaretest", "source_name": "Basiswissen_Softwaretest.pdf", "page": 283},
                ),
            ],
        )
        self.api.APP_STATE = self._make_state(chain)
        client = TestClient(self.api.app)

        response = client.post(
            "/v1/chat/completions",
            headers={"Authorization": "Bearer test-key"},
            json={
                "model": "agentic-rag",
                "messages": [{"role": "user", "content": "Who is the creator of this app?"}],
            },
        )

        self.assertEqual(response.status_code, 200)
        answer = response.json()["choices"][0]["message"]["content"]
        self.assertIn("Cagri Catik [1]", answer)
        self.assertIn("Sources:", answer)
        self.assertIn("`test.md`", answer)
        self.assertNotIn("Basiswissen_Softwaretest.pdf", answer)
        self.assertEqual(self.api.APP_STATE.last_request_trace["cited_indices"], [1])

    def test_openapi_schema_exposes_bearer_auth_for_protected_routes(self) -> None:
        self.api.APP_STATE = self._make_state(_FakeChain(answer="unused", docs=[]))
        client = TestClient(self.api.app)

        response = client.get("/openapi.json")

        self.assertEqual(response.status_code, 200)
        schema = response.json()
        self.assertIn("BearerAuth", schema["components"]["securitySchemes"])
        post_operation = schema["paths"]["/v1/chat/completions"]["post"]
        self.assertIn({"BearerAuth": []}, post_operation["security"])


if __name__ == "__main__":
    unittest.main()
