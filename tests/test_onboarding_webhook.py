import unittest
from pathlib import Path

from tinker.exceptions import InvalidPayloadError
from tinker.webhook import OnboardingEventData, WebhookHandler


class OnboardingWebhookTests(unittest.TestCase):
    def test_go_signed_setup_test(self):
        payload = (Path(__file__).parent / "fixtures/setup-webhook.json").read_text()
        handler = WebhookHandler()
        event = handler.handle(payload)
        self.assertTrue(event.is_onboarding_event())
        self.assertTrue(event.is_setup_test())
        self.assertIsInstance(event.data, OnboardingEventData)
        self.assertIn("webhook verification", event.data.message)
        self.assertIsNone(handler.handle_as_transaction(payload))
        self.assertTrue(handler.verify_signature(event, "webhook-secret"))
        self.assertTrue(handler.verify_signature(payload, "webhook-secret"))
        self.assertFalse(handler.verify_signature(payload, "wrong-secret"))
        self.assertFalse(handler.verify_signature(payload, ""))
        for before, after in (("verification", "forged"), ("HMAC-SHA256", "none"), ("sha256=", "invalid=")):
            self.assertFalse(handler.verify_signature(payload.replace(before, after), "webhook-secret"))
        self.assertFalse(handler.handle(payload.replace("setup.webhook_test", "onboarding.future")).is_setup_test())
        with self.assertRaises(InvalidPayloadError):
            handler.handle(payload.replace('"source":"onboarding"', '"source":"unknown"'))
