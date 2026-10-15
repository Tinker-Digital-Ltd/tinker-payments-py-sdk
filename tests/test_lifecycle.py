import json
import os
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from test_managed_billing import BillingSession

from tinker import TinkerClient
from tinker.exceptions import ApiError

FIXTURE = Path(
    os.environ.get(
        "TINKER_LIFECYCLE_FIXTURE",
        Path(__file__).parents[2]
        / "tinker-payments-openapi/fixtures/merchant-lifecycle.json",
    )
)
CONTRACT = json.loads(
    (Path(__file__).parent / "fixtures/merchant-lifecycle.json").read_text()
)
if FIXTURE.exists():
    assert CONTRACT == json.loads(FIXTURE.read_text()), (
        "Shared fixture snapshot drifted"
    )


class LifecycleTests(unittest.TestCase):
    def test_all_shared_operations(self):
        for row in CONTRACT["cases"]:
            with self.subTest(operation=row["operation"]):
                session = BillingSession(row["status"], row["response"])
                client = TinkerClient("public", "secret", session=session)
                tx, payouts = client.transactions(), client.payouts()
                operations = {
                    "refund": lambda tx=tx, payouts=payouts, row=row: tx.refund(
                        "payment/a b", row["body"], " stable-key "
                    ),
                    "refunds": lambda tx=tx, payouts=payouts, row=row: tx.refunds(
                        "payment/a b"
                    ),
                    "get_refund": lambda tx=tx, payouts=payouts, row=row: tx.get_refund(
                        "payment/a b", "refund/a b"
                    ),
                    "payout_methods": payouts.methods,
                    "payout_quote": lambda tx=tx, payouts=payouts, row=row: (
                        payouts.quote(
                            {
                                "payout_method_id": "method/a &b",
                                "amount": 100,
                                "currency": "JPY",
                            }
                        )
                    ),
                    "request_payout": lambda tx=tx, payouts=payouts, row=row: (
                        payouts.request_payout(row["body"], "stable-key")
                    ),
                    "payouts": lambda tx=tx, payouts=payouts, row=row: payouts.list(
                        {
                            "page": 2,
                            "per_page": 10,
                            "status": "pending_approval",
                            "currency": "JPY",
                        }
                    ),
                    "get_payout": lambda tx=tx, payouts=payouts, row=row: payouts.get(
                        "payout/a b"
                    ),
                    "cancel_checkout": lambda tx=tx, payouts=payouts, row=row: (
                        tx.cancel_checkout("payment/a b", row["body"], "stable-key")
                    ),
                    "cancellations": lambda tx=tx, payouts=payouts, row=row: (
                        tx.cancellations("payment/a b")
                    ),
                    "get_cancellation": lambda tx=tx, payouts=payouts, row=row: (
                        tx.get_cancellation("payment/a b", "cancel/a b")
                    ),
                }
                self.assertEqual(
                    operations[row["operation"]](), row["response"]["data"]
                )
                calls = [
                    call
                    for call in session.calls
                    if not call[1].endswith("/auth/token")
                ]
                self.assertEqual(len(calls), 1)
                method, url, body, headers = calls[0]
                actual, expected = (
                    urlsplit(url),
                    urlsplit("https://example.test/v1/" + row["path"]),
                )
                self.assertEqual(actual.path, expected.path)
                self.assertEqual(parse_qs(actual.query), parse_qs(expected.query))
                self.assertEqual(method, row["method"])
                self.assertEqual(body, row["body"])
                self.assertEqual(headers["Authorization"], "Bearer abc123")
                self.assertEqual(
                    headers.get("Idempotency-Key"),
                    row["headers"].get("Idempotency-Key"),
                )

    def test_structured_errors(self):
        for row in CONTRACT["errors"]:
            client = TinkerClient(
                "public",
                "secret",
                session=BillingSession(row["status"], row["response"]),
            )
            with self.assertRaises(ApiError) as raised:
                client.transactions().cancel_checkout(
                    "payment", {"reason": "stop"}, "key"
                )
            self.assertEqual(raised.exception.http_status, row["status"])
            self.assertEqual(
                raised.exception.error_code, row["response"]["error"]["code"]
            )
            self.assertEqual(raised.exception.details, row["response"])

    def test_invalid_values_do_not_send(self):
        session = BillingSession()
        client = TinkerClient("public", "secret", session=session)
        for key in ["", " ", "é" * 128]:
            with self.assertRaises(ValueError):
                client.transactions().cancel_checkout(
                    "payment", {"reason": "stop"}, key
                )
        for amount in [float("nan"), float("inf"), 0, -1]:
            with self.assertRaises(ValueError):
                client.payouts().quote({"payout_method_id": "method", "amount": amount})
        self.assertEqual(session.calls, [])


class CancellationWebhookTests(unittest.TestCase):
    def test_signed_event_does_not_create_a_payment(self):
        from tinker.webhook import CheckoutCancellationEventData

        path = Path(__file__).parent / "fixtures/checkout-cancellation-webhook.json"
        raw = path.read_text()
        canonical = (
            Path(__file__).parents[2]
            / "tinker-payments-openapi/fixtures/checkout-cancellation-webhook.json"
        )
        if canonical.exists():
            self.assertEqual(json.loads(raw), json.loads(canonical.read_text()))
        handler = TinkerClient("public", "secret", session=BillingSession()).webhooks()
        event = handler.handle(raw)
        self.assertTrue(event.is_checkout_cancellation())
        self.assertIsInstance(event.data, CheckoutCancellationEventData)
        self.assertEqual(event.data.cancellation["status"], "outcome_unknown")
        self.assertIsNone(event.to_transaction())
        self.assertTrue(handler.verify_signature(event, "webhook-secret"))
        self.assertFalse(handler.verify_signature(event, "wrong-secret"))
        changed = handler.handle(raw.replace("outcome_unknown", "cancelled", 1))
        self.assertFalse(handler.verify_signature(changed, "webhook-secret"))
