import unittest
from dataclasses import replace
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit

from test_sdk import FakeResponse, FakeSession

from tinker import ManagedCheckout, TinkerClient
from tinker.exceptions import ApiError, NetworkError


class BillingSession(FakeSession):
    def __init__(self, status=200, body=None, invalid_json=False):
        super().__init__()
        self.status = status
        self.body = (
            body
            if body is not None
            else {
                "success": True,
                "data": {"snapshot": 123, "next_cursor": "in_next", "has_more": True},
            }
        )
        self.invalid_json = invalid_json

    def request(self, method, url, headers=None, json=None, timeout=None):
        self.calls.append((method, url, json, headers))
        response = FakeResponse(self.status, self.body)
        response.headers = {"x-request-id": "header-id", "rEtRy-AfTeR": "30"}
        if self.invalid_json:
            response.text = "<html>Bad gateway</html>"

            def fail():
                raise ValueError("Invalid JSON")

            response.json = fail
        return response


class ManagedBillingTests(unittest.TestCase):
    def test_all_operations_and_pagination(self):
        session = BillingSession()
        m = TinkerClient("public", "secret", session=session).subscriptions()
        checkout = ManagedCheckout(
            "workspace",
            "buyer@example.com",
            "Buyer",
            "EUR",
            15000,
            3,
            "year",
            "https://example.com/return",
            "checkout-key",
        )
        self.assertEqual(
            checkout.to_dict(),
            {
                "external_customer_id": "workspace",
                "email": "buyer@example.com",
                "name": "Buyer",
                "currency": "EUR",
                "unit_amount": 15000,
                "quantity": 3,
                "interval": "year",
                "return_url": "https://example.com/return",
                "idempotency_key": "checkout-key",
            },
        )
        self.assertNotIn("trial_days", checkout.to_dict())
        m.checkout(checkout)
        trial = replace(checkout, trial_days=14)
        self.assertEqual(trial.to_dict()["trial_days"], 14)
        m.checkout(trial)
        end = datetime.fromtimestamp(1900000000, timezone.utc)
        dated = replace(checkout, trial_end=end)
        self.assertEqual(dated.to_dict()["trial_end"], 1900000000)
        with self.assertRaises(ValueError):
            replace(checkout, trial_end=datetime(2030, 1, 1)).to_dict()
        m.checkout(dated)
        m.expire_checkout("cs/a b", "expire-key")
        m.set_trial_end("sub/a b", end, "trial-end-key")
        m.end_trial("sub/a b", "end-trial-key")
        m.billing_resource("sub/a b")
        m.change_quantity("sub/a b", 4, "change-key")
        m.schedule_quantity("sub/a b", 2, "schedule-key")
        m.clear_scheduled_quantity("sub/a b", "clear-key")
        m.set_cancel_at_renewal("sub/a b", False, "resume-key")
        m.billing_operation("key/a b")
        m.payment_method_portal("sub/a b", "https://example.com/return", "portal-key")
        page = m.billing_payment_history("sub/a b", "in/a &b", 123)
        m.billing_payment_history("sub/a b")
        calls = [c for c in session.calls if not c[1].endswith("/auth/token")]
        base = "/v1/merchant/billing/resources/sub%2Fa%20b"
        expected = [
            ("POST", "/v1/merchant/billing/checkout", checkout.to_dict()),
            ("POST", "/v1/merchant/billing/checkout", trial.to_dict()),
            ("POST", "/v1/merchant/billing/checkout", dated.to_dict()),
            (
                "POST",
                "/v1/merchant/billing/checkout/cs%2Fa%20b/expire",
                {"idempotency_key": "expire-key"},
            ),
            (
                "POST",
                base + "/trial-end",
                {"trial_end": 1900000000, "idempotency_key": "trial-end-key"},
            ),
            ("POST", base + "/end-trial", {"idempotency_key": "end-trial-key"}),
            ("GET", base, None),
            (
                "POST",
                base + "/quantity",
                {"quantity": 4, "idempotency_key": "change-key"},
            ),
            (
                "POST",
                base + "/schedule",
                {"quantity": 2, "idempotency_key": "schedule-key"},
            ),
            ("POST", base + "/unschedule", {"idempotency_key": "clear-key"}),
            (
                "POST",
                base + "/cancel",
                {"cancel": False, "idempotency_key": "resume-key"},
            ),
            ("GET", "/v1/merchant/billing/operations/key%2Fa%20b", None),
            (
                "POST",
                base + "/payment-method",
                {
                    "return_url": "https://example.com/return",
                    "idempotency_key": "portal-key",
                },
            ),
            ("GET", base + "/payment-history", None),
            ("GET", base + "/payment-history", None),
        ]
        self.assertEqual([(c[0], urlsplit(c[1]).path, c[2]) for c in calls], expected)
        self.assertTrue(all(c[3]["Authorization"] == "Bearer abc123" for c in calls))
        self.assertEqual(
            parse_qs(urlsplit(calls[-2][1]).query),
            {"starting_after": ["in/a &b"], "snapshot": ["123"]},
        )
        self.assertEqual(urlsplit(calls[-1][1]).query, "")
        self.assertEqual(
            page, {"snapshot": 123, "next_cursor": "in_next", "has_more": True}
        )

    def test_structured_errors_and_envelope_failures(self):
        body = {
            "success": False,
            "error": {
                "message": "Try later",
                "code": "RATE_LIMITED",
                "provider_code": "rate_limit",
                "request_id": "body-id",
                "outcome": "not_applied",
            },
        }
        for status in (429, 200):
            with self.subTest(status=status):
                m = TinkerClient(
                    "public", "secret", session=BillingSession(status, body)
                ).subscriptions()
                with self.assertRaises(ApiError) as raised:
                    m.list_plans()
                e = raised.exception
                self.assertEqual(str(e), "Try later")
                self.assertEqual(
                    (
                        e.http_status,
                        e.error_code,
                        e.provider_code,
                        e.request_id,
                        e.retry_after,
                        e.outcome,
                    ),
                    (
                        status,
                        "RATE_LIMITED",
                        "rate_limit",
                        "body-id",
                        "30",
                        "not_applied",
                    ),
                )

    def test_non_json_failure_is_uncertain_api_error(self):
        m = TinkerClient(
            "public", "secret", session=BillingSession(502, invalid_json=True)
        ).subscriptions()
        with self.assertRaises(ApiError) as raised:
            m.list_plans()
        self.assertEqual(raised.exception.http_status, 502)
        self.assertEqual(raised.exception.request_id, "header-id")
        self.assertIsNone(raised.exception.outcome)

    def test_transport_failure_stays_network_error(self):
        session = BillingSession()

        def fail(**kwargs):
            raise OSError("Connection lost")

        session.request = fail
        m = TinkerClient("public", "secret", session=session).subscriptions()
        with self.assertRaises(NetworkError):
            m.list_plans()
