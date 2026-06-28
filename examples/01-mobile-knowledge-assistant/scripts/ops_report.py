from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from math import ceil, isfinite
from pathlib import Path
from statistics import mean


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ModelPricing:
    input_per_1k_usd: float
    output_per_1k_usd: float


@dataclass(frozen=True)
class ModelCallRecord:
    request_id: str
    route: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    first_token_ms: int
    status_code: int
    cache_hit: bool
    retry_count: int
    fallback_used: bool

    @property
    def success(self) -> bool:
        return 200 <= self.status_code < 300


def load_records(path: Path) -> list[ModelCallRecord]:
    """Load model gateway logs from JSON and fail fast on incomplete fields."""

    if not path.is_file():
        raise FileNotFoundError(f"model call log file not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid model call log JSON: {path}") from exc
    if not isinstance(payload, list) or not payload:
        raise ValueError("model call logs must be a non-empty JSON array")
    return [_load_record(item, index) for index, item in enumerate(payload, start=1)]


def load_pricing(path: Path) -> dict[str, ModelPricing]:
    """Load sample pricing.

    Real provider prices change over time, so the book keeps pricing in a data
    file instead of hard-coding vendor-specific numbers in the chapter text.
    """

    if not path.is_file():
        raise FileNotFoundError(f"pricing file not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid pricing JSON: {path}") from exc
    if not isinstance(payload, dict) or not payload:
        raise ValueError("pricing must be a non-empty JSON object")

    pricing: dict[str, ModelPricing] = {}
    for model, item in payload.items():
        if not isinstance(model, str) or not model.strip():
            raise ValueError("pricing model name must be a non-empty string")
        if not isinstance(item, dict):
            raise ValueError(f"pricing for model {model!r} must be an object")
        pricing[model] = ModelPricing(
            input_per_1k_usd=_required_non_negative_number(item, "input_per_1k_usd", f"pricing {model}"),
            output_per_1k_usd=_required_non_negative_number(item, "output_per_1k_usd", f"pricing {model}"),
        )
    return pricing


def build_report(
    records: list[ModelCallRecord],
    pricing: dict[str, ModelPricing],
    latency_slo_ms: int = 3000,
) -> dict:
    """Build a cost, latency, cache, retry, and fallback report for CI or dashboards."""

    if not records:
        raise ValueError("records must not be empty")
    if latency_slo_ms <= 0:
        raise ValueError("latency_slo_ms must be greater than 0")

    costs = [estimate_cost(record, pricing) for record in records]
    success_count = sum(1 for record in records if record.success)
    first_token_values = [record.first_token_ms for record in records if record.first_token_ms > 0]

    route_reports = {
        route: _route_report([record for record in records if record.route == route], pricing, latency_slo_ms)
        for route in sorted({record.route for record in records})
    }
    error_rate = _rate(len(records) - success_count, len(records))
    latency_p95 = _percentile([record.latency_ms for record in records], 95)

    return {
        "request_count": len(records),
        "success_rate": _rate(success_count, len(records)),
        "error_rate": error_rate,
        "cache_hit_rate": _rate(sum(1 for record in records if record.cache_hit), len(records)),
        "retry_rate": _rate(sum(1 for record in records if record.retry_count > 0), len(records)),
        "fallback_rate": _rate(sum(1 for record in records if record.fallback_used), len(records)),
        "total_cost_usd": round(sum(costs), 6),
        "latency_ms": {
            "avg": round(mean(record.latency_ms for record in records), 2),
            "p50": _percentile([record.latency_ms for record in records], 50),
            "p95": latency_p95,
            "slo_violation_rate": _rate(sum(1 for record in records if record.latency_ms > latency_slo_ms), len(records)),
        },
        "first_token_ms": {
            "p50": _percentile(first_token_values, 50),
            "p95": _percentile(first_token_values, 95),
        },
        "by_route": route_reports,
        "alerts": _alerts(error_rate, latency_p95, latency_slo_ms, records),
    }


def estimate_cost(record: ModelCallRecord, pricing: dict[str, ModelPricing]) -> float:
    if record.model not in pricing:
        raise ValueError(f"missing pricing for model: {record.model}")
    price = pricing[record.model]
    input_cost = record.prompt_tokens / 1000 * price.input_per_1k_usd
    output_cost = record.completion_tokens / 1000 * price.output_per_1k_usd
    return input_cost + output_cost


def stable_cache_key(
    question: str,
    prompt_version: str,
    kb_version: str,
    tenant_id: str,
    permission_scope: str,
    locale: str = "zh-CN",
) -> str:
    """Return a stable cache key without storing raw user text in the key name."""

    if not question.strip():
        raise ValueError("question must not be empty")
    payload = {
        "question": " ".join(question.split()),
        "prompt_version": prompt_version.strip(),
        "kb_version": kb_version.strip(),
        "tenant_id": tenant_id.strip(),
        "permission_scope": permission_scope.strip(),
        "locale": locale.strip(),
    }
    if not all(payload.values()):
        raise ValueError("prompt_version, kb_version, tenant_id, permission_scope, and locale must not be empty")
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def retry_schedule(max_retries: int, base_ms: int = 200, cap_ms: int = 3000) -> list[int]:
    """Return exponential backoff delays; production callers should add jitter."""

    if max_retries < 0:
        raise ValueError("max_retries must not be negative")
    if base_ms <= 0 or cap_ms <= 0:
        raise ValueError("base_ms and cap_ms must be positive")
    return [min(cap_ms, base_ms * 2**attempt) for attempt in range(max_retries)]


def classify_status(status_code: int) -> str:
    """Classify model gateway status codes before retrying blindly."""

    if not 100 <= status_code <= 599:
        raise ValueError("status_code must be a valid HTTP status code")
    if 200 <= status_code < 300:
        return "success"
    if status_code in {408, 425, 429, 500, 502, 503, 504}:
        return "retry"
    if status_code in {400, 401, 403, 404, 422}:
        return "fail_fast"
    return "manual_review"


def _route_report(records: list[ModelCallRecord], pricing: dict[str, ModelPricing], latency_slo_ms: int) -> dict:
    success_count = sum(1 for record in records if record.success)
    return {
        "request_count": len(records),
        "success_rate": _rate(success_count, len(records)),
        "cache_hit_rate": _rate(sum(1 for record in records if record.cache_hit), len(records)),
        "total_cost_usd": round(sum(estimate_cost(record, pricing) for record in records), 6),
        "latency_p95_ms": _percentile([record.latency_ms for record in records], 95),
        "slo_violation_rate": _rate(sum(1 for record in records if record.latency_ms > latency_slo_ms), len(records)),
    }


def _alerts(error_rate: float, latency_p95: int, latency_slo_ms: int, records: list[ModelCallRecord]) -> list[str]:
    alerts: list[str] = []
    if error_rate > 0.05:
        alerts.append("error_rate_above_5_percent")
    if latency_p95 > latency_slo_ms:
        alerts.append("latency_p95_above_slo")
    if any(record.fallback_used for record in records):
        alerts.append("fallback_used")
    return alerts


def _percentile(values: list[int], percentile: int) -> int:
    if not 0 < percentile <= 100:
        raise ValueError("percentile must be between 1 and 100")
    if not values:
        return 0
    ordered = sorted(values)
    index = max(0, ceil(len(ordered) * percentile / 100) - 1)
    return ordered[index]


def _rate(count: int, total: int) -> float:
    return round(count / total, 4) if total else 0.0


def _load_record(item: object, index: int) -> ModelCallRecord:
    if not isinstance(item, dict):
        raise ValueError(f"model call log #{index} must be an object")
    return ModelCallRecord(
        request_id=_required_str(item, "request_id", index),
        route=_required_str(item, "route", index),
        model=_required_str(item, "model", index),
        prompt_tokens=_required_non_negative_int(item, "prompt_tokens", index),
        completion_tokens=_required_non_negative_int(item, "completion_tokens", index),
        latency_ms=_required_positive_int(item, "latency_ms", index),
        first_token_ms=_required_non_negative_int(item, "first_token_ms", index),
        status_code=_required_http_status_code(item, "status_code", index),
        cache_hit=_required_bool(item, "cache_hit", index),
        retry_count=_required_non_negative_int(item, "retry_count", index),
        fallback_used=_required_bool(item, "fallback_used", index),
    )


def _required_str(item: dict, field: str, index: int) -> str:
    value = item.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"model call log #{index} field {field!r} must be a non-empty string")
    return value.strip()


def _required_bool(item: dict, field: str, index: int) -> bool:
    value = item.get(field)
    if not isinstance(value, bool):
        raise ValueError(f"model call log #{index} field {field!r} must be a boolean")
    return value


def _required_non_negative_int(item: dict, field: str, index: int) -> int:
    value = item.get(field)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"model call log #{index} field {field!r} must be a non-negative integer")
    return value


def _required_positive_int(item: dict, field: str, index: int) -> int:
    value = _required_non_negative_int(item, field, index)
    if value <= 0:
        raise ValueError(f"model call log #{index} field {field!r} must be a positive integer")
    return value


def _required_http_status_code(item: dict, field: str, index: int) -> int:
    value = _required_non_negative_int(item, field, index)
    if not 100 <= value <= 599:
        raise ValueError(f"model call log #{index} field {field!r} must be a valid HTTP status code")
    return value


def _required_non_negative_number(item: dict, field: str, context: str) -> float:
    value = item.get(field)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{context} field {field!r} must be a finite non-negative number")
    parsed = float(value)
    if not isfinite(parsed) or parsed < 0:
        raise ValueError(f"{context} field {field!r} must be a finite non-negative number")
    return parsed


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a model gateway cost, latency, and reliability report.")
    parser.add_argument("--logs", type=Path, default=PROJECT_ROOT / "data" / "observability" / "model_call_logs.json")
    parser.add_argument("--pricing", type=Path, default=PROJECT_ROOT / "data" / "observability" / "model_pricing.json")
    parser.add_argument("--latency-slo-ms", type=positive_int, default=3000)
    args = parser.parse_args()

    try:
        payload = build_report(load_records(args.logs), load_pricing(args.pricing), latency_slo_ms=args.latency_slo_ms)
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
