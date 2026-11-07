import json
import os
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from test_managed_billing import BillingSession

from tinker import Gateways, PaymentStatus, TinkerClient
from tinker.exceptions import ApiError, FeatureNotSupportedError

FIXTURE = Path(
    os.environ.get(
        "TINKER_LIFECYCLE_FIXTURE",
        Path(__file__).parents[3]
        / "tinker-payments-backend/openapi/fixtures/merchant-lifecycle.json",
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

    def test_gateway_cases(self):
        self.assertEqual(Gateways.PESAPAL, "pesapal")
        for row in CONTRACT["gateway"]["cases"]:
            session = BillingSession(row["status"], row["response"])
            tx = TinkerClient("public", "secret", session=session).transactions()
            op = row["operation"]
            run = {
                "listPaymentCapabilities": lambda: tx.capabilities("KES", "KE"),
                "initiatePayment": lambda: tx.initiate(row["body"]),
                "queryPayment": lambda: tx.query(row["body"]),
            }[op]
            if row["status"] == 422:
                with self.assertRaises(FeatureNotSupportedError) as raised:
                    run()
                error = raised.exception
                self.assertIsInstance(error, ApiError)
                self.assertEqual(error.error_code, "FEATURE_NOT_SUPPORTED")
                self.assertEqual(error.gateway, "mpesa")
                self.assertEqual(error.feature, "wallet")
                self.assertEqual(error.alternatives, ["stripe"])
            else:
                result = run()
                if op == "listPaymentCapabilities":
                    self.assertEqual(result, row["response"]["data"])
                else:
                    self.assertEqual(
                        result.status, "reversed" if op == "queryPayment" else "pending"
                    )
            method, url, body, _ = [
                c for c in session.calls if not c[1].endswith("/auth/token")
            ][0]
            actual, expected = (
                urlsplit(url),
                urlsplit("https://example.test/v1/" + row["path"]),
            )
            self.assertEqual(actual.path, expected.path)
            self.assertEqual(parse_qs(actual.query), parse_qs(expected.query))
            self.assertEqual(method, row["method"])
            self.assertEqual(body, row["body"])

    def test_completed_maps_to_success(self):
        body = {
            "success": True,
            "data": {"id": "a", "reference": "b", "status": "completed"},
        }
        tx = TinkerClient("p", "s", session=BillingSession(200, body)).transactions()
        self.assertTrue(tx.query({"reference": "b"}).is_successful())

    def test_payment_status_constants_and_unknown_pass_through(self):
        self.assertEqual(PaymentStatus.PARTIALLY_REFUNDED, "partially_refunded")
        self.assertEqual(PaymentStatus.SUCCESS, "success")
        body = {
            "success": True,
            "data": {"id": "a", "reference": "b", "status": "future_state"},
        }
        tx = TinkerClient("p", "s", session=BillingSession(200, body)).transactions()
        self.assertEqual(tx.query({"reference": "b"}).status, "future_state")

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
            Path(__file__).parents[3]
            / "tinker-payments-backend/openapi/fixtures/checkout-cancellation-webhook.json"
        )
        if canonical.exists():
            self.assertEqual(json.loads(raw), json.loads(canonical.read_text()))
        handler = TinkerClient("public", "secret", session=BillingSession()).webhooks()
        event = handler.handle(raw)
        self.assertTrue(event.is_checkout_cancellation())
        self.assertIsInstance(event.data, CheckoutCancellationEventData)
        self.assertEqual(event.data.resource["status"], "outcome_unknown")
        self.assertIsNone(event.to_transaction())
        self.assertTrue(handler.verify_signature(event, "webhook-secret"))
        self.assertFalse(handler.verify_signature(event, "wrong-secret"))
        changed = handler.handle(raw.replace("outcome_unknown", "cancelled", 1))
        self.assertFalse(handler.verify_signature(changed, "webhook-secret"))

    def test_refund_and_withdrawal_updates(self):
        from tinker.webhook import RefundEventData, WithdrawalEventData

        handler = TinkerClient("public", "secret", session=BillingSession()).webhooks()
        for name, expected_type in [
            ("refund", RefundEventData),
            ("withdrawal", WithdrawalEventData),
        ]:
            raw = (Path(__file__).parent / f"fixtures/{name}-webhook.json").read_text()
            canonical = (
                Path(__file__).parents[3]
                / f"tinker-payments-backend/openapi/fixtures/{name}-webhook.json"
            )
            if canonical.exists():
                self.assertEqual(json.loads(raw), json.loads(canonical.read_text()))
            event = handler.handle(raw)
            self.assertIsInstance(event.data, expected_type)
            self.assertIsNone(event.to_transaction())
            self.assertIsNone(
                handler.handle(
                    raw.replace(".updated.v1", ".updated.v2")
                ).to_transaction()
            )
            self.assertTrue(handler.verify_signature(event, "webhook-secret"))
            self.assertFalse(handler.verify_signature(event, "wrong-secret"))
            self.assertFalse(
                handler.verify_signature(
                    handler.handle(raw.replace("pending_", "forged_")), "webhook-secret"
                )
            )
