import unittest
from dataclasses import replace

from tinker.webhook import (
    InvoiceEventData,
    PaymentEventData,
    SettlementEventData,
    SubscriptionEventData,
    WebhookEvent,
)


class WebhookTests(unittest.TestCase):
    def test_event_types_preserve_data_and_only_payments_convert_to_transactions(self):
        data = {"id": "item-1", "reference": "REF1", "status": "success", "amount": 100}
        for source, event_type in (
            ("payment", PaymentEventData),
            ("subscription", SubscriptionEventData),
            ("invoice", InvoiceEventData),
            ("settlement", SettlementEventData),
        ):
            with self.subTest(source=source):
                event = WebhookEvent.from_dict({"source": source, "data": data})
                self.assertIsInstance(event.data, event_type)
                self.assertEqual(event.raw_data, data)
                transaction = event.to_transaction()
                if source == "payment":
                    self.assertIsNotNone(transaction)
                    self.assertEqual(transaction.query_data["reference"], "REF1")
                    self.assertTrue(transaction.is_successful())
                else:
                    self.assertIsNone(transaction)

    def test_non_object_optional_fields_use_empty_defaults(self):
        for value in (None, [], "invalid"):
            with self.subTest(value=value):
                event = WebhookEvent.from_dict(
                    {
                        "source": "payment",
                        "data": value,
                        "meta": value,
                        "security": value,
                    }
                )
                self.assertEqual(event.raw_data, {})
                self.assertEqual(event.raw_meta, {})
                self.assertEqual(event.meta.version, "1.0")
                self.assertEqual(event.security.signature, "")

    def test_mismatched_event_data_does_not_convert_to_transaction(self):
        subscription = WebhookEvent.from_dict({"source": "subscription", "data": {}})
        self.assertIsNone(replace(subscription, source="payment").to_transaction())
