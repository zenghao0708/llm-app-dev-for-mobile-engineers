import json
import subprocess
import sys
import tempfile
import unittest
from argparse import ArgumentTypeError
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from file_triage_agent import SafeFileTools, ToolCall, ToolRegistry, positive_int, run_agent


class FileTriageAgentTest(unittest.TestCase):
    def test_agent_reads_documents_and_reports_keyword_coverage(self):
        report = run_agent(
            "检查移动端知识库是否覆盖密钥、流式输出、权限和脱敏要求",
            ROOT / "data" / "documents",
            keywords=["API Key", "流式输出", "权限", "脱敏"],
            max_steps=8,
        )

        self.assertEqual(report["status"], "complete")
        self.assertEqual(report["stop_reason"], "all_documents_read")
        self.assertEqual(report["document_count"], 3)
        self.assertEqual(report["trace"][0]["act"]["tool"], "list_markdown_files")
        self.assertIn("mobile_ai_api.md", report["coverage"]["API Key"])
        self.assertIn("mobile_ai_api.md", report["coverage"]["流式输出"])
        self.assertIn("privacy_review.md", report["coverage"]["权限"])
        self.assertIn("crash_analysis.md", report["coverage"]["脱敏"])

    def test_agent_stops_when_max_steps_is_reached(self):
        report = run_agent(
            "只允许一步时不能完成所有文件分析",
            ROOT / "data" / "documents",
            keywords=["API Key"],
            max_steps=1,
        )

        self.assertEqual(report["status"], "stopped")
        self.assertEqual(report["stop_reason"], "max_steps_exceeded")
        self.assertEqual(report["document_count"], 0)

    def test_agent_reports_missing_keywords(self):
        report = run_agent(
            "检查是否有不存在的能力说明",
            ROOT / "data" / "documents",
            keywords=["不存在的关键词"],
            max_steps=8,
        )

        self.assertEqual(report["missing_keywords"], ["不存在的关键词"])
        self.assertIn("不存在的关键词", report["next_actions"][0])

    def test_safe_file_tools_reject_path_traversal(self):
        tools = SafeFileTools(ROOT / "data" / "documents")

        with self.assertRaises(ValueError):
            tools.read_markdown_file("../documents/mobile_ai_api.md")
        with self.assertRaises(ValueError):
            tools.read_markdown_file("/tmp/mobile_ai_api.md")
        with self.assertRaises(ValueError):
            tools.read_markdown_file("nested/mobile_ai_api.md")
        with self.assertRaises(ValueError):
            tools.read_markdown_file("notes.txt")

    def test_tool_registry_rejects_unknown_tools(self):
        registry = ToolRegistry(SafeFileTools(ROOT / "data" / "documents"))

        with self.assertRaises(ValueError):
            registry.call(ToolCall("delete_file", {"filename": "mobile_ai_api.md"}))

    def test_positive_int_rejects_non_positive_values(self):
        with self.assertRaises(ArgumentTypeError):
            positive_int("0")

    def test_agent_rejects_empty_docs_dir(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError):
                run_agent("hello", Path(temp_dir), keywords=["hello"])

    def test_cli_outputs_json_report(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "file_triage_agent.py"),
                "--goal",
                "检查知识库是否覆盖流式输出",
                "--keyword",
                "流式输出",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "complete")
        self.assertEqual(payload["stop_reason"], "all_documents_read")
        self.assertEqual(payload["document_count"], 3)
        self.assertEqual(len(payload["trace"]), 4)
        self.assertEqual(payload["trace"][0]["act"]["tool"], "list_markdown_files")
        for step in payload["trace"]:
            self.assertIn("observe", step)
            self.assertIn("plan", step)
            self.assertIn("act", step)
            self.assertIn("reflect", step)
        self.assertIn("mobile_ai_api.md", payload["coverage"]["流式输出"])

    def test_cli_reports_missing_docs_dir(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "file_triage_agent.py"),
                "--goal",
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
