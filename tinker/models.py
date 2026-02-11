"""Core SDK response models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ApiMeta:
    request_id: str | None = None
    timestamp: str | None = None
    environment: str | None = None

    @classmethod
    def from_dict(cls, meta: dict[str, Any] | None) -> "ApiMeta":
        meta = meta or {}
        return cls(
            request_id=str(meta["request_id"]) if "request_id" in meta else None,
            timestamp=str(meta["timestamp"]) if "timestamp" in meta else None,
            environment=str(meta["environment"]) if "environment" in meta else None,
        )


@dataclass
class Transaction:
    status: str
    initiation_data: dict[str, Any] | None = None
    query_data: dict[str, Any] | None = None
    callback_data: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "Transaction":
        data = data or {}
        has_initiation_ref = (
            ("paymentReference" in data or "payment_reference" in data) and "id" not in data
        )
        has_query_shape = "id" in data and "reference" in data

        if has_initiation_ref:
            return cls(status=str(data.get("status", "pending")), initiation_data=data)

        if has_query_shape:
            return cls(
                status=str(data.get("status", "pending")),
                query_data=data,
                callback_data=data,
            )

        return cls(status=str(data.get("status", "pending")))

    def is_successful(self) -> bool:
        return self.status == "success"

    def is_pending(self) -> bool:
        return self.status == "pending"

    def is_cancelled(self) -> bool:
        return self.status == "cancelled"

    def is_failed(self) -> bool:
        return self.status == "failed"
