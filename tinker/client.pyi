from typing import Any

from .api import PayoutManager, SubscriptionManager, TransactionManager
from .configuration import Configuration
from .models import ApiMeta
from .webhook import WebhookHandler

class TinkerClient:
    @property
    def config(self) -> Configuration: ...
    def __init__(
        self,
        api_public_key: str,
        api_secret_key: str,
        base_url: str | None = None,
        session: Any | None = None,
    ) -> None: ...
    def transactions(self) -> TransactionManager: ...
    def subscriptions(self) -> SubscriptionManager: ...
    def payouts(self) -> PayoutManager: ...
    def webhooks(self) -> WebhookHandler: ...
    def get_last_auth_meta(self) -> ApiMeta | None: ...

TinkerPayments = TinkerClient
