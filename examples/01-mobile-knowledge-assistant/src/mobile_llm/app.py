from __future__ import annotations

import json
import re
import threading
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from .config import Settings, load_settings
from .providers import create_provider
from .retriever import LocalRetriever
from .service import KnowledgeAssistant


MAX_JSON_BODY_BYTES = 64 * 1024
REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,80}$")


class BadRequestError(ValueError):
    pass


class RequestTooLargeError(ValueError):
    pass


def build_service(settings: Settings) -> KnowledgeAssistant:
    retriever = LocalRetriever.from_directory(settings.docs_dir)
    provider = create_provider(settings)
    return KnowledgeAssistant(retriever, provider)


class CancellationRegistry:
    """Tracks user-initiated cancellations by request ID.

    The registry is intentionally small and in-memory because the example server
    runs as a single process. A production service should store equivalent state
    in the request worker, gateway or task queue that owns the model call.
    """

    def __init__(self) -> None:
        self._active: set[str] = set()
        self._cancelled: set[str] = set()
        self._lock = threading.Lock()

    def register(self, request_id: str) -> bool:
        with self._lock:
            if request_id in self._active:
                return False
            self._active.add(request_id)
            self._cancelled.discard(request_id)
            return True

    def cancel(self, request_id: str) -> bool:
        with self._lock:
            if request_id not in self._active:
                return False
            self._cancelled.add(request_id)
            return True

    def unregister(self, request_id: str) -> None:
        with self._lock:
            self._active.discard(request_id)
            self._cancelled.discard(request_id)

    def is_cancelled(self, request_id: str) -> bool:
        with self._lock:
            return request_id in self._cancelled


def create_handler(service: KnowledgeAssistant, cancellations: CancellationRegistry | None = None):
    cancellations = cancellations or CancellationRegistry()

    class Handler(BaseHTTPRequestHandler):
        server_version = "MobileKnowledgeAssistant/1.0"

        def do_OPTIONS(self) -> None:
            self._send_empty(HTTPStatus.NO_CONTENT)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/health":
                self._send_json({"status": "ok"})
                return
            if parsed.path == "/api/ask/stream":
                query_params = parse_qs(parsed.query)
                query = query_params.get("question", [""])[0].strip()
                request_id = query_params.get("request_id", [""])[0].strip()
                if not query:
                    self._send_json({"error": "question is required"}, HTTPStatus.BAD_REQUEST)
                    return
                if request_id and not _valid_request_id(request_id):
                    self._send_json({"error": "invalid request_id"}, HTTPStatus.BAD_REQUEST)
                    return
                self._send_sse(query, request_id)
                return
            self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            cancel_request_id = self._cancel_request_id(parsed.path)
            if cancel_request_id:
                if not _valid_request_id(cancel_request_id):
                    self._send_json({"error": "invalid request_id"}, HTTPStatus.BAD_REQUEST)
                    return
                if not cancellations.cancel(cancel_request_id):
                    self._send_json(
                        {"status": "not_found", "request_id": cancel_request_id},
                        HTTPStatus.NOT_FOUND,
                    )
                    return
                self._send_json(
                    {"status": "accepted", "request_id": cancel_request_id},
                    HTTPStatus.ACCEPTED,
                )
                return

            if parsed.path != "/api/ask":
                self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
                return

            try:
                payload = self._read_json()
            except RequestTooLargeError as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
                return
            except BadRequestError as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                return

            question = str(payload.get("question", "")).strip()
            if not question:
                self._send_json({"error": "question is required"}, HTTPStatus.BAD_REQUEST)
                return
            request_id = str(payload.get("request_id", "")).strip()
            if request_id and not _valid_request_id(request_id):
                self._send_json({"error": "invalid request_id"}, HTTPStatus.BAD_REQUEST)
                return

            # The mobile app sends only user input and app state. Model keys,
            # retrieval details and Prompt templates stay on the server side.
            try:
                result = service.answer(question)
            except Exception:
                self._send_json(
                    {
                        "error": "model service unavailable",
                        "code": "MODEL_ERROR",
                    },
                    HTTPStatus.BAD_GATEWAY,
                )
                return
            if request_id:
                result["request_id"] = request_id
            self._send_json(result)

        def _read_json(self) -> dict:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError as exc:
                raise BadRequestError("invalid Content-Length") from exc
            if length < 0:
                raise BadRequestError("invalid Content-Length")
            if length > MAX_JSON_BODY_BYTES:
                raise RequestTooLargeError("request body is too large")

            body = self.rfile.read(length)
            if not body:
                return {}
            try:
                payload = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise BadRequestError("invalid JSON body") from exc
            if not isinstance(payload, dict):
                raise BadRequestError("JSON body must be an object")
            return payload

        def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self._send_common_headers()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _send_empty(self, status: HTTPStatus) -> None:
            self.send_response(status)
            self._send_common_headers()
            self.send_header("Content-Length", "0")
            self.end_headers()

        def _send_sse(self, question: str, request_id: str) -> None:
            request_id = request_id or f"req_{uuid.uuid4().hex[:12]}"
            if not cancellations.register(request_id):
                self._send_json(
                    {"error": "request_id is already active", "request_id": request_id},
                    HTTPStatus.CONFLICT,
                )
                return
            self.send_response(HTTPStatus.OK)
            self._send_common_headers()
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            try:
                for event in service.stream_answer(
                    question,
                    request_id=request_id,
                    is_cancelled=lambda: cancellations.is_cancelled(request_id),
                ):
                    self._write_sse(event)
            except (BrokenPipeError, ConnectionResetError):
                return
            except Exception:
                # Keep provider internals out of the mobile contract; the client
                # only needs a stable code and a user-facing message.
                try:
                    self._write_sse(
                        {
                            "type": "error",
                            "request_id": request_id,
                            "code": "MODEL_ERROR",
                            "message": "模型服务暂时不可用，请稍后重试",
                        }
                    )
                except (BrokenPipeError, ConnectionResetError):
                    return
            finally:
                cancellations.unregister(request_id)

        def _write_sse(self, event: dict) -> None:
            data = json.dumps(event, ensure_ascii=False)
            event_type = str(event.get("type", "message"))
            self.wfile.write(f"event: {event_type}\ndata: {data}\n\n".encode("utf-8"))
            # Flush each chunk so a mobile UI can render progressively.
            self.wfile.flush()

        def _send_common_headers(self) -> None:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

        def log_message(self, format: str, *args) -> None:
            # Keep test output clean. Production services should write structured
            # logs with request IDs and without raw private user content.
            return

        def _cancel_request_id(self, path: str) -> str:
            prefix = "/api/ask/"
            suffix = "/cancel"
            if not path.startswith(prefix) or not path.endswith(suffix):
                return ""
            request_id = path[len(prefix) : -len(suffix)]
            return unquote(request_id.strip("/"))

    return Handler


def _valid_request_id(request_id: str) -> bool:
    return bool(REQUEST_ID_RE.fullmatch(request_id))


def run(settings: Settings | None = None) -> None:
    settings = settings or load_settings()
    service = build_service(settings)
    server = ThreadingHTTPServer((settings.host, settings.port), create_handler(service))
    print(f"Serving on http://{settings.host}:{settings.port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
