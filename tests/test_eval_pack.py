from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from evaluation.generate_eval_pack import build_pack
from evaluation.score_eval_pack import score_case


class EvaluationPackTests(unittest.TestCase):
    def test_generated_pack_contains_positive_and_negative_cases(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            corpus_dir = Path(temp_dir)
            (corpus_dir / "guide.md").write_text(
                "Guide to Diagnostics\nAuthor: Jane Doe\n\nThis guide explains diagnostic workflows and communication stacks.",
                encoding="utf-8",
            )

            pack = build_pack(corpus_dir=corpus_dir, max_sources=2)
            case_types = {case["type"] for case in pack["cases"]}

            self.assertIn("title_lookup", case_types)
            self.assertIn("author_lookup", case_types)
            self.assertIn("source_grounding", case_types)
            self.assertIn("negative_missing_title", case_types)
            self.assertIn("negative_missing_acronym", case_types)

    def test_score_case_requires_abstention_for_negative_case(self) -> None:
        case = {
            "id": "C999",
            "type": "negative_missing_title",
            "prompt": "Is there a source titled X?",
            "checks": [{"kind": "abstain"}],
        }

        passed = score_case(case, "I don't know based on the indexed sources.")
        failed = score_case(case, "Yes, it exists.")

        self.assertTrue(passed["passed"])
        self.assertFalse(failed["passed"])


if __name__ == "__main__":
    unittest.main()
