import unittest

from ai_refactor.app_error import ErrorKind, NetworkFailure
from ai_refactor.network_client import FakeNetworkClient, NetworkResult
from ai_refactor.view_models import ProfileViewModel, SettingsViewModel


class ProfileViewModelTest(unittest.TestCase):
    def test_load_success_uses_profile_name(self):
        client = FakeNetworkClient(NetworkResult(payload={"name": "Ada"}))

        state = ProfileViewModel(client).load()

        self.assertFalse(state.loading)
        self.assertEqual(state.title, "Ada")
        self.assertIsNone(state.error)
        self.assertEqual(client.calls, 1)

    def test_timeout_returns_retryable_error_state(self):
        client = FakeNetworkClient(NetworkResult(failure=NetworkFailure(code="timeout")))

        state = ProfileViewModel(client).load()

        self.assertFalse(state.loading)
        self.assertEqual(state.title, "Profile")
        self.assertEqual(state.error.kind, ErrorKind.TIMEOUT)
        self.assertTrue(state.error.retryable)


class SettingsViewModelTest(unittest.TestCase):
    def test_load_success_uses_settings_title(self):
        client = FakeNetworkClient(NetworkResult(payload={"title": "Preferences"}))

        state = SettingsViewModel(client).load()

        self.assertFalse(state.loading)
        self.assertEqual(state.title, "Preferences")
        self.assertIsNone(state.error)

    def test_business_error_returns_non_retryable_error_state(self):
        client = FakeNetworkClient(
            NetworkResult(failure=NetworkFailure(code="biz_settings_locked"))
        )

        state = SettingsViewModel(client).load()

        self.assertFalse(state.loading)
        self.assertEqual(state.title, "Settings")
        self.assertEqual(state.error.kind, ErrorKind.BUSINESS_ERROR)
        self.assertFalse(state.error.retryable)


if __name__ == "__main__":
    unittest.main()
