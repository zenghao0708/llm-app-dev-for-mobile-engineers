import json
import subprocess
import sys
import tempfile
import unittest
from argparse import ArgumentTypeError
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from answer_eval import AnswerEvalCase, CitationRequirement, evaluate, load_cases, positive_int, score_threshold


class AnswerEvalTest(unittest.TestCase):
    def test_default_cases_pass_quality_gate(self):
        cases = load_cases(ROOT / "data" / "eval" / "answer_eval_cases.json")

        payload = evaluate(cases, ROOT / "data" / "documents", top_k=3, min_score=0.8)

        self.assertEqual(payload["case_count"], 4)
        self.assertEqual(payload["pass_rate"], 1.0)
        self.assertGreaterEqual(payload["average_score"], 0.9)

    def test_missing_expected_terms_lower_score(self):
        case = AnswerEvalCase(
            id="missing_terms",
            question="移动端为什么不能直接保存模型 API Key？",
            expected_terms=("不存在的关键要点",),
            required_citation=CitationRequirement(source="mobile_ai_api.md", section="API Key 管理"),
        )

        payload = evaluate([case], ROOT / "data" / "documents", top_k=3, min_score=0.8)

        self.assertEqual(payload["passed_count"], 0)
        self.assertEqual(payload["results"][0]["missing_terms"], ["不存在的关键要点"])

    def test_partial_missing_expected_terms_still_fails_gate(self):
        case = AnswerEvalCase(
            id="partial_missing_terms",
            question="移动端为什么不能直接保存模型 API Key？",
            expected_terms=("反编译", "抓包", "不存在的关键要点"),
            required_citation=CitationRequirement(source="mobile_ai_api.md", section="API Key 管理"),
        )

        payload = evaluate([case], ROOT / "data" / "documents", top_k=3, min_score=0.8)

        self.assertEqual(payload["results"][0]["score"], 0.8)
        self.assertEqual(payload["passed_count"], 0)
        self.assertEqual(payload["results"][0]["missing_terms"], ["不存在的关键要点"])

    def test_missing_required_citation_fails_case(self):
        case = AnswerEvalCase(
            id="missing_citation",
            question="移动端长回答应该怎么展示，用户离开页面时怎么办？",
            expected_terms=("流式输出", "取消请求"),
            required_citation=CitationRequirement(source="missing.md", section="Missing"),
        )

        payload = evaluate([case], ROOT / "data" / "documents", top_k=3, min_score=0.8)

        self.assertEqual(payload["passed_count"], 0)
        self.assertFalse(payload["results"][0]["citation_hit"])

    def test_forbidden_terms_fail_even_when_other_scores_match(self):
        case = AnswerEvalCase(
            id="forbidden",
            question="移动端长回答应该怎么展示，用户离开页面时怎么办？",
            expected_terms=("流式输出", "逐步追加", "取消请求"),
            required_citation=CitationRequirement(source="mobile_ai_api.md", section="流式输出"),
            forbidden_terms=("流式输出",),
        )

        payload = evaluate([case], ROOT / "data" / "documents", top_k=3, min_score=0.1)

        self.assertEqual(payload["passed_count"], 0)
        self.assertEqual(payload["results"][0]["forbidden_hits"], ["流式输出"])

    def test_load_cases_rejects_malformed_data(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bad.json"
            path.write_text("[]", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_cases(path)

            path.write_text('[{"id":"x","question":"q","expected_terms":["a"]}]', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_cases(path)

            path.write_text('[{"id":"x","question":"q","expected_terms":["a"],"required_citation":{"source":"s","section":" "}}]', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_cases(path)

    def test_cli_outputs_answer_metrics(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "answer_eval.py"), "--min-score", "0.8"],
            check=True,
            capture_output=True,
            text=True,
        )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["case_count"], 4)
        self.assertEqual(payload["pass_rate"], 1.0)

    def test_cli_returns_nonzero_when_quality_gate_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            cases_path = Path(temp_dir) / "failing_cases.json"
            cases_path.write_text(
                json.dumps(
                    [
                        {
                            "id": "cli_failure",
                            "question": "移动端为什么不能直接保存模型 API Key？",
                            "expected_terms": ["不存在的关键要点"],
                            "required_citation": {
                                "source": "mobile_ai_api.md",
                                "section": "API Key 管理",
                            },
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "answer_eval.py"),
                    "--cases",
                    str(cases_path),
                    "--min-score",
                    "0.8",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

        payload = json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(payload["passed_count"], 0)

    def test_cli_report_only_keeps_zero_exit_for_failed_cases(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            cases_path = Path(temp_dir) / "failing_cases.json"
            cases_path.write_text(
                json.dumps(
                    [
                        {
                            "id": "report_only",
                            "question": "移动端为什么不能直接保存模型 API Key？",
                            "expected_terms": ["不存在的关键要点"],
                            "required_citation": {
                                "source": "mobile_ai_api.md",
                                "section": "API Key 管理",
                            },
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "answer_eval.py"),
                    "--cases",
                    str(cases_path),
                    "--min-score",
                    "0.8",
                    "--report-only",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(payload["passed_count"], 0)

    def test_cli_reports_missing_cases_file_without_traceback(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "answer_eval.py"),
                "--cases",
                str(ROOT / "missing-answer-cases.json"),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cases file not found", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_argument_validators(self):
        self.assertEqual(positive_int("3"), 3)
        self.assertEqual(score_threshold("0.75"), 0.75)

        with self.assertRaises(ArgumentTypeError):
            positive_int("0")
        with self.assertRaises(ArgumentTypeError):
            score_threshold("1.5")


if __name__ == "__main__":
    unittest.main()
