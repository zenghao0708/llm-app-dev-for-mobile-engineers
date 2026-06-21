from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mobile_llm.config import Settings, load_settings
from mobile_llm.providers import MockLLMProvider
from mobile_llm.retriever import LocalRetriever
from mobile_llm.service import KnowledgeAssistant


MIN_PYTHON = (3, 10)
DEFAULT_QUESTION = "移动端为什么不能直接保存模型 API 密钥？"
MODEL_KEY_RE = re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b")
GOOGLE_KEY_RE = re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b")
GITHUB_TOKEN_RE = re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[0-9A-Za-z]{20,}\b")
GITHUB_PAT_RE = re.compile(r"\bgithub_pat_[0-9A-Za-z_]{20,}\b")
SLACK_TOKEN_RE = re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b")
SENSITIVE_QUERY_RE = re.compile(r"(?i)(api[_-]?key|access[_-]?token|token|secret|signature|sig)=")
PLACEHOLDER_API_KEYS = {
    "",
    "replace-with-your-api-key",
    "your-api-key",
    "your-api-key-here",
    "<your-api-key>",
    "example-api-key",
}


def run_checks(question: str = DEFAULT_QUESTION, docs_dir: Path | None = None) -> dict:
    settings, settings_error = _load_settings_safely()
    resolved_docs_dir = docs_dir or (settings.docs_dir if settings else PROJECT_ROOT / "data" / "documents")

    checks = [
        _check_python_version(),
        _check_file_exists("requirements_file", PROJECT_ROOT / "requirements.txt"),
        _check_env_example(PROJECT_ROOT / ".env.example"),
        _check_gitignore(PROJECT_ROOT.parent.parent / ".gitignore"),
        _check_settings_loaded(settings_error),
        _check_docs_dir(resolved_docs_dir),
    ]

    smoke_payload = _run_mock_assistant_smoke(question, resolved_docs_dir)
    checks.append(smoke_payload["check"])

    return {
        "passed": all(item["passed"] for item in checks),
        "project_root": str(PROJECT_ROOT),
        "settings": _safe_settings(settings),
        "checks": checks,
        "sample": smoke_payload["sample"],
    }


def _load_settings_safely() -> tuple[Settings | None, str]:
    try:
        return load_settings(), ""
    except Exception as exc:
        return None, str(exc)


def _safe_settings(settings: Settings | None) -> dict:
    if settings is None:
        return {}
    return {
        "host": settings.host,
        "port": settings.port,
        "provider": settings.provider,
        "api_url": _safe_url(settings.api_url),
        "api_key_set": bool(settings.api_key),
        "model": settings.model,
        "docs_dir": str(settings.docs_dir),
    }


def _safe_url(url: str) -> str:
    """Remove credentials and request parameters before printing config."""
    parts = urlsplit(url)
    host = parts.hostname or ""
    if not parts.scheme or not host:
        return "[configured]" if url else ""
    try:
        port = f":{parts.port}" if parts.port else ""
    except ValueError:
        port = ""
    return urlunsplit((parts.scheme, f"{host}{port}", parts.path, "", ""))


def _check_python_version() -> dict:
    current = sys.version_info[:3]
    return _check(
        "python_version",
        current >= MIN_PYTHON,
        {
            "current": ".".join(str(item) for item in current),
            "minimum": ".".join(str(item) for item in MIN_PYTHON),
        },
    )


def _check_file_exists(name: str, path: Path) -> dict:
    return _check(name, path.is_file(), {"path": str(path)})


def _check_env_example(path: Path) -> dict:
    if not path.is_file():
        return _check("env_example", False, {"path": str(path), "error": "missing"})
    values = _parse_env_file(path.read_text(encoding="utf-8"))
    required_keys = ("LLM_PROVIDER", "LLM_API_URL", "LLM_API_KEY", "LLM_MODEL")
    has_required_keys = all(key in values for key in required_keys)
    api_key_is_placeholder = _is_placeholder_api_key(values.get("LLM_API_KEY", ""))
    secret_like_keys = _secret_like_env_keys(values)
    return _check(
        "env_example",
        has_required_keys and api_key_is_placeholder and not secret_like_keys,
        {
            "path": str(path),
            "has_required_keys": has_required_keys,
            "api_key_is_placeholder": api_key_is_placeholder,
            "secret_like_keys": secret_like_keys,
        },
    )


def _parse_env_file(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def _is_placeholder_api_key(value: str) -> bool:
    return value.strip().strip("'\"").lower() in PLACEHOLDER_API_KEYS


def _secret_like_env_keys(values: dict[str, str]) -> list[str]:
    flagged: list[str] = []
    for key, value in values.items():
        normalized = value.strip().strip("'\"")
        if not normalized:
            continue
        if key == "LLM_API_KEY":
            if not _is_placeholder_api_key(normalized):
                flagged.append(key)
            continue
        if _looks_secret_like(normalized):
            flagged.append(key)
    return sorted(set(flagged))


def _looks_secret_like(value: str) -> bool:
    return any(
        pattern.search(value)
        for pattern in (
            MODEL_KEY_RE,
            GOOGLE_KEY_RE,
            GITHUB_TOKEN_RE,
            GITHUB_PAT_RE,
            SLACK_TOKEN_RE,
            SENSITIVE_QUERY_RE,
        )
    )


def _check_gitignore(path: Path) -> dict:
    if not path.is_file():
        return _check("gitignore_env_rule", False, {"path": str(path), "error": "missing"})
    lines = {line.strip() for line in path.read_text(encoding="utf-8").splitlines()}
    return _check(
        "gitignore_env_rule",
        ".env" in lines and ".env.*" in lines and "!.env.example" in lines,
        {"path": str(path)},
    )


def _check_settings_loaded(error: str) -> dict:
    return _check("settings_loaded", not error, {"error": error} if error else None)


def _check_docs_dir(path: Path) -> dict:
    markdown_count = len(list(path.glob("*.md"))) if path.is_dir() else 0
    return _check("docs_dir", path.is_dir() and markdown_count > 0, {"path": str(path), "markdown_count": markdown_count})


def _run_mock_assistant_smoke(question: str, docs_dir: Path) -> dict:
    if not docs_dir.is_dir() or not any(docs_dir.glob("*.md")):
        return {
            "check": _check("mock_assistant_smoke", False, {"error": "docs_dir is not ready"}),
            "sample": {},
        }

    # This uses the deterministic mock provider so the environment check never
    # spends tokens or requires a real model key.
    assistant = KnowledgeAssistant(LocalRetriever.from_directory(docs_dir), MockLLMProvider())
    result = assistant.answer(question)
    citations = result.get("citations", [])
    return {
        "check": _check(
            "mock_assistant_smoke",
            bool(result.get("answer")) and bool(citations),
            {"citations_count": len(citations)},
        ),
        "sample": {
            "question": question,
            "answer_preview": _preview(result.get("answer", "")),
            "first_citation": _first_citation(citations),
        },
    }


def _first_citation(citations: list[dict]) -> dict:
    if not citations:
        return {}
    citation = dict(citations[0])
    citation["text"] = _preview(citation.get("text", ""))
    return citation


def _preview(text: str, max_chars: int = 96) -> str:
    compact = " ".join(str(text).split())
    if len(compact) <= max_chars:
        return compact
    return compact[:max_chars].rstrip() + "..."


def _check(name: str, passed: bool, details: dict | None = None) -> dict:
    payload = {"name": name, "passed": bool(passed)}
    if details:
        payload["details"] = details
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Check the local development environment for the mobile LLM example.")
    parser.add_argument("--question", default=DEFAULT_QUESTION)
    parser.add_argument("--docs-dir", type=Path)
    args = parser.parse_args()

    payload = run_checks(question=args.question, docs_dir=args.docs_dir)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if not payload["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
