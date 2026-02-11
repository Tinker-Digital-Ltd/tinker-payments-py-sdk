"""Authentication manager for token fetching/caching."""

from __future__ import annotations

import base64
import time
from typing import Any

from .configuration import Configuration
from .exceptions import ApiError, NetworkError
from .models import ApiMeta

try:
    import requests
except ModuleNotFoundError:  # pragma: no cover
    requests = None


class AuthenticationManager:
    def __init__(self, config: Configuration, session: Any | None = None) -> None:
        self._config = config
        if session is not None:
            self._session = session
        elif requests is not None:
            self._session = requests.Session()
        else:
            raise NetworkError("requests is required unless a custom session is provided")
        self._token: str | None = None
        self._expires_at: int | None = None
        self._last_meta: ApiMeta | None = None

    def get_token(self) -> str:
        if self._is_token_valid():
            return self._token or ""
        return self._fetch_token()

    def get_last_meta(self) -> ApiMeta | None:
        return self._last_meta

    def _is_token_valid(self) -> bool:
        if self._token is None or self._expires_at is None:
            return False
        return int(time.time()) < self._expires_at - 60

    def _fetch_token(self) -> str:
        credentials = base64.b64encode(
            f"{self._config.api_public_key}:{self._config.api_secret_key}".encode("utf-8")
        ).decode("utf-8")

        try:
            response = self._session.post(
                self._config.auth_url,
                data={"credentials": credentials},
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                },
                timeout=30,
            )
            result = response.json() if response.text else {}
            auth_data = self._extract_auth_data(result)

            if response.status_code >= 400:
                raise ApiError(self._extract_error_message(result))

            token = auth_data.get("token")
            if not token:
                raise ApiError("Invalid authentication response: token missing")

            self._token = str(token)
            expires_in = int(auth_data.get("expires_in", 3600))
            self._expires_at = int(time.time()) + expires_in
            return self._token
        except ApiError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise NetworkError(f"Failed to authenticate: {exc}") from exc

    def _extract_auth_data(self, result: Any) -> dict[str, Any]:
        if isinstance(result, dict) and "success" in result:
            self._last_meta = ApiMeta.from_dict(result.get("meta") if isinstance(result.get("meta"), dict) else {})

            if result.get("success") is False:
                raise ApiError(self._extract_error_message(result))

            data = result.get("data", {})
            return data if isinstance(data, dict) else {}

        return result if isinstance(result, dict) else {}

    def _extract_error_message(self, result: Any) -> str:
        if isinstance(result, dict):
            if isinstance(result.get("error"), dict):
                error = result["error"]
                return str(error.get("message") or error.get("code") or "Authentication failed")

            if "message" in result:
                return str(result["message"])

        return "Authentication failed"
