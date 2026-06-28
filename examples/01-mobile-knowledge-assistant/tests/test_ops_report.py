import json
import subprocess
import sys
import tempfile
import unittest
from argparse import ArgumentTypeError
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from ops_report import (
    _percentile,
    build_report,
    classify_status,
    load_pricing,
    load_records,
    positive_int,
    retry_schedule,
    stable_cache_key,
)


class OpsReportTest(unittest.TestCase):
    def test_default_report_contains_cost_latency_and_reliability_metrics(self):
        records = load_records(ROOT / "data" / "observability" / "model_call_logs.json")
        pricing = load_pricing(ROOT / "data" / "observability" / "model_pricing.json")

        payload = build_report(records, pricing, latency_slo_ms=3000)

        self.assertEqual(payload["request_count"], 8)
        self.assertEqual(payload["success_rate"], 0.875)
        self.assertEqual(payload["error_rate"], 0.125)
        self.assertEqual(payload["cache_hit_rate"], 0.25)
        self.assertEqual(payload["retry_rate"], 0.25)
        self.assertEqual(payload["fallback_rate"], 0.125)
        self.assertGreater(payload["total_cost_usd"], 0)
        self.assertEqual(payload["latency_ms"]["p50"], 1420)
        self.assertEqual(payload["latency_ms"]["p95"], 5200)
        self.assertEqual(payload["latency_ms"]["slo_violation_rate"], 0.375)
        self.assertEqual(payload["first_token_ms"]["p50"], 680)
        self.assertEqual(payload["first_token_ms"]["p95"], 1450)
        self.assertEqual(payload["by_route"]["/api/ask"]["request_count"], 6)
        self.assertEqual(payload["by_route"]["/api/ask"]["success_rate"], 0.8333)
        self.assertEqual(payload["by_route"]["/api/ask/stream"]["latency_p95_ms"], 3380)
        self.assertIn("latency_p95_above_slo", payload["alerts"])
        self.assertIn("/api/ask", payload["by_route"])

    def test_report_rejects_missing_model_pricing(self):
        records = load_records(ROOT / "data" / "observability" / "model_call_logs.json")

        with self.assertRaises(ValueError):
            build_report(records, {})

    def test_stable_cache_key_normalizes_question_spaces_and_versions(self):
        first = stable_cache_key("移动端  为什么不能保存 API Key？", "prompt-v1", "kb-v3", "tenant-a", "support-docs")
        second = stable_cache_key("移动端 为什么不能保存 API Key？", "prompt-v1", "kb-v3", "tenant-a", "support-docs")
        changed = stable_cache_key("移动端 为什么不能保存 API Key？", "prompt-v2", "kb-v3", "tenant-a", "support-docs")
        other_tenant = stable_cache_key("移动端 为什么不能保存 API Key？", "prompt-v1", "kb-v3", "tenant-b", "support-docs")
        other_scope = stable_cache_key("移动端 为什么不能保存 API Key？", "prompt-v1", "kb-v3", "tenant-a", "admin-docs")

        self.assertEqual(first, second)
        self.assertNotEqual(first, changed)
        self.assertNotEqual(first, other_tenant)
        self.assertNotEqual(first, other_scope)
        self.assertEqual(len(first), 32)

    def test_retry_schedule_and_status_classification(self):
        self.assertEqual(retry_schedule(4, base_ms=200, cap_ms=1000), [200, 400, 800, 1000])
        self.assertEqual(classify_status(200), "success")
        self.assertEqual(classify_status(429), "retry")
        self.assertEqual(classify_status(401), "fail_fast")
        self.assertEqual(classify_status(418), "manual_review")
        with self.assertRaises(ValueError):
            classify_status(9999)

    def test_loaders_reject_malformed_data(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            records_path = Path(temp_dir) / "logs.json"
            records_path.write_text('[{"request_id":"x"}]', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_records(records_path)

            pricing_path = Path(temp_dir) / "pricing.json"
            pricing_path.write_text('{"fast-chat":{"input_per_1k_usd":-1,"output_per_1k_usd":0.1}}', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_pricing(pricing_path)

            pricing_path.write_text('{"fast-chat":{"input_per_1k_usd":NaN,"output_per_1k_usd":0.1}}', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_pricing(pricing_path)

            records_path.write_text(
                json.dumps(
                    [
                        {
                            "request_id": "req_bad",
                            "route": "/api/ask",
                            "model": "fast-chat",
                            "prompt_tokens": 1,
                            "completion_tokens": 1,
                            "latency_ms": 10,
                            "first_token_ms": 5,
                            "status_code": 9999,
                            "cache_hit": False,
                            "retry_count": 0,
                            "fallback_used": False,
                        }
                    ]
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_records(records_path)

    def test_cli_outputs_json_report(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "ops_report.py"), "--latency-slo-ms", "3000"],
            check=True,
            capture_output=True,
            text=True,
        )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["request_count"], 8)
        self.assertIn("alerts", payload)

    def test_cli_reports_bad_pricing_without_traceback(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pricing_path = Path(temp_dir) / "pricing.json"
            pricing_path.write_text('{"fast-chat":{"input_per_1k_usd":Infinity,"output_per_1k_usd":0.1}}', encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "ops_report.py"),
                    "--pricing",
                    str(pricing_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("finite non-negative number", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_argument_validator(self):
        self.assertEqual(positive_int("3000"), 3000)
        with self.assertRaises(ArgumentTypeError):
            positive_int("0")

    def test_percentile_rejects_invalid_percentile(self):
        with self.assertRaises(ValueError):
            _percentile([1, 2, 3], 0)


if __name__ == "__main__":
    unittest.main()
