from __future__ import annotations

from dataclasses import asdict
from typing import Callable, Iterable

from .prompts import build_rag_messages
from .providers import LLMProvider
from .retriever import LocalRetriever, SearchResult


class KnowledgeAssistant:
    def __init__(self, retriever: LocalRetriever, provider: LLMProvider):
        self.retriever = retriever
        self.provider = provider

    def answer(self, question: str, top_k: int = 3) -> dict:
        contexts = self.retriever.search(question, top_k=top_k)
        messages = build_rag_messages(question, contexts)
        answer = self.provider.generate(messages, contexts, question)
        return {
            "answer": answer,
            "citations": [_citation(item) for item in contexts],
        }

    def stream_answer(
        self,
        question: str,
        top_k: int = 3,
        request_id: str = "",
        is_cancelled: Callable[[], bool] | None = None,
    ) -> Iterable[dict]:
        contexts = self.retriever.search(question, top_k=top_k)
        messages = build_rag_messages(question, contexts)

        # SSE clients on mobile often render each chunk immediately. Keep each
        # emitted event small and structured so the UI can update progressively.
        for chunk in self.provider.stream_generate(messages, contexts, question):
            if is_cancelled and is_cancelled():
                yield _event("cancelled", request_id)
                return
            yield _event("token", request_id, content=chunk)
        if is_cancelled and is_cancelled():
            yield _event("cancelled", request_id)
            return
        yield _event("done", request_id, citations=[_citation(item) for item in contexts])


def _citation(item: SearchResult) -> dict:
    data = asdict(item.chunk)
    data["score"] = round(item.score, 4)
    return data


def _event(event_type: str, request_id: str, **payload) -> dict:
    event = {"type": event_type, **payload}
    if request_id:
        event["request_id"] = request_id
    return event
