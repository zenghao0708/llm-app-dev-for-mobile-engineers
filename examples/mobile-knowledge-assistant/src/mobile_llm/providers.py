from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Iterable, Protocol

from .config import Settings
from .retriever import SearchResult


MAX_PROVIDER_ATTEMPTS = 3
RETRYABLE_HTTP_STATUS = {408, 429, 500, 502, 503, 504}


class LLMProvider(Protocol):
    def generate(self, messages: list[dict[str, str]], contexts: list[SearchResult], question: str) -> str:
        ...

    def stream_generate(
        self, messages: list[dict[str, str]], contexts: list[SearchResult], question: str
    ) -> Iterable[str]:
        ...


class MockLLMProvider:
    """Deterministic provider used for local runs and tests.

    A runnable book example should not force every reader to apply for a model
    key first. This mock keeps the service behavior stable while preserving the
    same retrieval, Prompt and API boundaries used by the real provider.
    """

    def generate(self, messages: list[dict[str, str]], contexts: list[SearchResult], question: str) -> str:
        del messages
        if not contexts:
            return "根据当前资料无法确定。"

        top = contexts[0].chunk
        return (
            f"根据《{top.title}》的“{top.section}”部分，{_summarize(top.text)} "
            f"针对问题“{question}”，建议先按引用资料检查相关约束，再在移动端实现对应的状态与错误处理。"
        )

    def stream_generate(
        self, messages: list[dict[str, str]], contexts: list[SearchResult], question: str
    ) -> Iterable[str]:
        answer = self.generate(messages, contexts, question)
        parts = [part for part in answer.split("，") if part]
        for index, part in enumerate(parts):
            suffix = "，" if index < len(parts) - 1 else ""
            yield part + suffix


class OpenAICompatibleProvider:
    """Minimal OpenAI-compatible chat-completions client.

    The code uses urllib from the standard library to keep the example
    dependency-free. Production code can replace this class with the official
    SDK used by the team.
    """

    def __init__(self, settings: Settings):
        if not settings.api_key:
            raise ValueError("LLM_API_KEY is required when LLM_PROVIDER=openai_compatible")
        self.settings = settings

    def generate(self, messages: list[dict[str, str]], contexts: list[SearchResult], question: str) -> str:
        del contexts, question
        body = json.dumps(
            {
                "model": self.settings.model,
                "messages": messages,
                "temperature": 0.2,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            self.settings.api_url,
            data=body,
            headers={
                "Authorization": f"Bearer {self.settings.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        for attempt in range(MAX_PROVIDER_ATTEMPTS):
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    return payload["choices"][0]["message"]["content"]
            except urllib.error.HTTPError as exc:
                should_retry = _should_retry_http_status(exc.code, attempt)
                exc.close()
                if not should_retry:
                    raise RuntimeError(f"LLM request failed with HTTP {exc.code}") from exc
                _sleep_before_retry(attempt)
            except urllib.error.URLError as exc:
                if attempt == MAX_PROVIDER_ATTEMPTS - 1:
                    raise RuntimeError(f"LLM request failed: {exc}") from exc
                _sleep_before_retry(attempt)

        raise RuntimeError("LLM request failed after retries")

    def stream_generate(
        self, messages: list[dict[str, str]], contexts: list[SearchResult], question: str
    ) -> Iterable[str]:
        # This fallback preserves the server-side SSE contract, but it is not a
        # true token stream: the upstream call still waits for a full response.
        # Production gateways should implement stream=True parsing here.
        yield self.generate(messages, contexts, question)


def create_provider(settings: Settings) -> LLMProvider:
    if settings.provider == "mock":
        return MockLLMProvider()
    if settings.provider == "openai_compatible":
        return OpenAICompatibleProvider(settings)
    raise ValueError(f"Unsupported LLM_PROVIDER: {settings.provider}")


def _summarize(text: str, max_chars: int = 72) -> str:
    compact = " ".join(text.split())
    if len(compact) <= max_chars:
        return compact
    return compact[:max_chars].rstrip() + "..."


def _should_retry_http_status(status: int, attempt: int) -> bool:
    return status in RETRYABLE_HTTP_STATUS and attempt < MAX_PROVIDER_ATTEMPTS - 1


def _sleep_before_retry(attempt: int) -> None:
    time.sleep(0.2 * (2**attempt))
