"""Shared lifecycle request validation and encoding."""

import math
from urllib.parse import quote


def idempotency_headers(key: str) -> dict[str, str]:
    normalized = key.strip()
    if not normalized or len(normalized.encode("utf-8")) > 255:
        raise ValueError("Idempotency-Key must contain 1 to 255 UTF-8 bytes")
    return {"Idempotency-Key": normalized}


def positive_amount(amount: float) -> None:
    if not math.isfinite(amount) or amount <= 0:
        raise ValueError("amount must be finite and positive")


def payment_path(payment_id: str) -> str:
    return "merchant/payment/" + quote(payment_id, safe="")
