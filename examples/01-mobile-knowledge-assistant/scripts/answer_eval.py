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

from mobile_llm.providers import MockLLMProvider
from mobile_llm.retriever import LocalRetriever
from mobile_llm.service import KnowledgeAssistant


@dataclass(frozen=True)
class CitationRequirement:
    source: str
    section: str


@dataclass(frozen=True)
class AnswerEvalCase:
    id: str
    question: str
    expected_terms: tuple[str, ...]
    required_citation: CitationRequirement
    forbidden_terms: tuple[str, ...] = ()


def load_cases(path: Path) -> list[AnswerEvalCase]:
    """Load answer-level golden cases and reject incomplete data early."""

    if not path.is_file():
        raise FileNotFoundError(f"cases file not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid answer eval cases JSON: {path}") from exc
    if not isinstance(payload, list) or not payload:
        raise ValueError("answer eval cases must be a non-empty JSON array")

    cases = [_load_case(item, index) for index, item in enumerate(payload, start=1)]
    return cases


def evaluate(cases: list[AnswerEvalCase], docs_dir: Path, top_k: int = 3, min_score: float = 0.8) -> dict:
    """Run the local assistant and score answers with deterministic rules.

    This is not a replacement for human review or model-as-judge. It is a fast
    regression gate that checks whether important terms, citations, and safety
    constraints still hold after Prompt, retrieval, or provider changes.
    """

    if not cases:
        raise ValueError("cases must not be empty")
    if top_k <= 0:
        raise ValueError("top_k must be greater than 0")
    if not 0 <= min_score <= 1:
        raise ValueError("min_score must be between 0 and 1")
    _validate_docs_dir(docs_dir)

    assistant = KnowledgeAssistant(LocalRetriever.from_directory(docs_dir), MockLLMProvider())
    results = [_evaluate_case(assistant, case, top_k, min_score) for case in cases]
    passed = sum(1 for item in results if item["passed"])
    average_score = sum(item["score"] for item in results) / len(results)

    return {
        "case_count": len(results),
        "passed_count": passed,
        "pass_rate": round(passed / len(results), 4),
        "average_score": round(average_score, 4),
        "min_score": min_score,
        "results": results,
    }


def _evaluate_case(assistant: KnowledgeAssistant, case: AnswerEvalCase, top_k: int, min_score: float) -> dict:
    response = assistant.answer(case.question, top_k=top_k)
    answer = response["answer"]
    normalized_answer = _normalize(answer)
    matched_terms = [term for term in case.expected_terms if _normalize(term) in normalized_answer]
    missing_terms = [term for term in case.expected_terms if term not in matched_terms]
    forbidden_hits = [term for term in case.forbidden_terms if _normalize(term) in normalized_answer]
    citation_hit = _has_required_citation(response["citations"], case.required_citation)

    coverage_score = len(matched_terms) / len(case.expected_terms)
    citation_score = 1.0 if citation_hit else 0.0
    safety_score = 0.0 if forbidden_hits else 1.0
    score = round(0.6 * coverage_score + 0.3 * citation_score + 0.1 * safety_score, 4)

    passed = score >= min_score and not missing_terms and citation_hit and not forbidden_hits

    return {
        "id": case.id,
        "question": case.question,
        "score": score,
        "passed": passed,
        "matched_terms": matched_terms,
        "missing_terms": missing_terms,
        "citation_hit": citation_hit,
        "required_citation": {
            "source": case.required_citation.source,
            "section": case.required_citation.section,
        },
        "forbidden_hits": forbidden_hits,
        "answer": answer,
        "citations": [
            {
                "source": item["source"],
                "section": item["section"],
                "score": item["score"],
            }
            for item in response["citations"]
        ],
    }


def _load_case(item: object, index: int) -> AnswerEvalCase:
    if not isinstance(item, dict):
        raise ValueError(f"answer eval case #{index} must be an object")
    citation = item.get("required_citation")
    if not isinstance(citation, dict):
        raise ValueError(f"answer eval case #{index} field 'required_citation' must be an object")
    expected_terms = _required_string_list(item, "expected_terms", index)
    forbidden_terms = _optional_string_list(item, "forbidden_terms", index)
    return AnswerEvalCase(
        id=_required_str(item, "id", index),
        question=_required_str(item, "question", index),
        expected_terms=tuple(expected_terms),
        required_citation=CitationRequirement(
            source=_required_str(citation, "source", index),
            section=_required_str(citation, "section", index),
        ),
        forbidden_terms=tuple(forbidden_terms),
    )


def _has_required_citation(citations: list[dict], required: CitationRequirement) -> bool:
    return any(item.get("source") == required.source and item.get("section") == required.section for item in citations)


def _required_str(item: dict, field: str, index: int) -> str:
    value = item.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"answer eval case #{index} field {field!r} must be a non-empty string")
    return value.strip()


def _required_string_list(item: dict, field: str, index: int) -> list[str]:
    values = item.get(field)
    if not isinstance(values, list) or not values:
        raise ValueError(f"answer eval case #{index} field {field!r} must be a non-empty list")
    normalized = []
    for value_index, value in enumerate(values):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"answer eval case #{index} field {field!r}[{value_index}] must be a non-empty string")
        normalized.append(value.strip())
    return normalized


def _optional_string_list(item: dict, field: str, index: int) -> list[str]:
    values = item.get(field, [])
    if not isinstance(values, list):
        raise ValueError(f"answer eval case #{index} field {field!r} must be a list")
    normalized = []
    for value_index, value in enumerate(values):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"answer eval case #{index} field {field!r}[{value_index}] must be a non-empty string")
        normalized.append(value.strip())
    return normalized


def _normalize(text: str) -> str:
    return " ".join(text.casefold().split())


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


def score_threshold(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a number between 0 and 1") from exc
    if not 0 <= parsed <= 1:
        raise argparse.ArgumentTypeError("must be a number between 0 and 1")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate answer quality for the local mobile knowledge assistant.")
    parser.add_argument("--cases", type=Path, default=PROJECT_ROOT / "data" / "eval" / "answer_eval_cases.json")
    parser.add_argument("--docs-dir", type=Path, default=PROJECT_ROOT / "data" / "documents")
    parser.add_argument("--top-k", type=positive_int, default=3)
    parser.add_argument("--min-score", type=score_threshold, default=0.8)
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Print the report but do not fail the process when quality cases fail.",
    )
    args = parser.parse_args()

    try:
        payload = evaluate(load_cases(args.cases), args.docs_dir, top_k=args.top_k, min_score=args.min_score)
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if not args.report_only and payload["passed_count"] != payload["case_count"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
