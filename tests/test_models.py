from __future__ import annotations

import unittest

from projects.rag_app.models import select_models


class ModelSelectionTests(unittest.TestCase):
    def test_prefers_stronger_chat_model_over_tiny_qwen3(self) -> None:
        chat_model, embedding_model = select_models(
            [
                "qwen3:1.7b",
                "gpt-oss:20b",
                "nomic-embed-text:latest",
            ]
        )

        self.assertEqual(chat_model, "gpt-oss:20b")
        self.assertEqual(embedding_model, "nomic-embed-text:latest")

    def test_prefers_larger_variant_with_same_priority_family(self) -> None:
        chat_model, _ = select_models(
            [
                "gpt-oss:20b",
                "gpt-oss:120b-cloud",
                "nomic-embed-text:latest",
            ]
        )

        self.assertEqual(chat_model, "gpt-oss:120b-cloud")


if __name__ == "__main__":
    unittest.main()
