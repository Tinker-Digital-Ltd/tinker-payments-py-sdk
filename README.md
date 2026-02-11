# Tinker Payments Python SDK

Python SDK for the standardized Tinker Payments API (`/v1`) with auth token management, sandbox/production routing, payment initiate/query, subscription endpoints, and webhook verification.

## Installation

```bash
pip install tinker-payments
```

## Quick Start

```python
from tinker import TinkerClient

client = TinkerClient("pk_test_xxx", "sk_test_xxx")

payment = client.transactions().initiate(
    {
        "amount": 1200,
        "currency": "KES",
        "gateway": "mpesa",
        "merchantReference": "ORDER-1001",
        "returnUrl": "https://merchant.example/callback",
    }
)

result = client.transactions().query(
    {
        "reference": "TP-REF-123",
        "gateway": "mpesa",
    }
)
```

## Environment Resolution

- Uses `https://sandbox-api.tinkerpayments.com/v1/` when keys start with `pk_test_` or `sk_test_`.
- Uses `https://api.tinkerpayments.com/v1/` for live keys.
- Override with `TinkerClient(pk, sk, base_url="https://custom-host/v1")`.

## Standard API Envelope

All standardized endpoints are expected to return:

```json
{
  "success": true,
  "data": {},
  "error": null,
  "meta": {
    "request_id": "5b5b3526-8dc1-4f7b-9bb8-cdbfc8df4984",
    "timestamp": "2026-02-11T22:52:45Z",
    "environment": "production"
  }
}
```

The latest auth envelope metadata is available through `client.get_last_auth_meta()`.

## Subscriptions

```python
subs = client.subscriptions()

subs.create_plan(
    {
        "name": "Pro",
        "amount": 1000,
        "currency": "KES",
        "intervals": ["monthly"],
        "description": "Pro plan",
        "is_active": True,
    }
)

subs.list_plans()
subs.create(
    {
        "plan_id": "plan_123",
        "gateway": "stripe",
        "customer": {
            "external_customer_id": "cust_123",
            "email": "customer@example.com",
        },
    }
)
subs.list(plan_id="plan_123", external_customer_id="cust_123")
subs.cancel("sub_123")
```

## Webhooks

```python
event = client.webhooks().handle(raw_body)

if not client.webhooks().verify_signature(event, "whsec_..."):
    raise ValueError("Invalid webhook signature")
```

Signature verification uses HMAC-SHA256 over a JSON object containing `id`, `type`, `source`, `timestamp`, `data`, and `meta`.
