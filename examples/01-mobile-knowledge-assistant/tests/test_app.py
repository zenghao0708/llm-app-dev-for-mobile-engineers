from pathlib import Path
import json
import threading
import unittest
import urllib.error
import urllib.request
from urllib.parse import urlencode
from http.server import ThreadingHTTPServer

from mobile_llm.app import build_service, create_handler
from mobile_llm.config import Settings
from mobile_llm.retriever import LocalRetriever
from mobile_llm.service import KnowledgeAssistant


ROOT = Path(__file__).resolve().parents[1]


class AppTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        settings = Settings(
            host="127.0.0.1",
            port=0,
            provider="mock",
            api_url="",
            api_key="",
            model="mock",
            docs_dir=ROOT / "data" / "documents",
        )
        service = build_service(settings)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(service))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=3)
        cls.server.server_close()

    def test_health(self):
        with urllib.request.urlopen(f"{self.base_url}/health", timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(payload["status"], "ok")

    def test_ask_endpoint(self):
        body = json.dumps({"question": "移动端为什么不能直接保存模型 API Key？"}).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/api/ask",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(request, timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))

        self.assertIn("answer", payload)
        self.assertGreater(len(payload["citations"]), 0)

    def test_stream_endpoint(self):
        query = urlencode({"question": "如何处理移动端流式输出", "request_id": "req_stream_test"})
        url = f"{self.base_url}/api/ask/stream?{query}"

        with urllib.request.urlopen(url, timeout=3) as response:
            text = response.read().decode("utf-8")

        self.assertIn("event: token", text)
        self.assertIn('"type": "token"', text)
        self.assertIn("event: done", text)
        self.assertIn('"type": "done"', text)
        self.assertIn('"request_id": "req_stream_test"', text)

    def test_cancel_endpoint_accepts_request_id(self):
        provider = BlockingProvider()
        service = KnowledgeAssistant(LocalRetriever.from_directory(ROOT / "data" / "documents"), provider)
        server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(service))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_port}"
        stream = None

        try:
            query = urlencode({"question": "如何处理移动端流式输出", "request_id": "req_cancel_test"})
            stream = urllib.request.urlopen(f"{base_url}/api/ask/stream?{query}", timeout=3)
            first_data = _read_next_data_line(stream)
            self.assertIn('"type": "token"', first_data)

            request = urllib.request.Request(
                f"{base_url}/api/ask/req_cancel_test/cancel",
                data=b"",
                method="POST",
            )

            with urllib.request.urlopen(request, timeout=3) as response:
                payload = json.loads(response.read().decode("utf-8"))

            self.assertEqual(response.status, 202)
            self.assertEqual(payload["status"], "accepted")
            self.assertEqual(payload["request_id"], "req_cancel_test")

            provider.release()
            remaining = stream.read().decode("utf-8")
            self.assertIn("event: cancelled", remaining)
            self.assertIn('"type": "cancelled"', remaining)
            self.assertNotIn('"type": "done"', remaining)
        finally:
            if stream:
                stream.close()
            provider.release()
            server.shutdown()
            thread.join(timeout=3)
            server.server_close()

    def test_cancel_endpoint_returns_not_found_for_inactive_request(self):
        request = urllib.request.Request(
            f"{self.base_url}/api/ask/req_missing/cancel",
            data=b"",
            method="POST",
        )

        with self.assertRaises(urllib.error.HTTPError) as context:
            urllib.request.urlopen(request, timeout=3)

        error = context.exception
        try:
            self.assertEqual(error.code, 404)
            payload = json.loads(error.read().decode("utf-8"))
            self.assertEqual(payload["status"], "not_found")
            self.assertEqual(payload["request_id"], "req_missing")
        finally:
            error.close()

    def test_invalid_json_returns_bad_request(self):
        request = urllib.request.Request(
            f"{self.base_url}/api/ask",
            data=b"{not-json",
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with self.assertRaises(urllib.error.HTTPError) as context:
            urllib.request.urlopen(request, timeout=3)

        error = context.exception
        try:
            self.assertEqual(error.code, 400)
            payload = json.loads(error.read().decode("utf-8"))
            self.assertEqual(payload["error"], "invalid JSON body")
        finally:
            error.close()

    def test_invalid_request_id_returns_bad_request(self):
        body = json.dumps({"request_id": "../bad", "question": "hello"}).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/api/ask",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with self.assertRaises(urllib.error.HTTPError) as context:
            urllib.request.urlopen(request, timeout=3)

        error = context.exception
        try:
            self.assertEqual(error.code, 400)
            payload = json.loads(error.read().decode("utf-8"))
            self.assertEqual(payload["error"], "invalid request_id")
        finally:
            error.close()

    def test_ask_endpoint_returns_stable_error_when_provider_fails(self):
        service = KnowledgeAssistant(LocalRetriever.from_directory(ROOT / "data" / "documents"), FailingProvider())
        server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(service))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_port}"

        try:
            body = json.dumps({"question": "hello"}).encode("utf-8")
            request = urllib.request.Request(
                f"{base_url}/api/ask",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with self.assertRaises(urllib.error.HTTPError) as context:
                urllib.request.urlopen(request, timeout=3)

            error = context.exception
            try:
                self.assertEqual(error.code, 502)
                payload = json.loads(error.read().decode("utf-8"))
                self.assertEqual(payload["code"], "MODEL_ERROR")
                self.assertEqual(payload["error"], "model service unavailable")
            finally:
                error.close()
        finally:
            server.shutdown()
            thread.join(timeout=3)
            server.server_close()

    def test_large_json_body_returns_request_entity_too_large(self):
        request = urllib.request.Request(
            f"{self.base_url}/api/ask",
            data=json.dumps({"question": "x" * (70 * 1024)}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with self.assertRaises(urllib.error.HTTPError) as context:
            urllib.request.urlopen(request, timeout=3)

        error = context.exception
        try:
            self.assertEqual(error.code, 413)
            payload = json.loads(error.read().decode("utf-8"))
            self.assertEqual(payload["error"], "request body is too large")
        finally:
            error.close()


class BlockingProvider:
    def __init__(self):
        self._release = threading.Event()

    def generate(self, messages, contexts, question):
        del messages, contexts, question
        return "ok"

    def stream_generate(self, messages, contexts, question):
        del messages, contexts, question
        yield "第一段"
        self._release.wait(timeout=2)
        yield "第二段"

    def release(self):
        self._release.set()


class FailingProvider:
    def generate(self, messages, contexts, question):
        del messages, contexts, question
        raise RuntimeError("upstream failed")

    def stream_generate(self, messages, contexts, question):
        del messages, contexts, question
        raise RuntimeError("upstream failed")
        yield ""


def _read_next_data_line(stream) -> str:
    for _ in range(6):
        line = stream.readline().decode("utf-8")
        if line.startswith("data: "):
            return line
    raise AssertionError("SSE data line not found")


if __name__ == "__main__":
    unittest.main()
