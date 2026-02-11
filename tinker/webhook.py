"""Webhook parsing and signature verification helpers."""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Any

from .exceptions import InvalidPayloadError
from .models import Transaction


@dataclass(frozen=True)
class WebhookSecurity:
    signature: str = ""
    algorithm: str = "HMAC-SHA256"


@dataclass(frozen=True)
class WebhookMeta:
    version: str = "1.0"
    app_id: str = ""
    gateway: str | None = None


@dataclass(frozen=True)
class PaymentEventData:
    id: str
    status: str
    reference: str
    amount: float
    currency: str
    channel: str
    created_at: str
    paid_at: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PaymentEventData":
        return cls(
            id=str(data.get("id", "")),
            status=str(data.get("status", "pending")),
            reference=str(data.get("reference", "")),
            amount=float(data.get("amount", 0)),
            currency=str(data.get("currency", "")),
            channel=str(data.get("channel", "")),
            created_at=str(data.get("created_at", "")),
            paid_at=str(data["paid_at"]) if data.get("paid_at") is not None else None,
        )


@dataclass(frozen=True)
class SubscriptionEventData:
    id: str
    status: str
    plan_id: str
    account_id: str
    current_period_start: str | None
    current_period_end: str | None
    created_at: str
    cancelled_at: str | None
    paused_at: str | None
    reactivated_at: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SubscriptionEventData":
        current_start = data.get("current_period_start")
        return cls(
            id=str(data.get("subscription_id", data.get("id", ""))),
            status=str(data.get("status", "")),
            plan_id=str(data.get("plan_id", "")),
            account_id=str(data.get("account_id", data.get("customer_id", ""))),
            current_period_start=str(current_start) if current_start is not None else None,
            current_period_end=(
                str(data["current_period_end"]) if data.get("current_period_end") is not None else None
            ),
            created_at=str(data.get("created_at") or current_start or ""),
            cancelled_at=str(data["cancelled_at"]) if data.get("cancelled_at") is not None else None,
            paused_at=str(data["paused_at"]) if data.get("paused_at") is not None else None,
            reactivated_at=str(data["reactivated_at"]) if data.get("reactivated_at") is not None else None,
        )


@dataclass(frozen=True)
class InvoiceEventData:
    id: str
    status: str
    invoice_number: str
    amount: float
    currency: str
    subscription_id: str
    created_at: str
    paid_at: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InvoiceEventData":
        return cls(
            id=str(data.get("invoice_id", data.get("id", ""))),
            status=str(data.get("status", "")),
            invoice_number=str(data.get("invoice_number", "")),
            amount=float(data.get("amount", 0)),
            currency=str(data.get("currency", "")),
            subscription_id=str(data.get("subscription_id", "")),
            created_at=str(data.get("created_at", "")),
            paid_at=str(data["paid_at"]) if data.get("paid_at") is not None else None,
        )


@dataclass(frozen=True)
class SettlementEventData:
    id: str
    status: str
    amount: float
    net_amount: float | None
    currency: str
    settlement_date: str
    created_at: str
    processed_at: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SettlementEventData":
        return cls(
            id=str(data.get("settlement_id", data.get("id", ""))),
            status=str(data.get("status", "")),
            amount=float(data.get("amount", 0)),
            net_amount=float(data["net_amount"]) if data.get("net_amount") is not None else None,
            currency=str(data.get("currency", "")),
            settlement_date=str(data.get("settlement_date", "")),
            created_at=str(data.get("created_at", "")),
            processed_at=str(data["processed_at"]) if data.get("processed_at") is not None else None,
        )


@dataclass(frozen=True)
class WebhookEvent:
    id: str
    type: str
    source: str
    timestamp: str
    data: PaymentEventData | SubscriptionEventData | InvoiceEventData | SettlementEventData
    meta: WebhookMeta
    security: WebhookSecurity
    raw_data: dict[str, Any]
    raw_meta: dict[str, Any]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "WebhookEvent":
        source = str(payload.get("source", ""))
        raw_data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        raw_meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}

        if source == "payment":
            event_data = PaymentEventData.from_dict(raw_data)
        elif source == "subscription":
            event_data = SubscriptionEventData.from_dict(raw_data)
        elif source == "invoice":
            event_data = InvoiceEventData.from_dict(raw_data)
        elif source == "settlement":
            event_data = SettlementEventData.from_dict(raw_data)
        else:
            raise InvalidPayloadError(f"Unknown webhook source: {source}")

        security_input = payload.get("security") if isinstance(payload.get("security"), dict) else {}

        return cls(
            id=str(payload.get("id", "")),
            type=str(payload.get("type", "")),
            source=source,
            timestamp=str(payload.get("timestamp", "")),
            data=event_data,
            meta=WebhookMeta(
                version=str(raw_meta.get("version", "1.0")),
                app_id=str(raw_meta.get("app_id", "")),
                gateway=str(raw_meta["gateway"]) if raw_meta.get("gateway") is not None else None,
            ),
            security=WebhookSecurity(
                signature=str(security_input.get("signature", "")),
                algorithm=str(security_input.get("algorithm", "HMAC-SHA256")),
            ),
            raw_data=raw_data,
            raw_meta=raw_meta,
        )

    def to_transaction(self) -> Transaction | None:
        if self.source != "payment":
            return None

        return Transaction.from_dict(
            {
                "id": self.data.id,
                "status": self.data.status,
                "reference": self.data.reference,
                "amount": self.data.amount,
                "currency": self.data.currency,
                "channel": self.data.channel,
                "created_at": self.data.created_at,
                "paid_at": self.data.paid_at,
            }
        )


class WebhookHandler:
    def handle(self, payload: str | dict[str, Any]) -> WebhookEvent:
        if isinstance(payload, str):
            try:
                data = json.loads(payload)
            except json.JSONDecodeError as exc:
                raise InvalidPayloadError(f"Invalid JSON payload: {exc}") from exc
        else:
            data = payload

        if not isinstance(data, dict):
            raise InvalidPayloadError("Webhook payload must be an object")

        return WebhookEvent.from_dict(data)

    def handle_as_transaction(self, payload: str | dict[str, Any]) -> Transaction | None:
        event = self.handle(payload)
        return event.to_transaction()

    def verify_signature(
        self,
        payload: WebhookEvent | str | dict[str, Any],
        webhook_secret: str,
    ) -> bool:
        if not webhook_secret:
            return False

        event = payload if isinstance(payload, WebhookEvent) else self.handle(payload)
        signature = event.security.signature
        if not signature.startswith("sha256="):
            return False

        payload_without_security = {
            "id": event.id,
            "type": event.type,
            "source": event.source,
            "timestamp": event.timestamp,
            "data": event.raw_data,
            "meta": event.raw_meta,
        }

        encoded = json.dumps(payload_without_security, separators=(",", ":"), ensure_ascii=False)
        computed = "sha256=" + hmac.new(
            webhook_secret.encode("utf-8"),
            encoded.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(signature, computed)
