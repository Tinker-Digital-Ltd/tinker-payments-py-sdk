"""Exact-price managed recurring checkout request."""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ManagedCheckout:
    external_customer_id: str
    email: str
    name: str
    currency: str
    unit_amount: int
    quantity: int
    interval: str
    return_url: str
    idempotency_key: str
    trial_days: int = 0

    def to_dict(self) -> dict[str, Any]:
        body = asdict(self)
        if self.trial_days <= 0:
            del body["trial_days"]
        return body
