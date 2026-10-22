# Tinker Payments Python SDK

Python 3.9+ SDK with automatic authentication, payments, subscriptions and signed webhooks. Keep secret keys on the server.

## Installation

```bash
pip install tinker-payments
```

## Quick Start

```python
from tinker import TinkerClient
from tinker.exceptions import ApiError

client = TinkerClient("pk_test_xxx", "sk_test_xxx")

payment = client.transactions().initiate(
    {
        "amount": 1200,
        "currency": "KES",
        "gateway": "mpesa",
        "merchantReference": "ORDER-1001",
        "returnUrl": "https://merchant.example/payment/return",
        "customerPhone": "+254712345678",
    }
)

result = client.transactions().query(
    {
        "reference": "TP-REF-123",
        "gateway": "mpesa",
    }
)
```

Payments use currency units. Mpesa requires `customerPhone`; `returnUrl` is the browser destination, while webhooks are configured in the dashboard.

## Configuration

Test key prefixes (`pk_test_` or `sk_test_`) select `https://sandbox-api.tinkerpayments.com/v1/`; other keys select `https://api.tinkerpayments.com/v1/`. Override with `TinkerClient(pk, sk, base_url="https://custom-host/v1")`; pass `session=` for a requests-compatible transport.

## Plan subscriptions

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

## Managed recurring billing

Checkout uses exact integer minor-unit prices (`15000` = EUR 150.00), a `month` or `year` interval, and a quantity. The SDK does not convert prices or apply discounts. Responses are unwrapped data maps/objects.

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
from tinker import ManagedCheckout

billing = client.subscriptions()
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
```

Pass integers for minor-unit amounts, quantities and snapshots; do not convert through
floating-point prices. `ManagedCheckout` is an exported dataclass.

### Trials with a required payment method

Set `trial_days` (1 to 30) to collect a card at checkout and charge first when the trial ends. The SDK sends `trial_days` only when it is above 0, so checkouts without a trial keep working against servers released before trial support. A gateway without trial support returns HTTP 422 `TRIAL_UNSUPPORTED` with `outcome: not_applied`. Limiting a customer to one trial is the app's responsibility.

```python
billing.checkout(ManagedCheckout(
    external_customer_id="workspace-123", email="buyer@example.com", name="Buyer",
    currency="EUR", unit_amount=15000, quantity=3, interval="year",
    return_url="https://example.com/billing", idempotency_key="checkout-456",
    trial_days=14,
))
```

Checkout and billing resource responses include a provider-neutral `managed_state` map: `status` (`pending`, `trialing`, `active`, `past_due`, `paused` or `canceled`), `trial_ends_at`, `current_period_end` and `cancel_at_period_end`. Read it instead of raw provider fields; grant access while `status` is `trialing` or `active` and `current_period_end` is in the future. Managed subscription webhooks carry `billing_status` and `trial_ends_at`, and `subscription.trial_will_end` arrives up to three days before the trial ends. The trial's €0 invoice sends `invoice.paid` with amount 0 and is not a payment.

Use a stable key per mutation and reuse it with the same payload after a lost response. Recover through the operation lookup; missing or pending results remain uncertain. Only an explicit `outcome` of `not_applied` confirms no mutation.

The payment-method portal changes payment details only; quantity, price and overdue invoice payment are separate actions. It requires an app-owned managed subscription with a dedicated customer. Reuse the operation key after a lost response and use a new key for a deliberately new session after expiry.

For payment history, keep the returned `snapshot` across `next_cursor` pages until `has_more` is false. Amounts are integer minor units and timestamps are UTC RFC3339. History covers captured cash, tax-exclusive eligible amounts, refunds, and dispute principal withdrawals/reinstatements (`reverses_id` identifies the reversed withdrawal).

Quarantine items with `reconciliation_reason` and verify every page before committing a scan. The snapshot is an event cutoff, not an immutable provider snapshot: rescan from the first page to discover later adjustments, then apply facts idempotently by payment/adjustment ID. Zero-cash invoices advance pagination without an item. Processing/dispute fees are excluded from eligible principal; currency conversion and customer credits need explicit reconciliation.

## Refunds, wallet withdrawals and checkout cancellation

The app owner must enable withdrawal requests in app settings. A payout is a withdrawal from the merchant's wallet to its own active, verified payout method. Amounts use currency units: withdrawing JPY 100 with a fee of 2 reserves 100 and pays 98. Obtain a quote and pass its `fee_amount` as `expected_fee_amount`; a fee conflict includes a refreshed quote in the structured API error. No method accepts arbitrary recipient banking details.

Supply a stable `Idempotency-Key` for every refund, payout or cancellation request. Keys are trimmed and must be 1–255 UTF-8 bytes. Reuse the same key and semantic request after transport failures; a changed request conflicts. A replay returns the original resource and fee snapshot. Start a new key for a new intended operation.

A refund's `pending_review`/`approved` state and a payout's `pending_approval`/`approved` state are not completion. Only `refunded`, `paid` or provider-confirmed `cancelled` establishes completion. Preserve cancellation `outcome_unknown` and poll by ID; do not blindly submit another request. Unsupported cancellation raises HTTP 422 `CHECKOUT_CANCELLATION_UNSUPPORTED` and retains the persisted `request_id`/`status` in error details. Lifecycle conflicts use HTTP 409; replaying a persisted rejection retains its 422/409 result.

Refund history includes refundable amounts and `refund_capability`. Cancellation history includes `capability`, the newest 100 requests and `has_more`; retrieve older known requests by ID. Payout listing accepts `page`, `per_page` (maximum 100), `status` and `currency`. Reads are scoped to the app; payout reads show only requests attributed to that app.

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

Cancellation resources expose `payment_conflict` when later successful payment evidence conflicts with expiry. Treat successful payment as authoritative and use the refund workflow where appropriate.

## Webhooks

```python
event = client.webhooks().handle(raw_body)
if not client.webhooks().verify_signature(event, webhook_secret):
    raise ValueError("Invalid webhook signature")
transaction = event.to_transaction()  # None for setup/lifecycle events
```

Verify the signature before consuming fields or converting the event to a transaction; reuse the parsed event rather than reading the request body twice. Deduplicate by event ID. The SDK verifies HMAC-SHA256 over the envelope excluding `security`, using the server's field order, map ordering and escaping.

After verification, acknowledge `setup.webhook_test` (`source: onboarding`) with HTTP 200, 202 or 204; it needs no payment lookup or fulfillment. The signed lifecycle events `refund.updated.v1`, `withdrawal.updated.v1` and `checkout.cancellation.updated.v1` carry `data.resource` with `source: payment`. Their typed resources never convert into payment transactions. Poll request IDs if delivery is delayed.

## Errors and response metadata

API errors retain `http_status`, `error_code`, `provider_code`, `request_id`, `retry_after`, `outcome` and the full envelope in `details`. Request IDs prefer the response body over `X-Request-ID`; `Retry-After` remains its original string. Non-JSON HTTP failures retain status/headers and an uncertain outcome. Only an explicit `not_applied` outcome confirms no mutation. Managers unwrap response `data`; use `get_last_meta()` for request metadata and `client.get_last_auth_meta()` for authentication metadata.

```python
try:
    client.transactions().query({"reference": "TP-REF-123", "gateway": "mpesa"})
except ApiError as error:
    print(error.error_code, error.details)
```

## Development

```sh
python -m pip install -e '.[dev]'
ruff check .
python -m unittest discover -s tests -v
```
