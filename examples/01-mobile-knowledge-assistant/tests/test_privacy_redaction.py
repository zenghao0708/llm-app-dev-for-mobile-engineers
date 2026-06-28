import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from privacy_redaction import read_input, redact_text, report_payload


class PrivacyRedactionTest(unittest.TestCase):
    def test_redacts_common_mobile_log_identifiers(self):
        report = redact_text(
            "email=a@example.com phone=13800138000 "
            "id=110101199003071234 device=550e8400-e29b-41d4-a716-446655440000 "
            "ip=10.1.2.3 api_key=test-secret-value"
        )

        self.assertNotIn("a@example.com", report.redacted_text)
        self.assertNotIn("13800138000", report.redacted_text)
        self.assertNotIn("110101199003071234", report.redacted_text)
        self.assertNotIn("550e8400-e29b-41d4-a716-446655440000", report.redacted_text)
        self.assertNotIn("10.1.2.3", report.redacted_text)
        self.assertNotIn("test-secret-value", report.redacted_text)
        self.assertIn("[EMAIL]", report.redacted_text)
        self.assertIn("[PHONE]", report.redacted_text)
        self.assertIn("[ID_CARD]", report.redacted_text)
        self.assertIn("[UUID]", report.redacted_text)
        self.assertIn("[IP_ADDRESS]", report.redacted_text)
        self.assertIn("[SECRET]", report.redacted_text)

    def test_report_contains_counts_not_raw_values(self):
        report = redact_text(
            "user=a@example.com token=abc123\n"
            "Authorization: Bearer raw-secret\n"
            '{"api_key":"json-secret"}'
        )
        payload = report_payload(report)
        encoded = json.dumps(payload, ensure_ascii=False)

        self.assertIn({"kind": "email", "count": 1}, payload["findings"])
        self.assertIn({"kind": "secret_assignment", "count": 1}, payload["findings"])
        self.assertIn({"kind": "secret_header", "count": 1}, payload["findings"])
        self.assertIn({"kind": "secret_json_field", "count": 1}, payload["findings"])
        self.assertNotIn("a@example.com", encoded)
        self.assertNotIn("abc123", encoded)
        self.assertNotIn("raw-secret", encoded)
        self.assertNotIn("json-secret", encoded)

    def test_redacts_authorization_cookie_and_set_cookie_headers(self):
        report = redact_text(
            "Authorization: Bearer jwt-secret\n"
            "Authorization: Basic basic-secret\n"
            "Cookie: session=abc; csrftoken=def\n"
            "Set-Cookie: sid=ghi; HttpOnly"
        )

        self.assertNotIn("jwt-secret", report.redacted_text)
        self.assertNotIn("basic-secret", report.redacted_text)
        self.assertNotIn("session=abc", report.redacted_text)
        self.assertNotIn("csrftoken=def", report.redacted_text)
        self.assertNotIn("sid=ghi", report.redacted_text)
        self.assertIn({"kind": "secret_header", "count": 4}, report_payload(report)["findings"])

    def test_redacts_key_value_secrets_with_spaces_and_cookie_segments(self):
        report = redact_text(
            "token=Bearer token-secret\n"
            "access_token=Bearer access-secret\n"
            "authorization=Bearer auth-secret\n"
            "cookie=session=abc; csrftoken=def"
        )

        self.assertNotIn("token-secret", report.redacted_text)
        self.assertNotIn("access-secret", report.redacted_text)
        self.assertNotIn("auth-secret", report.redacted_text)
        self.assertNotIn("session=abc", report.redacted_text)
        self.assertNotIn("csrftoken=def", report.redacted_text)
        self.assertIn({"kind": "secret_assignment", "count": 4}, report_payload(report)["findings"])

    def test_key_value_secret_keeps_following_plain_fields(self):
        report = redact_text("api_key=sk-test request_id=req_001 status=ok")

        self.assertNotIn("sk-test", report.redacted_text)
        self.assertIn("request_id=req_001", report.redacted_text)
        self.assertIn("status=ok", report.redacted_text)

    def test_header_redaction_is_not_counted_again_as_assignment(self):
        report = redact_text("Authorization: Bearer raw-secret")
        payload = report_payload(report)

        self.assertEqual(payload["findings"], [{"kind": "secret_header", "count": 1}])
        self.assertNotIn("raw-secret", payload["redacted_text"])

    def test_redacts_json_secret_fields(self):
        report = redact_text(
            '{"token":"abc123","access_token":"access-secret",'
            '"authorization":"Bearer auth-secret","cookie":"a=b; c=d"}'
        )
        encoded = json.dumps(report_payload(report), ensure_ascii=False)

        self.assertNotIn("abc123", encoded)
        self.assertNotIn("access-secret", encoded)
        self.assertNotIn("auth-secret", encoded)
        self.assertNotIn("a=b", encoded)
        self.assertNotIn("c=d", encoded)
        self.assertIn({"kind": "secret_json_field", "count": 4}, report_payload(report)["findings"])

    def test_no_findings_for_plain_text(self):
        report = redact_text("普通的功能说明，不包含隐私字段")

        self.assertEqual(report.redacted_text, "普通的功能说明，不包含隐私字段")
        self.assertEqual(report.findings, [])

    def test_read_input_rejects_text_and_file_together(self):
        with self.assertRaises(ValueError):
            read_input("hello", Path("log.txt"))

    def test_cli_redacts_file_without_printing_raw_secret(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "log.txt"
            path.write_text("Authorization: Bearer raw-secret\nemail=a@example.com", encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "privacy_redaction.py"), "--file", str(path)],
                check=True,
                capture_output=True,
                text=True,
            )

        payload = json.loads(result.stdout)
        self.assertIn("[SECRET]", payload["redacted_text"])
        self.assertIn("[EMAIL]", payload["redacted_text"])
        self.assertNotIn("raw-secret", result.stdout)
        self.assertNotIn("a@example.com", result.stdout)

    def test_cli_requires_input_source(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "privacy_redaction.py")],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("either --text or --file is required", result.stderr)

    def test_cli_rejects_text_and_file_together(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "log.txt"
            path.write_text("hello", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "privacy_redaction.py"),
                    "--text",
                    "hello",
                    "--file",
                    str(path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("use either --text or --file, not both", result.stderr)


if __name__ == "__main__":
    unittest.main()
