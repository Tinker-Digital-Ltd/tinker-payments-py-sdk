"""SDK configuration and environment resolution."""

from __future__ import annotations

from dataclasses import dataclass

from . import endpoints


@dataclass(frozen=True)
class Configuration:
    api_public_key: str
    api_secret_key: str
    base_url: str
    auth_url: str

    @classmethod
    def create(
        cls,
        api_public_key: str,
        api_secret_key: str,
        base_url: str | None = None,
    ) -> "Configuration":
        resolved_base_url = base_url
        if resolved_base_url is None or not resolved_base_url.strip():
            resolved_base_url = (
                endpoints.SANDBOX_BASE_URL
                if api_public_key.startswith("pk_test_")
                or api_secret_key.startswith("sk_test_")
                else endpoints.PRODUCTION_BASE_URL
            )

        resolved_base_url = resolved_base_url.rstrip("/")
        if not resolved_base_url.endswith(endpoints.API_VERSION_PATH):
            resolved_base_url = f"{resolved_base_url}{endpoints.API_VERSION_PATH}"

        normalized_base_url = f"{resolved_base_url}/"
        auth_url = f"{resolved_base_url}{endpoints.AUTH_TOKEN_PATH}"

        return cls(
            api_public_key=api_public_key,
            api_secret_key=api_secret_key,
            base_url=normalized_base_url,
            auth_url=auth_url,
        )
