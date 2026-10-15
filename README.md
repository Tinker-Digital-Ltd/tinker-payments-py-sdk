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

## API errors

API exceptions preserve `http_status`, `error_code`, `provider_code`, `request_id`, `retry_after`, and `outcome`.
Request IDs prefer `error.request_id` over the `X-Request-ID` header. `Retry-After`
is retained as its original header string. Non-JSON HTTP failures retain status and
headers as API errors with an unknown outcome. Existing exception constructors and
legacy code/message access remain compatible.

Only an explicit `not_applied` outcome confirms no mutation. A missing outcome
remains uncertain.

## Managed recurring billing

Requires a Tinker server with the managed-billing, payment-method and payment-history
endpoints enabled. Installing the SDK does not deploy or enable those endpoints.
Existing plan-based subscription methods remain available.

Checkout uses exact integer minor-unit prices (for example, `15000` means EUR 150.00),
an explicit recurring interval (`month` or `year`), and a quantity. The SDK does not
convert prices or apply automatic discounts. Managed responses are unwrapped API
data objects/maps; payment history includes `items`, `snapshot`, `has_more` and
`next_cursor`.

| Method | Purpose |
|---|---|
| `checkout` | Create an exact-price recurring checkout |
| `billing_resource` | Read a managed billing resource |
| `change_quantity` | Change the current quantity |
| `schedule_quantity` | Schedule a quantity change |
| `clear_scheduled_quantity` | Remove a scheduled quantity change |
| `set_cancel_at_renewal` | Set cancellation at renewal; pass false to clear it |
| `billing_operation` | Recover the durable result by idempotency key |
| `payment_method_portal` | Create a short-lived hosted payment-method link |
| `billing_payment_history` | Read one page of captured payments and adjustments |

```python
from tinker import ManagedCheckout, TinkerClient
from tinker.exceptions import ApiError

payments = TinkerClient("public-key", "secret-key")
billing = payments.subscriptions()
billing.checkout(ManagedCheckout(
    external_customer_id="workspace-123", email="buyer@example.com", name="Buyer",
    currency="EUR", unit_amount=15000, quantity=3, interval="year",
    return_url="https://example.com/billing", idempotency_key="checkout-123",
))
billing.change_quantity("resource-id", 4, "quantity-123")
billing.set_cancel_at_renewal("resource-id", False, "resume-123")
billing.payment_method_portal("resource-id", "https://example.com/billing", "portal-123")
page = billing.billing_payment_history("resource-id", "", 0)
# After an uncertain command response, recover using the SAME key:
operation = billing.billing_operation("quantity-123")
# Catch ApiError and inspect error.http_status, error.outcome, etc.
```

Pass integers for minor-unit amounts, quantities and snapshots; do not convert through
floating-point prices. `ManagedCheckout` is an exported dataclass.

Use a stable, unique idempotency key for each mutation, and reuse it only with the
same payload. After a timeout, retrieve the durable result with the operation lookup
method. Missing or pending results do not prove a charge failed. Do not retry with a
new key to work around an uncertain result. Only an explicit `outcome == "not_applied"`
confirms no mutation; missing outcome remains uncertain. No automatic charge retry is
performed by these methods.

The payment-method portal updates payment details only. It cannot change quantity or
price, and paying an overdue invoice is a separate action through its hosted invoice
URL. Reuse the operation key after an uncertain response; use a new key to deliberately
open a fresh session after expiry. The server checks app ownership and requires a
managed subscription with a dedicated customer.

For payment history, start with an empty cursor and zero snapshot, then retain the
returned snapshot and pass `next_cursor` until `has_more` is false. Amounts are integer
minor units and timestamps are UTC RFC3339. The history includes captured cash payments,
tax-exclusive eligible amounts, successful refunds, and dispute principal withdrawals
and reinstatements (`reverses_id` links a reinstatement to its withdrawal).

Quarantine items with `reconciliation_reason`; commit a scan only after every page has
been verified. The snapshot is an event cutoff, not an immutable provider snapshot.
Rescan from the first page regularly and apply facts idempotently by payment/adjustment
ID. Zero-cash invoices are omitted from items while still advancing pagination. Currency
conversion and customer credits require explicit reconciliation; processing and dispute
fees are excluded from eligible principal. The SDK returns these facts without applying
credits or reconciling them automatically.

### Setup webhook acknowledgement

The dashboard sends a signed `setup.webhook_test` event with `source: "onboarding"`, `data.message`, and setup metadata. Parse it with the webhook handler, verify its signature using the application webhook secret, then acknowledge it with HTTP 200, 202, or 204. Setup events have onboarding data and do not convert to payment transactions. Event classification alone does not authenticate a request. Invalid signatures must be rejected; no payment lookup or fulfillment is needed for a valid setup test.

The signature uses HMAC-SHA256 over the JSON envelope excluding `security`, preserving envelope field order and Go JSON map ordering and escaping.

### Development checks

Install test and lint tooling with `python -m pip install '.[dev]'`. Run `ruff check .` and `python -m unittest discover -s tests -v`. CI runs both on pushes and pull requests, including the minimum supported Python version.

## Refunds, wallet withdrawals and checkout cancellation

These APIs require the merchant lifecycle backend routes under `/v1/merchant` to be deployed. SDK package releases must follow backend deployment and verified sandbox parity. Existing apps need the owner to enable withdrawal requests in app settings.

`payouts` means a withdrawal from the merchant's wallet to its own active, verified payout method. Amounts use currency units: withdrawing JPY 100 with a fee of 2 reserves 100 and pays 98. Obtain a quote and pass its `fee_amount` as `expected_fee_amount`; a fee conflict includes a refreshed quote in the structured API error. No method accepts arbitrary recipient banking details.

Supply a stable `Idempotency-Key` for every refund, payout or cancellation request. Keys are trimmed and must be 1–255 UTF-8 bytes. Reuse the same key and semantic request after transport failures; a changed request conflicts. A replay returns the original resource and fee snapshot. Start a new key for a new intended operation.

A refund's `pending_review`/`approved` state and a payout's `pending_approval`/`approved` state mean review is outstanding. Only `refunded`, `paid` or provider-confirmed `cancelled` establishes completion. Preserve cancellation `outcome_unknown` and poll by ID; do not blindly submit another request. Unsupported cancellation raises HTTP 422 `CHECKOUT_CANCELLATION_UNSUPPORTED` and retains the persisted `request_id`/`status` in error details. Lifecycle conflicts use HTTP 409; replaying a persisted rejection retains its 422/409 result.

Refund history includes refundable amounts and `refund_capability`. Cancellation history includes `capability`, the newest 100 requests and `has_more`; retrieve older known requests by ID. Payout listing accepts `page`, `per_page` (maximum 100), `status` and `currency`. Reads are scoped to the app; payout reads show only requests attributed to that app.

The signed events `refund.updated.v1`, `withdrawal.updated.v1` and `checkout.cancellation.updated.v1` have source `payment` and typed `data.resource`. Verify its signature before using its typed cancellation data. It never converts to a payment transaction. Events can arrive late or more than once; polling remains available.

```python
tx = client.transactions()
review = tx.refund(payment_id, {"reason": "requested_by_customer", "amount": 100}, "refund-order-42")
print(review["refund"]["status"])
payouts = client.payouts()
destinations = payouts.methods()
destination = next(method for method in destinations if method["status"] == "active" and method["is_verified"])
quote = payouts.quote({"payout_method_id": destination["id"], "amount": 100, "currency": destination["currency"]})
requested = payouts.request_payout({"payout_method_id": destination["id"], "amount": 100, "currency": destination["currency"], "expected_fee_amount": quote["fee_amount"]}, "withdrawal-42")
print(payouts.get(requested["withdrawal"]["id"])["status"])
try:
    result = tx.cancel_checkout(unpaid_payment_id, {"reason": "Customer left checkout"}, "cancel-order-42")
    print(tx.get_cancellation(unpaid_payment_id, result["cancellation"]["id"])["status"])
except ApiError as error:  # from tinker.exceptions import ApiError
    print(error.error_code, error.details)
```

`transactions()` also exposes `refunds`, `get_refund` and `cancellations`; `payouts().list()` accepts typed pagination filters. The public `tinker.lifecycle` module provides TypedDict request/result/resource schemas and Literal status/reason types. Client stubs expose the new manager; `ApiError.details` retains the complete response envelope and nested `error.details`.
