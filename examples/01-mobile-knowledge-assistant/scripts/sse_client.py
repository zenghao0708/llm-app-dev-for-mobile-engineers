from __future__ import annotations

import argparse
from enum import Enum
import json
import urllib.parse
import urllib.request
import uuid
from typing import Iterable


class ClientState(str, Enum):
    IDLE = "idle"
    SUBMITTING = "submitting"
    WAITING_FIRST_TOKEN = "waiting_first_token"
    STREAMING = "streaming"
    DONE = "done"
    CANCELLED = "cancelled"
    FAILED = "failed"


def build_stream_url(base_url: str, question: str, request_id: str) -> str:
    query = urllib.parse.urlencode({"question": question, "request_id": request_id})
    return f"{base_url.rstrip('/')}/api/ask/stream?{query}"


def parse_sse_events(lines: Iterable[bytes]) -> Iterable[dict]:
    event_type = ""
    data_lines: list[str] = []

    for raw_line in lines:
        line = raw_line.decode("utf-8").rstrip("\r\n")
        if line.startswith("event:"):
            event_type = line.removeprefix("event:").strip()
        elif line.startswith("data:"):
            data_lines.append(line.removeprefix("data:").strip())
        elif line == "" and data_lines:
            payload = json.loads("\n".join(data_lines))
            if event_type:
                payload.setdefault("type", event_type)
            yield payload
            event_type = ""
            data_lines.clear()


def cancel_request(base_url: str, request_id: str) -> dict:
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/ask/{urllib.parse.quote(request_id)}/cancel",
        data=b"",
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def consume_stream(base_url: str, question: str, request_id: str, cancel_after_tokens: int = 0) -> ClientState:
    state = ClientState.SUBMITTING
    token_count = 0
    cancel_sent = False
    url = build_stream_url(base_url, question, request_id)

    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            state = ClientState.WAITING_FIRST_TOKEN
            for event in parse_sse_events(response):
                event_type = event.get("type")
                if event_type == "token":
                    state = ClientState.STREAMING
                    token_count += 1
                    print(event.get("content", ""), end="", flush=True)
                    if cancel_after_tokens and token_count >= cancel_after_tokens and not cancel_sent:
                        cancel_request(base_url, request_id)
                        cancel_sent = True
                elif event_type == "done":
                    print()
                    print(f"citations: {len(event.get('citations', []))}")
                    return ClientState.DONE
                elif event_type == "cancelled":
                    print()
                    return ClientState.CANCELLED
                elif event_type == "error":
                    print(f"\nerror: {event.get('code')} {event.get('message')}")
                    return ClientState.FAILED
    except Exception as exc:
        print(f"\nclient error: {exc}")
        return ClientState.FAILED

    return state


def main() -> None:
    parser = argparse.ArgumentParser(description="Consume the mobile knowledge assistant SSE API.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--question", required=True)
    parser.add_argument("--request-id", default="")
    parser.add_argument("--cancel-after-tokens", type=int, default=0)
    args = parser.parse_args()

    request_id = args.request_id or f"req_{uuid.uuid4().hex[:12]}"
    final_state = consume_stream(args.base_url, args.question, request_id, args.cancel_after_tokens)
    print(f"state: {final_state.value}")


if __name__ == "__main__":
    main()
