from pathlib import Path
import json
import unittest
import urllib.error
from unittest.mock import patch

from mobile_llm.config import Settings
from mobile_llm.providers import OpenAICompatibleProvider


ROOT = Path(__file__).resolve().parents[1]


class OpenAICompatibleProviderTest(unittest.TestCase):
    def test_retryable_http_status_is_retried(self):
        provider = OpenAICompatibleProvider(_settings())
        too_many_requests = urllib.error.HTTPError(
            url="https://api.example.com/v1/chat/completions",
            code=429,
            msg="rate limited",
            hdrs=None,
            fp=None,
        )

        with (
            patch(
                "mobile_llm.providers.urllib.request.urlopen",
                side_effect=[too_many_requests, _FakeResponse({"choices": [{"message": {"content": "ok"}}]})],
            ) as urlopen,
            patch("mobile_llm.providers.time.sleep") as sleep,
        ):
            answer = provider.generate([{"role": "user", "content": "hello"}], [], "hello")

        self.assertEqual(answer, "ok")
        self.assertEqual(urlopen.call_count, 2)
        sleep.assert_called_once()

    def test_auth_error_is_not_retried(self):
        provider = OpenAICompatibleProvider(_settings())
        unauthorized = urllib.error.HTTPError(
            url="https://api.example.com/v1/chat/completions",
            code=401,
            msg="unauthorized",
            hdrs=None,
            fp=None,
        )

        with patch("mobile_llm.providers.urllib.request.urlopen", side_effect=unauthorized) as urlopen:
            with self.assertRaises(RuntimeError):
                provider.generate([{"role": "user", "content": "hello"}], [], "hello")

        self.assertEqual(urlopen.call_count, 1)

    def test_network_error_stops_after_max_attempts(self):
        provider = OpenAICompatibleProvider(_settings())
        network_error = urllib.error.URLError("temporary network failure")

        with (
            patch("mobile_llm.providers.urllib.request.urlopen", side_effect=network_error) as urlopen,
            patch("mobile_llm.providers.time.sleep") as sleep,
        ):
            with self.assertRaises(RuntimeError):
                provider.generate([{"role": "user", "content": "hello"}], [], "hello")

        self.assertEqual(urlopen.call_count, 3)
        self.assertEqual(sleep.call_count, 2)


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def _settings() -> Settings:
    return Settings(
        host="127.0.0.1",
        port=0,
        provider="openai_compatible",
        api_url="https://api.example.com/v1/chat/completions",
        api_key="test-key",
        model="test-model",
        docs_dir=ROOT / "data" / "documents",
    )


if __name__ == "__main__":
    unittest.main()
