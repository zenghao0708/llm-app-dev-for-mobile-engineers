from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ORDERS = PROJECT_ROOT / "data" / "tools" / "orders.json"
ORDER_ID_PATTERN = re.compile(r"\b[A-Z]\d{4}\b")


TOOL_CALL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["tool_name", "arguments", "requires_confirmation"],
    "additionalProperties": False,
    "properties": {
        "tool_name": {
            "type": "string",
            "enum": ["query_order", "request_order_cancellation"],
        },
        "arguments": {
            "type": "object",
            "required": ["order_id"],
            "additionalProperties": False,
            "properties": {
                "order_id": {"type": "string"},
                "reason": {"type": "string"},
            },
        },
        "requires_confirmation": {"type": "boolean"},
    },
}

TOOL_POLICIES: dict[str, dict[str, Any]] = {
    "query_order": {"requires_confirmation": False, "risk_level": "none"},
    "request_order_cancellation": {"requires_confirmation": True, "risk_level": "high"},
}


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, str]
    requires_confirmation: bool


def run_structured_tool_flow(
    message: str,
    user_id: str,
    orders_path: Path = DEFAULT_ORDERS,
    confirmed: bool = False,
) -> dict:
    """Run a structured-output and tool-call flow for a mobile order assistant."""

    if not message.strip():
        raise ValueError("message must not be empty")
    if not user_id.strip():
        raise ValueError("user_id must not be empty")

    orders = load_orders(orders_path)
    # In production this payload would come from a model with response_format or
    # tool calling enabled. The deterministic adapter keeps the example runnable
    # without an API key while preserving the same validation boundary.
    model_output = mock_model_structured_output(message)
    validate_json_schema(model_output, TOOL_CALL_SCHEMA)
    call = tool_call_from_model_output(model_output)
    tool_result = dispatch_tool_call(call, orders, user_id=user_id.strip(), confirmed=confirmed)

    return {
        "user_id": user_id.strip(),
        "message": message,
        "model_output": model_output,
        "schema_valid": True,
        "tool_result": tool_result,
        "audit": {
            "tool_name": call.name,
            "model_requires_confirmation": call.requires_confirmation,
            "server_requires_confirmation": _requires_confirmation(call.name),
            "confirmed": confirmed,
            "executed": tool_result["status"] in {"success", "cancellation_requested"},
        },
    }


def mock_model_structured_output(message: str) -> dict:
    """Build a deterministic stand-in for a model's structured JSON output."""

    order_id = _extract_order_id(message)
    wants_cancel = any(keyword in message for keyword in ("取消", "退款", "不要了", "退掉"))
    if wants_cancel:
        return {
            "tool_name": "request_order_cancellation",
            "arguments": {
                "order_id": order_id,
                "reason": "用户在移动端会话中请求取消订单",
            },
            "requires_confirmation": True,
        }

    return {
        "tool_name": "query_order",
        "arguments": {"order_id": order_id},
        "requires_confirmation": False,
    }


def validate_json_schema(value: Any, schema: dict[str, Any], path: str = "$") -> None:
    """Validate the small JSON Schema subset used in this chapter."""

    expected_type = schema.get("type")
    if expected_type == "object":
        if not isinstance(value, dict):
            raise ValueError(f"{path} must be an object")
        required = schema.get("required", [])
        for field in required:
            if field not in value:
                raise ValueError(f"{path}.{field} is required")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extra = sorted(set(value) - set(properties))
            if extra:
                raise ValueError(f"{path} has unexpected fields: {', '.join(extra)}")
        for field, child_schema in properties.items():
            if field in value:
                validate_json_schema(value[field], child_schema, f"{path}.{field}")
        return

    if expected_type == "string":
        if not isinstance(value, str):
            raise ValueError(f"{path} must be a string")
    elif expected_type == "boolean":
        if not isinstance(value, bool):
            raise ValueError(f"{path} must be a boolean")
    else:
        raise ValueError(f"unsupported schema type at {path}: {expected_type}")

    enum = schema.get("enum")
    if enum is not None and value not in enum:
        raise ValueError(f"{path} must be one of: {', '.join(map(str, enum))}")


def tool_call_from_model_output(model_output: dict) -> ToolCall:
    return ToolCall(
        name=model_output["tool_name"],
        arguments={key: str(value) for key, value in model_output["arguments"].items()},
        requires_confirmation=bool(model_output["requires_confirmation"]),
    )


def dispatch_tool_call(call: ToolCall, orders: dict[str, dict], user_id: str, confirmed: bool = False) -> dict:
    """Dispatch a validated tool call through a server-side whitelist."""

    if call.name not in TOOL_POLICIES:
        raise ValueError(f"tool is not allowed: {call.name}")

    try:
        order_id = _required_argument(call, "order_id")
    except ValueError as exc:
        return {"ok": False, "status": "invalid_arguments", "message": str(exc)}

    if call.name == "query_order":
        return query_order(orders, user_id, order_id)

    preflight = _preflight_order_cancellation(orders, user_id, order_id)
    if not preflight["ok"]:
        return preflight
    if _requires_confirmation(call.name) and not confirmed:
        return {
            "ok": False,
            "status": "confirmation_required",
            "mobile_confirmation": _build_mobile_confirmation(call.name, order_id),
        }
    return request_order_cancellation(orders, user_id, order_id, confirmed=confirmed)


def query_order(orders: dict[str, dict], user_id: str, order_id: str) -> dict:
    order = _find_owned_order(orders, user_id, order_id)
    if not order["ok"]:
        return order
    payload = order["payload"]
    return {
        "ok": True,
        "status": "success",
        "payload": {
            "order_id": payload["order_id"],
            "status": payload["status"],
            "carrier": payload["carrier"],
            "eta": payload["eta"],
            "total_cny": payload["total_cny"],
        },
    }


def request_order_cancellation(orders: dict[str, dict], user_id: str, order_id: str, confirmed: bool) -> dict:
    order = _find_owned_order(orders, user_id, order_id)
    if not order["ok"]:
        return order
    payload = order["payload"]
    if not payload["cancellable"]:
        return {
            "ok": False,
            "status": "not_cancellable",
            "message": "订单当前状态不允许自动取消，请转人工处理。",
        }
    if not confirmed:
        return {
            "ok": False,
            "status": "confirmation_required",
            "message": "取消订单属于高风险动作，需要用户确认。",
        }
    return {
        "ok": True,
        "status": "cancellation_requested",
        "payload": {
            "order_id": payload["order_id"],
            "next_state": "cancel_requested",
            "message": "已提交取消申请，等待业务系统处理。",
        },
    }


def _preflight_order_cancellation(orders: dict[str, dict], user_id: str, order_id: str) -> dict:
    order = _find_owned_order(orders, user_id, order_id)
    if not order["ok"]:
        return order
    if not order["payload"]["cancellable"]:
        return {
            "ok": False,
            "status": "not_cancellable",
            "message": "订单当前状态不允许自动取消，请转人工处理。",
        }
    return order


def _requires_confirmation(tool_name: str) -> bool:
    policy = TOOL_POLICIES.get(tool_name)
    return bool(policy and policy["requires_confirmation"])


def _build_mobile_confirmation(tool_name: str, order_id: str) -> dict[str, str]:
    if tool_name == "request_order_cancellation":
        return {
            "title": "确认取消订单",
            "message": f"取消订单 {order_id}，可能影响发货或退款，请用户确认后再执行。",
            "risk_level": TOOL_POLICIES[tool_name]["risk_level"],
        }
    raise ValueError(f"tool does not define a confirmation card: {tool_name}")


def load_orders(path: Path) -> dict[str, dict]:
    if not path.is_file():
        raise FileNotFoundError(f"orders file not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid orders JSON: {path}") from exc
    if not isinstance(payload, list) or not payload:
        raise ValueError("orders must be a non-empty JSON array")

    orders: dict[str, dict] = {}
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"order #{index} must be an object")
        order_id = _required_str(item, "order_id", index)
        if order_id in orders:
            raise ValueError(f"duplicate order_id: {order_id}")
        orders[order_id] = {
            "order_id": order_id,
            "user_id": _required_str(item, "user_id", index),
            "status": _required_str(item, "status", index),
            "carrier": _optional_str(item, "carrier"),
            "eta": _optional_str(item, "eta"),
            "total_cny": _required_non_negative_number(item, "total_cny", index),
            "cancellable": _required_bool(item, "cancellable", index),
        }
    return orders


def _find_owned_order(orders: dict[str, dict], user_id: str, order_id: str) -> dict:
    if not order_id.strip():
        return {"ok": False, "status": "invalid_arguments", "message": "order_id must not be empty"}
    order = orders.get(order_id)
    if order is None:
        return {"ok": False, "status": "not_found", "message": "订单不存在"}
    if order["user_id"] != user_id:
        return {"ok": False, "status": "forbidden", "message": "当前用户无权访问该订单"}
    return {"ok": True, "status": "owned", "payload": order}


def _extract_order_id(message: str) -> str:
    match = ORDER_ID_PATTERN.search(message.upper())
    return match.group(0) if match else ""


def _required_argument(call: ToolCall, name: str) -> str:
    value = call.arguments.get(name, "")
    if not value.strip():
        raise ValueError(f"tool argument {name!r} must not be empty")
    normalized = value.strip().upper() if name == "order_id" else value.strip()
    if name == "order_id" and ORDER_ID_PATTERN.fullmatch(normalized) is None:
        raise ValueError("tool argument 'order_id' must match the format A1024")
    return normalized


def _required_str(item: dict, field: str, index: int) -> str:
    value = item.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"order #{index} field {field!r} must be a non-empty string")
    return value.strip()


def _optional_str(item: dict, field: str) -> str:
    value = item.get(field, "")
    if not isinstance(value, str):
        raise ValueError(f"field {field!r} must be a string")
    return value.strip()


def _required_bool(item: dict, field: str, index: int) -> bool:
    value = item.get(field)
    if not isinstance(value, bool):
        raise ValueError(f"order #{index} field {field!r} must be a boolean")
    return value


def _required_non_negative_number(item: dict, field: str, index: int) -> float:
    value = item.get(field)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        raise ValueError(f"order #{index} field {field!r} must be a non-negative number")
    return float(value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a structured-output tool call for a mobile order assistant.")
    parser.add_argument("--message", required=True)
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--orders", type=Path, default=DEFAULT_ORDERS)
    parser.add_argument("--confirm", action="store_true", help="Confirm high-risk tool calls such as cancellation.")
    args = parser.parse_args()

    try:
        payload = run_structured_tool_flow(
            args.message,
            args.user_id,
            orders_path=args.orders,
            confirmed=args.confirm,
        )
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
