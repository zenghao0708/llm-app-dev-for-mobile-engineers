from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path


WORD_RE = re.compile(r"[A-Za-z0-9_@.+-]+")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")


@dataclass(frozen=True)
class DocumentChunk:
    source: str
    title: str
    section: str
    text: str


@dataclass(frozen=True)
class SearchResult:
    chunk: DocumentChunk
    score: float


def tokenize(text: str) -> set[str]:
    """Tokenize mixed Chinese and English text for a small local retriever.

    This is not meant to replace a vector database. It gives readers a real,
    dependency-free retrieval path that can be tested before swapping in
    Embedding and a vector store in later chapters.
    """

    lowered = text.lower()
    words = set(WORD_RE.findall(lowered))
    cjk_chars = CJK_RE.findall(lowered)
    bigrams = {a + b for a, b in zip(cjk_chars, cjk_chars[1:])}
    return words | set(cjk_chars) | bigrams


def load_markdown_chunks(docs_dir: Path) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    for path in sorted(docs_dir.glob("*.md")):
        chunks.extend(_split_markdown(path))
    return chunks


def _split_markdown(path: Path) -> list[DocumentChunk]:
    title = path.stem
    section = "正文"
    buffer: list[str] = []
    chunks: list[DocumentChunk] = []

    def flush() -> None:
        text = "\n".join(line for line in buffer if line.strip()).strip()
        if text:
            chunks.append(
                DocumentChunk(
                    source=path.name,
                    title=title,
                    section=section,
                    text=text,
                )
            )
        buffer.clear()

    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            flush()
            title = line[2:].strip()
            section = title
        elif line.startswith("## "):
            flush()
            section = line[3:].strip()
        else:
            buffer.append(line)
    flush()
    return chunks


class LocalRetriever:
    def __init__(self, chunks: list[DocumentChunk]):
        self._index = [(chunk, tokenize(f"{chunk.title} {chunk.section} {chunk.text}")) for chunk in chunks]

    @classmethod
    def from_directory(cls, docs_dir: Path) -> "LocalRetriever":
        return cls(load_markdown_chunks(docs_dir))

    def search(self, query: str, top_k: int = 3) -> list[SearchResult]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        results: list[SearchResult] = []
        for chunk, tokens in self._index:
            overlap = query_tokens & tokens
            if not overlap:
                continue
            # Normalize by token counts so long sections do not always win.
            score = len(overlap) / math.sqrt(len(query_tokens) * len(tokens))
            results.append(SearchResult(chunk=chunk, score=score))

        results.sort(key=lambda item: item.score, reverse=True)
        return results[:top_k]

