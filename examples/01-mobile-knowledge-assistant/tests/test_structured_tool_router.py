import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from structured_tool_router import (
    TOOL_CALL_SCHEMA,
    ToolCall,
    dispatch_tool_call,
    load_orders,
    run_structured_tool_flow,
    validate_json_schema,
)


class StructuredToolRouterTest(unittest.TestCase):
    def test_query_order_runs_read_only_tool_for_owner(self):
        payload = run_structured_tool_flow("帮我查一下订单 A1024 到哪里了", "user_001")

        self.assertTrue(payload["schema_valid"])
        self.assertEqual(payload["model_output"]["tool_name"], "query_order")
        self.assertEqual(payload["tool_result"]["status"], "success")
        self.assertEqual(payload["tool_result"]["payload"]["order_id"], "A1024")
        self.assertEqual(payload["audit"]["executed"], True)
        self.assertEqual(payload["audit"]["server_requires_confirmation"], False)

    def test_forbids_cross_user_order_access(self):
        payload = run_structured_tool_flow("帮我查一下订单 B2048", "user_001")

        self.assertEqual(payload["tool_result"]["status"], "forbidden")
        self.assertEqual(payload["audit"]["executed"], False)

    def test_cancellation_requires_mobile_confirmation(self):
        payload = run_structured_tool_flow("我要取消订单 P3001", "user_001")

        self.assertEqual(payload["model_output"]["tool_name"], "request_order_cancellation")
        self.assertEqual(payload["tool_result"]["status"], "confirmation_required")
        self.assertEqual(payload["tool_result"]["mobile_confirmation"]["risk_level"], "high")
        self.assertEqual(payload["audit"]["executed"], False)
        self.assertEqual(payload["audit"]["server_requires_confirmation"], True)

    def test_cancellation_forbidden_before_confirmation(self):
        payload = run_structured_tool_flow("我要取消订单 B2048", "user_001")

        self.assertEqual(payload["tool_result"]["status"], "forbidden")
        self.assertNotIn("mobile_confirmation", payload["tool_result"])
        self.assertEqual(payload["audit"]["executed"], False)

    def test_confirmed_cancellation_submits_request_without_writing_file(self):
        payload = run_structured_tool_flow("我要取消订单 P3001", "user_001", confirmed=True)

        self.assertEqual(payload["tool_result"]["status"], "cancellation_requested")
        self.assertEqual(payload["tool_result"]["payload"]["next_state"], "cancel_requested")
        self.assertEqual(payload["audit"]["executed"], True)

    def test_shipped_order_cannot_be_cancelled_even_after_confirmation(self):
        payload = run_structured_tool_flow("取消订单 A1024", "user_001", confirmed=True)

        self.assertEqual(payload["tool_result"]["status"], "not_cancellable")
        self.assertEqual(payload["audit"]["executed"], False)

    def test_non_cancellable_order_does_not_request_confirmation(self):
        payload = run_structured_tool_flow("取消订单 A1024", "user_001")

        self.assertEqual(payload["tool_result"]["status"], "not_cancellable")
        self.assertNotIn("mobile_confirmation", payload["tool_result"])
        self.assertEqual(payload["audit"]["executed"], False)

    def test_missing_order_returns_not_found_before_confirmation(self):
        payload = run_structured_tool_flow("取消订单 Z9999", "user_001")

        self.assertEqual(payload["tool_result"]["status"], "not_found")
        self.assertNotIn("mobile_confirmation", payload["tool_result"])
        self.assertEqual(payload["audit"]["executed"], False)

    def test_missing_order_id_returns_invalid_arguments_before_confirmation(self):
        payload = run_structured_tool_flow("我要取消订单", "user_001")

        self.assertEqual(payload["tool_result"]["status"], "invalid_arguments")
        self.assertIn("order_id", payload["tool_result"]["message"])
        self.assertEqual(payload["audit"]["executed"], False)

    def test_server_policy_overrides_model_confirmation_flag(self):
        orders = load_orders(ROOT / "data" / "tools" / "orders.json")
        result = dispatch_tool_call(
            ToolCall(
                name="request_order_cancellation",
                arguments={"order_id": "P3001"},
                requires_confirmation=False,
            ),
            orders,
            user_id="user_001",
        )

        self.assertEqual(result["status"], "confirmation_required")
        self.assertEqual(result["mobile_confirmation"]["risk_level"], "high")

    def test_invalid_order_id_format_is_rejected_by_dispatcher(self):
        orders = load_orders(ROOT / "data" / "tools" / "orders.json")
        result = dispatch_tool_call(
            ToolCall(
                name="query_order",
                arguments={"order_id": "order-1024"},
                requires_confirmation=False,
            ),
            orders,
            user_id="user_001",
        )

        self.assertEqual(result["status"], "invalid_arguments")
        self.assertIn("A1024", result["message"])

    def test_schema_rejects_extra_fields_and_invalid_enum(self):
        valid_payload = {
            "tool_name": "query_order",
            "arguments": {"order_id": "A1024"},
            "requires_confirmation": False,
        }
        validate_json_schema(valid_payload, TOOL_CALL_SCHEMA)

        invalid_payload = dict(valid_payload)
        invalid_payload["extra"] = "not allowed"
        with self.assertRaises(ValueError):
            validate_json_schema(invalid_payload, TOOL_CALL_SCHEMA)

        invalid_payload = dict(valid_payload)
        invalid_payload["mobile_confirmation"] = {
            "title": "确认取消订单",
            "message": "模型不应决定确认卡",
            "risk_level": "low",
        }
        with self.assertRaises(ValueError):
            validate_json_schema(invalid_payload, TOOL_CALL_SCHEMA)

        invalid_payload = dict(valid_payload)
        invalid_payload["tool_name"] = "delete_order"
        with self.assertRaises(ValueError):
            validate_json_schema(invalid_payload, TOOL_CALL_SCHEMA)

    def test_tool_registry_rejects_unknown_tools(self):
        orders = load_orders(ROOT / "data" / "tools" / "orders.json")

        with self.assertRaises(ValueError):
            dispatch_tool_call(
                ToolCall(
                    name="delete_order",
                    arguments={"order_id": "A1024"},
                    requires_confirmation=True,
                ),
                orders,
                user_id="user_001",
            )

    def test_load_orders_rejects_bad_data(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "orders.json"
            path.write_text('[{"order_id":"A1024"}]', encoding="utf-8")

            with self.assertRaises(ValueError):
                load_orders(path)

    def test_cli_outputs_structured_payload(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "structured_tool_router.py"),
                "--message",
                "帮我查一下订单 A1024",
                "--user-id",
                "user_001",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["tool_result"]["status"], "success")
        self.assertEqual(payload["model_output"]["arguments"]["order_id"], "A1024")

    def test_cli_reports_invalid_message_without_traceback(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "structured_tool_router.py"),
                "--message",
                " ",
                "--user-id",
                "user_001",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("message must not be empty", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
