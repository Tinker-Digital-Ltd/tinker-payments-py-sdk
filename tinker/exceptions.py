"""SDK exception types."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class TinkerError(Exception):
    """Base SDK exception."""


class ApiError(TinkerError):
    """API failure. Only outcome == 'not_applied' confirms no mutation."""

    def __init__(
        self,
        message: str,
        *,
        http_status: int | None = None,
        details: Any = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.http_status = http_status
        self.details = details
        error = details.get("error") if isinstance(details, dict) else None
        error = error if isinstance(error, dict) else {}
        headers = {str(k).lower(): v for k, v in (headers or {}).items()}
        self.error_code = error.get("code")
        self.provider_code = error.get("provider_code")
        self.request_id = error.get("request_id") or headers.get("x-request-id")
        self.retry_after = headers.get("retry-after")
        self.outcome = error.get("outcome")


class NetworkError(TinkerError):
    """Raised when request transport fails."""


class InvalidPayloadError(TinkerError):
    """Raised when payload parsing or shape validation fails."""
