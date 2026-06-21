from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mobile_llm.retriever import LocalRetriever, SearchResult


@dataclass(frozen=True)
class RagEvalCase:
    """A retrieval-only golden case used before judging model answers."""

    id: str
    question: str
    expected_source: str
    expected_section: str


def load_cases(path: Path) -> list[RagEvalCase]:
    """Load golden questions and fail fast on malformed cases.

    The book uses this script as a production-style quality gate. Invalid
    evaluation data should stop the run, otherwise a green score can hide that
    the test set was empty or incomplete.
    """

    if not path.is_file():
        raise FileNotFoundError(f"cases file not found: {path}")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid eval cases JSON: {path}") from exc
    if not isinstance(payload, list):
        raise ValueError("eval cases must be a JSON array")

    cases: list[RagEvalCase] = []
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"eval case #{index} must be an object")
        cases.append(
            RagEvalCase(
                id=_required_str(item, "id", index),
                question=_required_str(item, "question", index),
                expected_source=_required_str(item, "expected_source", index),
                expected_section=_required_str(item, "expected_section", index),
            )
        )
    if not cases:
        raise ValueError("eval cases must not be empty")
    return cases


def evaluate(cases: list[RagEvalCase], docs_dir: Path, top_k: int = 3) -> dict:
    """Evaluate whether expected document sections appear in Top-K retrieval.

    This function deliberately does not call an LLM. It isolates the retrieval
    layer so readers can tell whether an answer problem came from missing
    context before they tune prompts or model parameters.
    """

    if top_k <= 0:
        raise ValueError("top_k must be greater than 0")
    if not cases:
        raise ValueError("cases must not be empty")
    _validate_docs_dir(docs_dir)

    retriever = LocalRetriever.from_directory(docs_dir)
    results = [_evaluate_case(retriever, case, top_k) for case in cases]
    hits = sum(1 for item in results if item["hit"])
    # MRR rewards placing the expected section earlier in the ranked list.
    reciprocal_ranks = [1 / item["rank"] for item in results if item["rank"]]
    mrr = sum(reciprocal_ranks) / len(results)

    return {
        "top_k": top_k,
        "case_count": len(results),
        "hit_count": hits,
        "hit_rate": round(hits / len(results), 4),
        "mrr": round(mrr, 4),
        "results": results,
    }


def _evaluate_case(retriever: LocalRetriever, case: RagEvalCase, top_k: int) -> dict:
    retrieved = retriever.search(case.question, top_k=top_k)
    rank = _expected_rank(retrieved, case)
    return {
        "id": case.id,
        "question": case.question,
        "expected": {
            "source": case.expected_source,
            "section": case.expected_section,
        },
        "hit": rank is not None,
        "rank": rank,
        "retrieved": [_result_payload(item) for item in retrieved],
    }


def _expected_rank(results: list[SearchResult], case: RagEvalCase) -> int | None:
    for index, item in enumerate(results, start=1):
        if item.chunk.source == case.expected_source and item.chunk.section == case.expected_section:
            return index
    return None


def _result_payload(item: SearchResult) -> dict:
    return {
        "source": item.chunk.source,
        "section": item.chunk.section,
        "score": round(item.score, 4),
        "snippet": _snippet(item.chunk.text),
    }


def _snippet(text: str, max_chars: int = 80) -> str:
    compact = " ".join(text.split())
    if len(compact) <= max_chars:
        return compact
    return compact[:max_chars].rstrip() + "..."


def _required_str(item: dict, field: str, index: int) -> str:
    value = item.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"eval case #{index} field {field!r} must be a non-empty string")
    return value.strip()


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
    parser = argparse.ArgumentParser(description="Evaluate whether local RAG retrieval finds expected sections.")
    parser.add_argument("--cases", type=Path, default=PROJECT_ROOT / "data" / "eval" / "rag_eval_cases.json")
    parser.add_argument("--docs-dir", type=Path, default=PROJECT_ROOT / "data" / "documents")
    parser.add_argument("--top-k", type=positive_int, default=3)
    args = parser.parse_args()

    try:
        payload = evaluate(load_cases(args.cases), args.docs_dir, top_k=args.top_k)
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
