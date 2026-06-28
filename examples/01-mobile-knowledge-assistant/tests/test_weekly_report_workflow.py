import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from weekly_report_workflow import build_draft, collect_inputs, run_workflow, validate_draft, validate_workflow


class WeeklyReportWorkflowTest(unittest.TestCase):
    def test_workflow_stops_at_confirmation_gate_by_default(self):
        result = run_workflow(ROOT / "data" / "workflow" / "weekly_report_inputs.json")

        self.assertEqual(result["status"], "waiting_confirmation")
        self.assertEqual(result["stop_reason"], "approval_required")
        self.assertEqual(result["steps"][-1]["name"], "human_confirmation")
        self.assertTrue(result["steps"][-1]["requires_confirmation"])
        self.assertIn("## 本周完成", result["draft"])
        self.assertTrue(result["validation"]["ok"])

    def test_workflow_publishes_only_after_approval(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "weekly.md"
            result = run_workflow(
                ROOT / "data" / "workflow" / "weekly_report_inputs.json",
                approve=True,
                output_path=output_path,
            )

            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["stop_reason"], "published")
            self.assertTrue(output_path.is_file())
            self.assertIn("移动端 AI 周报", output_path.read_text(encoding="utf-8"))

    def test_collect_inputs_requires_non_empty_lists(self):
        with self.assertRaises(ValueError):
            collect_inputs({"user_id": "u1", "week": "2026-W25", "tasks": []})

    def test_collect_inputs_rejects_malformed_list_items(self):
        payload = json.loads((ROOT / "data" / "workflow" / "weekly_report_inputs.json").read_text(encoding="utf-8"))
        payload["tasks"] = ["bad"]

        with self.assertRaises(ValueError):
            collect_inputs(payload)

    def test_collect_inputs_rejects_empty_required_fields(self):
        payload = json.loads((ROOT / "data" / "workflow" / "weekly_report_inputs.json").read_text(encoding="utf-8"))
        payload["tasks"][0]["impact"] = " "

        with self.assertRaises(ValueError):
            collect_inputs(payload)

    def test_validate_draft_reports_missing_sections(self):
        validation = validate_draft("# hello\n")

        self.assertFalse(validation["ok"])
        self.assertIn("## 本周完成", validation["errors"])

    def test_validate_workflow_checks_structured_risk_items(self):
        data = collect_inputs(json.loads((ROOT / "data" / "workflow" / "weekly_report_inputs.json").read_text(encoding="utf-8")))
        data["risks"] = [""]

        validation = validate_workflow(data, build_draft(data))

        self.assertFalse(validation["ok"])
        self.assertIn("risks must include at least one non-empty item", validation["errors"])

    def test_build_draft_keeps_risks_and_next_week_plan(self):
        data = collect_inputs(json.loads((ROOT / "data" / "workflow" / "weekly_report_inputs.json").read_text(encoding="utf-8")))

        draft = build_draft(data)

        self.assertIn("真实模型网关的流式协议尚未接入", draft)
        self.assertIn("接入真实模型网关流式协议", draft)

    def test_cli_outputs_waiting_confirmation(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "weekly_report_workflow.py")],
            check=True,
            capture_output=True,
            text=True,
        )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "waiting_confirmation")
        self.assertEqual(payload["steps"][-1]["name"], "human_confirmation")

    def test_cli_writes_output_when_approved(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "weekly.md"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "weekly_report_workflow.py"),
                    "--approve",
                    "--out",
                    str(output_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "complete")
            self.assertIn("weekly.md", payload["published_to"])
            self.assertTrue(output_path.is_file())
            self.assertIn("移动端 AI 周报", output_path.read_text(encoding="utf-8"))

    def test_cli_approve_without_output_is_dry_run(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "weekly_report_workflow.py"), "--approve"],
            check=True,
            capture_output=True,
            text=True,
        )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "dry_run")
        self.assertEqual(payload["stop_reason"], "dry_run")
        self.assertEqual(payload["published_to"], "dry-run")

    def test_cli_output_without_approval_does_not_write_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "weekly.md"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "weekly_report_workflow.py"),
                    "--out",
                    str(output_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "waiting_confirmation")
            self.assertFalse(output_path.exists())

    def test_cli_reports_output_write_errors_without_traceback(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "weekly_report_workflow.py"),
                    "--approve",
                    "--out",
                    temp_dir,
                ],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Is a directory", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_cli_rejects_malformed_list_items_without_traceback(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "bad.json"
            payload = json.loads((ROOT / "data" / "workflow" / "weekly_report_inputs.json").read_text(encoding="utf-8"))
            payload["tasks"] = ["bad"]
            input_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "weekly_report_workflow.py"),
                    "--input",
                    str(input_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("tasks[0] must be an object", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_cli_reports_missing_input(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "weekly_report_workflow.py"),
                "--input",
                str(ROOT / "missing-workflow.json"),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("workflow input not found", result.stderr)


if __name__ == "__main__":
    unittest.main()
