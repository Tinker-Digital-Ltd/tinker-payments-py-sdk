import hashlib
import hmac
import json
import unittest

from tinker import TinkerClient


class FakeResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body
        self.text = json.dumps(body)

    def json(self):
        return self._body


class FakeSession:
    def __init__(self):
        self.calls = []

    def post(self, url, data=None, headers=None, timeout=None):
        self.calls.append(("POST", url, data))
        return FakeResponse(
            200,
            {
                "success": True,
                "data": {"token": "abc123", "expires_in": 3600},
                "meta": {
                    "request_id": "5b5b3526-8dc1-4f7b-9bb8-cdbfc8df4984",
                    "timestamp": "2026-02-11T22:52:45Z",
                    "environment": "sandbox",
                },
            },
        )

    def request(self, method, url, headers=None, json=None, timeout=None):
        self.calls.append((method, url, json))
        return FakeResponse(
            200,
            {
                "success": True,
                "data": {"paymentReference": "P123", "status": "pending"},
                "meta": {
                    "request_id": "meta-request",
                    "timestamp": "2026-02-11T22:52:45Z",
                    "environment": "sandbox",
                },
            },
        )


class SdkTests(unittest.TestCase):
    def test_sandbox_url_resolution(self):
        client = TinkerClient("pk_test_123", "sk_test_123", session=FakeSession())
        self.assertEqual(client.config.base_url, "https://sandbox-api.tinkerpayments.com/v1/")

    def test_auth_meta_is_mapped(self):
        session = FakeSession()
        client = TinkerClient("pk_test_123", "sk_test_123", session=session)
        client.transactions().initiate({"amount": 100, "currency": "KES"})
        meta = client.get_last_auth_meta()
        self.assertIsNotNone(meta)
        self.assertEqual(meta.request_id, "5b5b3526-8dc1-4f7b-9bb8-cdbfc8df4984")
        self.assertEqual(meta.environment, "sandbox")

    def test_webhook_signature_verification(self):
        client = TinkerClient("pk_live_123", "sk_live_123", session=FakeSession())
        secret = "whsec_123"
        payload = {
            "id": "evt_123",
            "type": "payment.completed",
            "source": "payment",
            "timestamp": "2026-02-11T22:52:45Z",
            "data": {
                "id": "pay_1",
                "status": "success",
                "reference": "REF1",
                "amount": 100,
                "currency": "KES",
                "channel": "card",
                "created_at": "2026-02-11T22:52:45Z",
            },
            "meta": {"app_id": "app_123", "version": "1.0"},
        }

        raw = json.dumps(
            {
                "id": payload["id"],
                "type": payload["type"],
                "source": payload["source"],
                "timestamp": payload["timestamp"],
                "data": payload["data"],
                "meta": payload["meta"],
            },
            separators=(",", ":"),
            ensure_ascii=False,
        )

        payload["security"] = {
            "algorithm": "HMAC-SHA256",
            "signature": "sha256=" + hmac.new(secret.encode(), raw.encode(), hashlib.sha256).hexdigest(),
        }

        self.assertTrue(client.webhooks().verify_signature(payload, secret))


if __name__ == "__main__":
    unittest.main()
