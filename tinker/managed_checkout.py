"""Exact-price managed recurring checkout request."""

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Optional


def unix_seconds(moment: datetime) -> int:
    if moment.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return int(moment.timestamp())


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
    trial_end: Optional[datetime] = None

    def to_dict(self) -> dict[str, Any]:
        body = asdict(self)
        if self.trial_days <= 0:
            del body["trial_days"]
        if self.trial_end is None:
            del body["trial_end"]
        else:
            body["trial_end"] = unix_seconds(self.trial_end)
        return body
