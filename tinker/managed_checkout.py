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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
