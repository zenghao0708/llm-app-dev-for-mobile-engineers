from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    provider: str
    api_url: str
    api_key: str
    model: str
    docs_dir: Path


def load_settings() -> Settings:
    """Load runtime settings from environment variables.

    The model API key is intentionally read only on the server side. A mobile
    app should call this service, not the model vendor directly, because keys
    embedded in an app package can be extracted.
    """

    docs_dir = Path(os.getenv("DOCS_DIR", PROJECT_ROOT / "data" / "documents"))
    return Settings(
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        provider=os.getenv("LLM_PROVIDER", "mock"),
        api_url=os.getenv("LLM_API_URL", "https://api.example.com/v1/chat/completions"),
        api_key=os.getenv("LLM_API_KEY", ""),
        model=os.getenv("LLM_MODEL", "example-chat-model"),
        docs_dir=docs_dir,
    )

