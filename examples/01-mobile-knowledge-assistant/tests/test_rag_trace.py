import sys
from argparse import ArgumentTypeError
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from rag_trace import build_trace, positive_int


ROOT = Path(__file__).resolve().parents[1]


class RagTraceTest(unittest.TestCase):
    def test_trace_contains_retrieved_contexts_prompt_and_answer(self):
        trace = build_trace("移动端为什么不能直接保存模型 API Key？", ROOT / "data" / "documents")

        self.assertEqual(trace["question"], "移动端为什么不能直接保存模型 API Key？")
        self.assertGreater(len(trace["retrieved_contexts"]), 0)
        self.assertEqual(trace["retrieved_contexts"][0]["section"], "API Key 管理")
        self.assertIn("来源 1", trace["prompt_messages"][1]["content"])
        self.assertIn("answer", trace)

    def test_trace_respects_top_k(self):
        trace = build_trace("移动端权限和隐私怎么处理？", ROOT / "data" / "documents", top_k=1)

        self.assertEqual(len(trace["retrieved_contexts"]), 1)

    def test_positive_int_rejects_non_positive_values(self):
        with self.assertRaises(ArgumentTypeError):
            positive_int("0")
        with self.assertRaises(ArgumentTypeError):
            positive_int("-1")

    def test_build_trace_rejects_invalid_top_k(self):
        with self.assertRaises(ValueError):
            build_trace("hello", ROOT / "data" / "documents", top_k=0)

    def test_build_trace_rejects_missing_docs_dir(self):
        with self.assertRaises(FileNotFoundError):
            build_trace("hello", ROOT / "missing-docs")

    def test_build_trace_rejects_empty_docs_dir(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError):
                build_trace("hello", Path(temp_dir))

    def test_cli_outputs_json_trace(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "rag_trace.py"),
                "--question",
                "移动端为什么不能直接保存模型 API Key？",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["retrieved_contexts"][0]["section"], "API Key 管理")

    def test_cli_reports_missing_docs_dir(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "rag_trace.py"),
                "--question",
                "hello",
                "--docs-dir",
                str(ROOT / "missing-docs"),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("docs_dir not found", result.stderr)


if __name__ == "__main__":
    unittest.main()
