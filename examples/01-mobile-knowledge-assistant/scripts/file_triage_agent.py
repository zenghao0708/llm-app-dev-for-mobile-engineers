from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_KEYWORDS = ("API Key", "流式输出", "权限", "脱敏", "引用")


@dataclass(frozen=True)
class ToolCall:
    name: str
    args: dict[str, str]


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    payload: object
    error: str | None = None


class SafeFileTools:
    """Read-only tools exposed to the agent loop.

    The path checks are part of the lesson: an agent may choose tools, but code
    still enforces what files can be listed or read.
    """

    def __init__(self, docs_dir: Path):
        self.docs_dir = docs_dir.resolve()

    def list_markdown_files(self) -> list[str]:
        _validate_docs_dir(self.docs_dir)
        return [path.name for path in sorted(self.docs_dir.glob("*.md"))]

    def read_markdown_file(self, filename: str) -> str:
        if Path(filename).name != filename:
            raise ValueError(f"nested paths are not allowed: {filename}")
        path = (self.docs_dir / filename).resolve()
        if self.docs_dir != path.parent:
            raise ValueError(f"file is outside docs_dir: {filename}")
        if path.suffix != ".md":
            raise ValueError(f"only Markdown files are allowed: {filename}")
        if not path.is_file():
            raise FileNotFoundError(f"document not found: {filename}")
        return path.read_text(encoding="utf-8")


class ToolRegistry:
    """Small whitelist dispatcher for tool calls planned by the agent."""

    def __init__(self, tools: SafeFileTools):
        self._tools = {
            "list_markdown_files": lambda _args: tools.list_markdown_files(),
            "read_markdown_file": lambda args: tools.read_markdown_file(_required_arg(args, "filename")),
        }

    def call(self, call: ToolCall) -> ToolResult:
        if call.name not in self._tools:
            raise ValueError(f"tool is not allowed: {call.name}")
        try:
            return ToolResult(ok=True, payload=self._tools[call.name](call.args))
        except (FileNotFoundError, ValueError) as exc:
            return ToolResult(ok=False, payload=None, error=str(exc))


def run_agent(goal: str, docs_dir: Path, keywords: list[str] | None = None, max_steps: int = 8) -> dict:
    """Run a deterministic read-only agent over local Markdown documents.

    A production agent would usually let a model choose the next tool call. This
    script keeps the planner deterministic so readers can inspect every
    Observe/Plan/Act/Tool Result/Reflect step without needing an API key.
    """

    if not goal.strip():
        raise ValueError("goal must not be empty")
    if max_steps <= 0:
        raise ValueError("max_steps must be greater than 0")

    _validate_docs_dir(docs_dir)
    selected_keywords = _normalize_keywords(keywords)
    registry = ToolRegistry(SafeFileTools(docs_dir))
    state = {
        "files": [],
        "read_files": set(),
        "documents": [],
        "trace": [],
    }

    for step in range(1, max_steps + 1):
        call = _plan_next_action(state)
        if call is None:
            return _build_report("complete", goal, selected_keywords, state, stop_reason="all_documents_read")

        result = registry.call(call)
        state["trace"].append(_trace_entry(step, state, call, result))
        if not result.ok:
            return _build_report("failed", goal, selected_keywords, state, stop_reason=result.error or "tool_failed")

        _apply_tool_result(state, call, result, selected_keywords)
        if state["files"] and len(state["read_files"]) == len(state["files"]):
            return _build_report("complete", goal, selected_keywords, state, stop_reason="all_documents_read")

    return _build_report("stopped", goal, selected_keywords, state, stop_reason="max_steps_exceeded")


def _plan_next_action(state: dict) -> ToolCall | None:
    files: list[str] = state["files"]
    read_files: set[str] = state["read_files"]
    if not files:
        return ToolCall("list_markdown_files", {})
    for filename in files:
        if filename not in read_files:
            return ToolCall("read_markdown_file", {"filename": filename})
    return None


def _apply_tool_result(state: dict, call: ToolCall, result: ToolResult, keywords: list[str]) -> None:
    if call.name == "list_markdown_files":
        state["files"] = list(result.payload)
        return
    if call.name == "read_markdown_file":
        filename = call.args["filename"]
        state["read_files"].add(filename)
        state["documents"].append(_analyze_document(filename, str(result.payload), keywords))


def _analyze_document(filename: str, text: str, keywords: list[str]) -> dict:
    headings = _extract_headings(text)
    hits = {keyword: _keyword_count(text, keyword) for keyword in keywords}
    snippets = {
        keyword: _first_matching_line(text, keyword)
        for keyword, count in hits.items()
        if count > 0
    }
    return {
        "source": filename,
        "headings": headings,
        "keyword_hits": hits,
        "matched_keywords": [keyword for keyword, count in hits.items() if count > 0],
        "snippets": snippets,
        "score": sum(hits.values()),
    }


def _build_report(status: str, goal: str, keywords: list[str], state: dict, stop_reason: str) -> dict:
    documents: list[dict] = state["documents"]
    coverage = {
        keyword: [doc["source"] for doc in documents if doc["keyword_hits"].get(keyword, 0) > 0]
        for keyword in keywords
    }
    missing_keywords = [keyword for keyword, sources in coverage.items() if not sources]
    return {
        "goal": goal,
        "status": status,
        "stop_reason": stop_reason,
        "keywords": keywords,
        "document_count": len(documents),
        "coverage": coverage,
        "missing_keywords": missing_keywords,
        "documents": sorted(documents, key=lambda item: item["score"], reverse=True),
        "next_actions": _next_actions(missing_keywords),
        "trace": state["trace"],
    }


def _trace_entry(step: int, state: dict, call: ToolCall, result: ToolResult) -> dict:
    return {
        "step": step,
        "observe": _observation(state),
        "plan": _plan_text(call),
        "act": {"tool": call.name, "args": call.args},
        "reflect": _result_summary(result),
    }


def _observation(state: dict) -> str:
    files = state["files"]
    if not files:
        return "No files have been listed yet."
    return f"{len(state['read_files'])}/{len(files)} files have been read."


def _plan_text(call: ToolCall) -> str:
    if call.name == "list_markdown_files":
        return "List candidate Markdown documents before reading content."
    return f"Read {call.args['filename']} and extract headings plus keyword coverage."


def _result_summary(result: ToolResult) -> dict:
    if not result.ok:
        return {"ok": False, "error": result.error}
    if isinstance(result.payload, list):
        return {"ok": True, "items": len(result.payload)}
    return {"ok": True, "chars": len(str(result.payload))}


def _next_actions(missing_keywords: list[str]) -> list[str]:
    if not missing_keywords:
        return ["All requested keywords were found; ask a reviewer to inspect whether the matches answer the goal."]
    return [
        "Add or update documents for missing keywords: " + ", ".join(missing_keywords),
        "Re-run the agent after the knowledge base changes.",
    ]


def _extract_headings(text: str) -> list[str]:
    headings = []
    for line in text.splitlines():
        if line.startswith("#"):
            headings.append(line.lstrip("#").strip())
    return headings


def _keyword_count(text: str, keyword: str) -> int:
    return text.lower().count(keyword.lower())


def _first_matching_line(text: str, keyword: str, max_chars: int = 120) -> str:
    keyword_lower = keyword.lower()
    for line in text.splitlines():
        compact = " ".join(line.split())
        if keyword_lower in compact.lower():
            if len(compact) <= max_chars:
                return compact
            return compact[:max_chars].rstrip() + "..."
    return ""


def _normalize_keywords(keywords: list[str] | None) -> list[str]:
    values = keywords or list(DEFAULT_KEYWORDS)
    normalized = []
    for keyword in values:
        keyword = keyword.strip()
        if keyword and keyword not in normalized:
            normalized.append(keyword)
    if not normalized:
        raise ValueError("at least one keyword is required")
    return normalized


def _required_arg(args: dict[str, str], name: str) -> str:
    value = args.get(name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"missing tool argument: {name}")
    return value


def _validate_docs_dir(docs_dir: Path) -> None:
    if not docs_dir.is_dir():
        raise FileNotFoundError(f"docs_dir not found: {docs_dir}")
    if not any(docs_dir.glob("*.md")):
        raise ValueError(f"docs_dir has no Markdown files: {docs_dir}")


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a read-only file triage agent over local Markdown documents.")
    parser.add_argument("--goal", required=True)
    parser.add_argument("--docs-dir", type=Path, default=PROJECT_ROOT / "data" / "documents")
    parser.add_argument("--keyword", action="append", dest="keywords")
    parser.add_argument("--max-steps", type=positive_int, default=8)
    args = parser.parse_args()

    try:
        report = run_agent(args.goal, args.docs_dir, keywords=args.keywords, max_steps=args.max_steps)
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
