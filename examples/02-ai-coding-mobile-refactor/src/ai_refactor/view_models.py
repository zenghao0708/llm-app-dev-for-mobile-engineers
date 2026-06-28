from __future__ import annotations

from dataclasses import dataclass

from ai_refactor.app_error import AppError, ErrorMapper
from ai_refactor.network_client import FakeNetworkClient


@dataclass(frozen=True)
class ScreenState:
    loading: bool
    title: str
    error: AppError | None = None


class ProfileViewModel:
    def __init__(self, client: FakeNetworkClient) -> None:
        self._client = client

    def load(self) -> ScreenState:
        result = self._client.get("/profile")
        if result.ok:
            return ScreenState(loading=False, title=result.payload.get("name", "Profile"))
        return ScreenState(
            loading=False,
            title="Profile",
            error=ErrorMapper.from_network_failure(result.failure),
        )


class SettingsViewModel:
    def __init__(self, client: FakeNetworkClient) -> None:
        self._client = client

    def load(self) -> ScreenState:
        result = self._client.get("/settings")
        if result.ok:
            return ScreenState(loading=False, title=result.payload.get("title", "Settings"))
        return ScreenState(
            loading=False,
            title="Settings",
            error=ErrorMapper.from_network_failure(result.failure),
        )
