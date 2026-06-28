import unittest

from ai_refactor.app_error import ErrorKind, ErrorMapper, NetworkFailure


class ErrorMapperTest(unittest.TestCase):
    def test_timeout_is_retryable(self):
        error = ErrorMapper.from_network_failure(NetworkFailure(code="timeout"))

        self.assertEqual(error.kind, ErrorKind.TIMEOUT)
        self.assertEqual(error.message_key, "error_network_timeout")
        self.assertTrue(error.retryable)

    def test_offline_is_retryable(self):
        error = ErrorMapper.from_network_failure(NetworkFailure(code="offline"))

        self.assertEqual(error.kind, ErrorKind.OFFLINE)
        self.assertEqual(error.tracking_code, "network_offline")
        self.assertTrue(error.retryable)

    def test_server_error_uses_http_status(self):
        error = ErrorMapper.from_network_failure(NetworkFailure(code="http", http_status=503))

        self.assertEqual(error.kind, ErrorKind.SERVER_ERROR)
        self.assertEqual(error.tracking_code, "http_503")
        self.assertTrue(error.retryable)

    def test_business_error_is_not_retryable(self):
        error = ErrorMapper.from_network_failure(NetworkFailure(code="biz_nickname_too_long"))

        self.assertEqual(error.kind, ErrorKind.BUSINESS_ERROR)
        self.assertEqual(error.message_key, "error_biz_nickname_too_long")
        self.assertFalse(error.retryable)

    def test_unknown_error_has_safe_fallback(self):
        error = ErrorMapper.from_network_failure(NetworkFailure(code="unexpected"))

        self.assertEqual(error.kind, ErrorKind.UNKNOWN)
        self.assertEqual(error.message_key, "error_unknown")
        self.assertFalse(error.retryable)


if __name__ == "__main__":
    unittest.main()
