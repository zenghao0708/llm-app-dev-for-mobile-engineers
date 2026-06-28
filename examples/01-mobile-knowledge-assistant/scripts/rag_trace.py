from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mobile_llm.prompts import build_rag_messages
from mobile_llm.providers import MockLLMProvider
from mobile_llm.retriever import LocalRetriever, SearchResult


def build_trace(question: str, docs_dir: Path, top_k: int = 3) -> dict:
    if top_k <= 0:
        raise ValueError("top_k must be greater than 0")

    _validate_docs_dir(docs_dir)
    retriever = LocalRetriever.from_directory(docs_dir)
    contexts = retriever.search(question, top_k=top_k)
    messages = build_rag_messages(question, contexts)
    answer = MockLLMProvider().generate(messages, contexts, question)

    return {
        "question": question,
        "retrieved_contexts": [_context_payload(item) for item in contexts],
        "prompt_messages": messages,
        "answer": answer,
    }


def _context_payload(item: SearchResult) -> dict:
    payload = asdict(item.chunk)
    payload["score"] = round(item.score, 4)
    payload["snippet"] = _snippet(item.chunk.text)
    payload.pop("text")
    return payload


def _snippet(text: str, max_chars: int = 96) -> str:
    compact = " ".join(text.split())
    if len(compact) <= max_chars:
        return compact
    return compact[:max_chars].rstrip() + "..."


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
    parser = argparse.ArgumentParser(description="Print a trace of the local RAG pipeline.")
    parser.add_argument("--question", required=True)
    parser.add_argument("--docs-dir", type=Path, default=PROJECT_ROOT / "data" / "documents")
    parser.add_argument("--top-k", type=positive_int, default=3)
    args = parser.parse_args()

    try:
        trace = build_trace(args.question, args.docs_dir, top_k=args.top_k)
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(trace, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
