"""Public SDK client."""

from __future__ import annotations

from typing import Any

from .api import SubscriptionManager, TransactionManager
from .auth import AuthenticationManager
from .configuration import Configuration
from .models import ApiMeta
from .webhook import WebhookHandler

try:
    import requests
except ModuleNotFoundError:  # pragma: no cover
    requests = None


class TinkerClient:
    def __init__(
        self,
        api_public_key: str,
        api_secret_key: str,
        base_url: str | None = None,
        session: Any | None = None,
    ) -> None:
        self._config = Configuration.create(api_public_key, api_secret_key, base_url)
        if session is not None:
            self._session = session
        elif requests is not None:
            self._session = requests.Session()
        else:
            raise RuntimeError("requests is required unless a custom session is provided")
        self._auth_manager = AuthenticationManager(self._config, self._session)
        self._transactions: TransactionManager | None = None
        self._subscriptions: SubscriptionManager | None = None
        self._webhooks: WebhookHandler | None = None

    @property
    def config(self) -> Configuration:
        return self._config

    def transactions(self) -> TransactionManager:
        if self._transactions is None:
            self._transactions = TransactionManager(self._config, self._auth_manager, self._session)
        return self._transactions

    def subscriptions(self) -> SubscriptionManager:
        if self._subscriptions is None:
            self._subscriptions = SubscriptionManager(self._config, self._auth_manager, self._session)
        return self._subscriptions

    def webhooks(self) -> WebhookHandler:
        if self._webhooks is None:
            self._webhooks = WebhookHandler()
        return self._webhooks

    def get_last_auth_meta(self) -> ApiMeta | None:
        return self._auth_manager.get_last_meta()


TinkerPayments = TinkerClient
