from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ErrorKind(str, Enum):
    TIMEOUT = "timeout"
    OFFLINE = "offline"
    SERVER_ERROR = "server_error"
    BUSINESS_ERROR = "business_error"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class NetworkFailure:
    code: str
    http_status: int | None = None
    message: str = ""


@dataclass(frozen=True)
class AppError:
    kind: ErrorKind
    message_key: str
    tracking_code: str
    retryable: bool


class ErrorMapper:
    @staticmethod
    def from_network_failure(failure: NetworkFailure) -> AppError:
        if failure.code == "timeout":
            return AppError(
                kind=ErrorKind.TIMEOUT,
                message_key="error_network_timeout",
                tracking_code="network_timeout",
                retryable=True,
            )
        if failure.code == "offline":
            return AppError(
                kind=ErrorKind.OFFLINE,
                message_key="error_network_offline",
                tracking_code="network_offline",
                retryable=True,
            )
        if failure.http_status and failure.http_status >= 500:
            return AppError(
                kind=ErrorKind.SERVER_ERROR,
                message_key="error_server_busy",
                tracking_code=f"http_{failure.http_status}",
                retryable=True,
            )
        if failure.code.startswith("biz_"):
            return AppError(
                kind=ErrorKind.BUSINESS_ERROR,
                message_key=f"error_{failure.code}",
                tracking_code=failure.code,
                retryable=False,
            )
        return AppError(
            kind=ErrorKind.UNKNOWN,
            message_key="error_unknown",
            tracking_code="unknown",
            retryable=False,
        )
