import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from dev_environment_check import _check_env_example, run_checks


class DevEnvironmentCheckTest(unittest.TestCase):
    def test_default_environment_passes(self):
        payload = run_checks()

        self.assertTrue(payload["passed"])
        self.assertTrue(_check_passed(payload, "python_version"))
        self.assertTrue(_check_passed(payload, "env_example"))
        self.assertTrue(_check_passed(payload, "mock_assistant_smoke"))
        self.assertIn("answer_preview", payload["sample"])
        self.assertIn("first_citation", payload["sample"])

    def test_report_does_not_echo_raw_api_key(self):
        with patch.dict(os.environ, {"LLM_API_KEY": "local-secret-value"}, clear=False):
            payload = run_checks()

        encoded = json.dumps(payload, ensure_ascii=False)
        self.assertTrue(payload["settings"]["api_key_set"])
        self.assertNotIn("local-secret-value", encoded)

    def test_report_sanitizes_api_url_credentials_and_query(self):
        secret_url = "https://user:pass-secret@example.com/v1/chat?api_key=query-secret#fragment-secret"
        with patch.dict(os.environ, {"LLM_API_URL": secret_url}, clear=False):
            payload = run_checks()

        encoded = json.dumps(payload, ensure_ascii=False)
        self.assertEqual(payload["settings"]["api_url"], "https://example.com/v1/chat")
        self.assertNotIn("pass-secret", encoded)
        self.assertNotIn("query-secret", encoded)
        self.assertNotIn("fragment-secret", encoded)

    def test_env_example_rejects_non_placeholder_api_key(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env_example = Path(temp_dir) / ".env.example"
            env_example.write_text(
                "\n".join(
                    [
                        "LLM_PROVIDER=mock",
                        "LLM_API_URL=https://api.example.com/v1/chat/completions",
                        "LLM_API_KEY=" + "AI" + "zaSyD_fake_secret_value_for_testing",
                        "LLM_MODEL=example-chat-model",
                    ]
                ),
                encoding="utf-8",
            )

            payload = _check_env_example(env_example)

        self.assertFalse(payload["passed"])
        self.assertFalse(payload["details"]["api_key_is_placeholder"])
        self.assertIn("LLM_API_KEY", payload["details"]["secret_like_keys"])

    def test_env_example_rejects_url_with_secret_query(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env_example = Path(temp_dir) / ".env.example"
            env_example.write_text(
                "\n".join(
                    [
                        "LLM_PROVIDER=mock",
                        "LLM_API_URL=https://api.example.com/v1/chat/completions?api_key=query-secret",
                        "LLM_API_KEY=replace-with-your-api-key",
                        "LLM_MODEL=example-chat-model",
                    ]
                ),
                encoding="utf-8",
            )

            payload = _check_env_example(env_example)

        self.assertFalse(payload["passed"])
        self.assertIn("LLM_API_URL", payload["details"]["secret_like_keys"])

    def test_missing_docs_dir_fails_without_exception(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "missing-docs"

            payload = run_checks(docs_dir=missing)

        self.assertFalse(payload["passed"])
        self.assertFalse(_check_passed(payload, "docs_dir"))
        self.assertFalse(_check_passed(payload, "mock_assistant_smoke"))

    def test_cli_outputs_json(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "dev_environment_check.py")],
            check=True,
            capture_output=True,
            text=True,
        )

        payload = json.loads(result.stdout)
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["settings"]["provider"], "mock")


def _check_passed(payload: dict, name: str) -> bool:
    return next(item["passed"] for item in payload["checks"] if item["name"] == name)


if __name__ == "__main__":
    unittest.main()
