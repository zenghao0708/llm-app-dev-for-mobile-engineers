from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path


PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "email",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        "[EMAIL]",
    ),
    (
        "phone",
        re.compile(r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)"),
        "[PHONE]",
    ),
    (
        "id_card",
        re.compile(r"(?<![A-Za-z0-9])\d{17}[\dXx](?![A-Za-z0-9])"),
        "[ID_CARD]",
    ),
    (
        "uuid",
        re.compile(
            r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-"
            r"[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
        ),
        "[UUID]",
    ),
    (
        "ip_address",
        re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
        "[IP_ADDRESS]",
    ),
    (
        "model_api_key",
        re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
        "[MODEL_API_KEY]",
    ),
]

SECRET_ASSIGNMENT_RE = re.compile(
    r"(?P<name>\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|"
    r"token|authorization|session|cookie)\b)(?P<sep>\s*[:=]\s*)"
    r"(?P<value>.*?)(?=(?:\s+[A-Za-z_][A-Za-z0-9_-]*\s*[:=])|,|$)",
    re.IGNORECASE,
)
SECRET_HEADER_RE = re.compile(
    r"(?im)(?P<name>\b(?:authorization|cookie|set-cookie)\b)(?P<sep>\s*:\s*)(?P<value>[^\r\n]+)"
)
COOKIE_ASSIGNMENT_RE = re.compile(
    r"(?P<name>\bcookie\b)(?P<sep>\s*=\s*)(?P<value>[^\r\n,]+)",
    re.IGNORECASE,
)
SECRET_JSON_FIELD_RE = re.compile(
    r'(?P<prefix>"(?:api[_-]?key|access[_-]?token|refresh[_-]?token|'
    r'token|authorization|session|cookie|set-cookie)"\s*:\s*")'
    r'(?P<value>(?:\\.|[^"\\])*)'
    r'(?P<suffix>")',
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RedactionFinding:
    kind: str
    count: int


@dataclass(frozen=True)
class RedactionReport:
    redacted_text: str
    findings: list[RedactionFinding]


def redact_text(text: str) -> RedactionReport:
    """Redact common sensitive values before logs are sent to an LLM service.

    The report intentionally returns only finding counts, not the raw matched
    values. Logging the sensitive values in a "redaction report" would defeat
    the purpose of redaction.
    """

    counts: Counter[str] = Counter()

    def replace_secret(match: re.Match[str]) -> str:
        if match.group("value").strip() == "[SECRET]":
            return match.group(0)
        counts["secret_assignment"] += 1
        return f"{match.group('name')}{match.group('sep')}[SECRET]"

    def replace_secret_header(match: re.Match[str]) -> str:
        counts["secret_header"] += 1
        return f"{match.group('name')}{match.group('sep')}[SECRET]"

    def replace_secret_json_field(match: re.Match[str]) -> str:
        counts["secret_json_field"] += 1
        return f"{match.group('prefix')}[SECRET]{match.group('suffix')}"

    redacted = SECRET_HEADER_RE.sub(replace_secret_header, text)
    redacted = SECRET_JSON_FIELD_RE.sub(replace_secret_json_field, redacted)
    redacted = COOKIE_ASSIGNMENT_RE.sub(replace_secret, redacted)
    redacted = SECRET_ASSIGNMENT_RE.sub(replace_secret, redacted)

    for kind, pattern, replacement in PATTERNS:
        redacted, count = pattern.subn(replacement, redacted)
        if count:
            counts[kind] += count

    findings = [RedactionFinding(kind=kind, count=count) for kind, count in sorted(counts.items())]
    return RedactionReport(redacted_text=redacted, findings=findings)


def read_input(text: str | None, file_path: Path | None) -> str:
    if text is not None and file_path is not None:
        raise ValueError("use either --text or --file, not both")
    if text is not None:
        return text
    if file_path is not None:
        return file_path.read_text(encoding="utf-8")
    raise ValueError("either --text or --file is required")


def report_payload(report: RedactionReport) -> dict:
    return {
        "redacted_text": report.redacted_text,
        "findings": [asdict(item) for item in report.findings],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Redact sensitive values before sending text to an LLM service.")
    parser.add_argument("--text", help="Text to redact. Do not use this for large production logs.")
    parser.add_argument("--file", type=Path, help="UTF-8 text file to redact.")
    args = parser.parse_args()

    try:
        source = read_input(args.text, args.file)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    print(json.dumps(report_payload(redact_text(source)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
