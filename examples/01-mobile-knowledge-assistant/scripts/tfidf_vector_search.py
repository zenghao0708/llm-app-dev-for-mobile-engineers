from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mobile_llm.retriever import CJK_RE, WORD_RE, DocumentChunk, load_markdown_chunks


@dataclass(frozen=True)
class VectorSearchHit:
    source: str
    title: str
    section: str
    score: float
    snippet: str


class TfidfVectorIndex:
    """A small, dependency-free vector index for explaining retrieval mechanics.

    The vector is not a neural Embedding. It is a TF-IDF vector built from the
    local Markdown corpus, which makes the same indexing, normalization and
    cosine-similarity steps visible before readers replace it with a production
    Embedding model and vector database.
    """

    def __init__(self, chunks: list[DocumentChunk]):
        if not chunks:
            raise ValueError("chunks must not be empty")

        self._chunks = chunks
        self._idf = _build_idf(chunks)
        self.dimension = len(self._idf)
        self._vectors = [_normalize(_tfidf(chunk, self._idf)) for chunk in chunks]

    @property
    def size(self) -> int:
        return len(self._chunks)

    @classmethod
    def from_directory(cls, docs_dir: Path) -> "TfidfVectorIndex":
        _validate_docs_dir(docs_dir)
        return cls(load_markdown_chunks(docs_dir))

    def search(self, query: str, top_k: int = 3) -> list[VectorSearchHit]:
        if top_k <= 0:
            raise ValueError("top_k must be greater than 0")

        query_vector = _normalize(_tfidf_text(query, self._idf))
        if not query_vector:
            return []

        scored_hits: list[tuple[float, VectorSearchHit]] = []
        for chunk, vector in zip(self._chunks, self._vectors):
            score = _dot(query_vector, vector)
            if score <= 0:
                continue
            scored_hits.append(
                (
                    score,
                    VectorSearchHit(
                        source=chunk.source,
                        title=chunk.title,
                        section=chunk.section,
                        score=round(score, 4),
                        snippet=_snippet(chunk.text),
                    ),
                )
            )

        scored_hits.sort(key=lambda item: item[0], reverse=True)
        return [hit for _, hit in scored_hits[:top_k]]


def search_payload(question: str, docs_dir: Path, top_k: int = 3) -> dict:
    index = TfidfVectorIndex.from_directory(docs_dir)
    hits = index.search(question, top_k=top_k)
    return {
        "question": question,
        "index_size": index.size,
        "vector_dimension": index.dimension,
        "results": [hit.__dict__ for hit in hits],
    }


def _build_idf(chunks: list[DocumentChunk]) -> dict[str, float]:
    document_frequency: Counter[str] = Counter()
    for chunk in chunks:
        document_frequency.update(_terms_for_chunk(chunk).keys())

    total_docs = len(chunks)
    return {
        term: math.log((1 + total_docs) / (1 + frequency)) + 1
        for term, frequency in document_frequency.items()
    }


def _terms_for_chunk(chunk: DocumentChunk) -> Counter[str]:
    return _term_counts(f"{chunk.title} {chunk.section} {chunk.text}")


def _tfidf(chunk: DocumentChunk, idf: dict[str, float]) -> dict[str, float]:
    return _weighted_terms(_terms_for_chunk(chunk), idf)


def _tfidf_text(text: str, idf: dict[str, float]) -> dict[str, float]:
    return _weighted_terms(_term_counts(text), idf)


def _term_counts(text: str) -> Counter[str]:
    lowered = text.lower()
    terms: Counter[str] = Counter(WORD_RE.findall(lowered))
    cjk_chars = CJK_RE.findall(lowered)
    terms.update(cjk_chars)
    terms.update(a + b for a, b in zip(cjk_chars, cjk_chars[1:]))
    return terms


def _weighted_terms(terms: Counter[str], idf: dict[str, float]) -> dict[str, float]:
    weighted: dict[str, float] = {}
    for term, count in terms.items():
        if term not in idf:
            continue
        weighted[term] = (1 + math.log(count)) * idf[term]
    return weighted


def _normalize(vector: dict[str, float]) -> dict[str, float]:
    norm = math.sqrt(sum(value * value for value in vector.values()))
    if norm == 0:
        return {}
    return {term: value / norm for term, value in vector.items()}


def _dot(left: dict[str, float], right: dict[str, float]) -> float:
    if len(left) > len(right):
        left, right = right, left
    return sum(value * right.get(term, 0.0) for term, value in left.items())


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
    parser = argparse.ArgumentParser(description="Run a local TF-IDF vector search over Markdown docs.")
    parser.add_argument("--question", required=True)
    parser.add_argument("--docs-dir", type=Path, default=PROJECT_ROOT / "data" / "documents")
    parser.add_argument("--top-k", type=positive_int, default=3)
    args = parser.parse_args()

    try:
        payload = search_payload(args.question, args.docs_dir, top_k=args.top_k)
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
