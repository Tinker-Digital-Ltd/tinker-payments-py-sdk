import unittest

from test_sdk import FakeResponse, FakeSession

from tinker import TinkerClient
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
