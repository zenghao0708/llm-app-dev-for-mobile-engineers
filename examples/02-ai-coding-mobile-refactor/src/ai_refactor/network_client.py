from __future__ import annotations

from dataclasses import dataclass

from ai_refactor.app_error import NetworkFailure


@dataclass(frozen=True)
class NetworkResult:
    payload: dict[str, str] | None = None
    failure: NetworkFailure | None = None

    @property
    def ok(self) -> bool:
        return self.failure is None


class FakeNetworkClient:
    def __init__(self, result: NetworkResult) -> None:
        self._result = result
        self.calls = 0

    def get(self, path: str) -> NetworkResult:
        if not path.startswith("/"):
            raise ValueError("path must start with /")
        self.calls += 1
        return self._result
