import json
import subprocess
import sys
import tempfile
import unittest
from argparse import ArgumentTypeError
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from rag_eval import evaluate, load_cases, positive_int


class RagEvalTest(unittest.TestCase):
    def test_eval_default_cases_reach_full_hit_rate(self):
        cases = load_cases(ROOT / "data" / "eval" / "rag_eval_cases.json")

        payload = evaluate(cases, ROOT / "data" / "documents", top_k=3)

        self.assertEqual(payload["case_count"], 7)
        self.assertEqual(payload["hit_rate"], 1.0)
        self.assertGreaterEqual(payload["mrr"], 0.8)

    def test_eval_marks_miss_when_expected_section_is_wrong(self):
        cases = load_cases(ROOT / "data" / "eval" / "rag_eval_cases.json")
        wrong_case = cases[0].__class__(
            id="wrong",
            question=cases[0].question,
            expected_source="missing.md",
            expected_section="missing",
        )

        payload = evaluate([wrong_case], ROOT / "data" / "documents", top_k=3)

        self.assertEqual(payload["hit_rate"], 0)
        self.assertIsNone(payload["results"][0]["rank"])

    def test_eval_tracks_rank_and_top_k_boundary(self):
        cases = load_cases(ROOT / "data" / "eval" / "rag_eval_cases.json")
        expected_case = cases[0].__class__(
            id="rank_two",
            question="alpha beta",
            expected_source="b-target.md",
            expected_section="Target",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            docs_dir = Path(temp_dir)
            (docs_dir / "a-distractor.md").write_text(
                "# Alpha\n\n## Distractor\n\nalpha beta\n",
                encoding="utf-8",
            )
            (docs_dir / "b-target.md").write_text(
                "# Alpha\n\n## Target\n\nalpha\n",
                encoding="utf-8",
            )

            miss_payload = evaluate([expected_case], docs_dir, top_k=1)
            hit_payload = evaluate([expected_case], docs_dir, top_k=2)

        self.assertEqual(miss_payload["hit_rate"], 0)
        self.assertIsNone(miss_payload["results"][0]["rank"])
        self.assertEqual(hit_payload["hit_rate"], 1.0)
        self.assertEqual(hit_payload["results"][0]["rank"], 2)
        self.assertEqual(hit_payload["mrr"], 0.5)

    def test_evaluate_rejects_empty_cases(self):
        with self.assertRaises(ValueError):
            evaluate([], ROOT / "data" / "documents", top_k=3)

    def test_load_cases_rejects_empty_or_invalid_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "cases.json"
            path.write_text("[]", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_cases(path)

            path.write_text('{"id":"not-array"}', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_cases(path)

    def test_load_cases_requires_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "cases.json"
            path.write_text('[{"id":"x","question":"hello"}]', encoding="utf-8")

            with self.assertRaises(ValueError):
                load_cases(path)

    def test_top_k_must_be_positive(self):
        cases = load_cases(ROOT / "data" / "eval" / "rag_eval_cases.json")

        with self.assertRaises(ValueError):
            evaluate(cases, ROOT / "data" / "documents", top_k=0)
        with self.assertRaises(ArgumentTypeError):
            positive_int("0")

    def test_cli_outputs_metrics(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "rag_eval.py"), "--top-k", "3"],
            check=True,
            capture_output=True,
            text=True,
        )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["case_count"], 7)
        self.assertEqual(payload["hit_rate"], 1.0)

    def test_cli_reports_missing_cases_file(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "rag_eval.py"),
                "--cases",
                str(ROOT / "missing-cases.json"),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cases file not found", result.stderr)


if __name__ == "__main__":
    unittest.main()
