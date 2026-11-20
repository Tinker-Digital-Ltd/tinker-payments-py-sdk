import unittest

from test_sdk import FakeSession

from tinker import TinkerClient

BASE = "https://sandbox-api.tinkerpayments.com/v1/merchant/"


class AccessTests(unittest.TestCase):
    def setUp(self):
        self.session = FakeSession()
        self.client = TinkerClient("pk_test_1", "sk_test_1", session=self.session)

    def last(self):
        method, url, body = self.session.calls[-1]
        return method, url, body

    def test_customers(self):
        c = self.client.customers()
        cases = [
            (lambda: c.list_customers(), "GET", "customers", None),
            (
                lambda: c.list_customers("a b", 2, 50),
                "GET",
                "customers?search=a+b&page=2&page_size=50",
                None,
            ),
            (lambda: c.get_customer("u/1"), "GET", "customers/u%2F1", None),
            (
                lambda: c.get_entitlement("u1", "pro"),
                "GET",
                "customers/u1/entitlements/pro",
                None,
            ),
            (
                lambda: c.grant_promotional_entitlement("u1", "pro", duration="P7D"),
                "POST",
                "customers/u1/entitlements/pro/promotional",
                {"duration": "P7D"},
            ),
            (
                lambda: c.revoke_promotional_entitlements("u1", "pro"),
                "POST",
                "customers/u1/entitlements/pro/revoke_promotionals",
                None,
            ),
            (
                lambda: c.alias("u1", "a"),
                "POST",
                "customers/u1/alias",
                {"alias": "a"},
            ),
            (
                lambda: c.transfer("u1", "u2"),
                "POST",
                "customers/u1/transfer",
                {"to": "u2"},
            ),
            (
                lambda: c.set_attributes("u1", {"k": None}),
                "POST",
                "customers/u1/attributes",
                {"attributes": {"k": None}},
            ),
            (lambda: c.get_offerings("u1"), "GET", "customers/u1/offerings", None),
            (lambda: c.create_token("u1"), "POST", "customers/u1/token", None),
            (
                lambda: c.create_token("u1", expires_in=300),
                "POST",
                "customers/u1/token",
                {"expires_in": 300},
            ),
        ]
        for call, method, path, body in cases:
            call()
            self.assertEqual(self.last(), (method, BASE + path, body))

    def test_catalogue_and_experiments(self):
        e = self.client.entitlements()
        p = self.client.products()
        o = self.client.offerings()
        x = self.client.experiments()
        i = self.client.integrations()
        cases = [
            (e.list, "GET", "entitlements", None),
            (
                lambda: e.create({"identifier": "pro"}),
                "POST",
                "entitlements",
                {"identifier": "pro"},
            ),
            (lambda: e.get("e1"), "GET", "entitlements/e1", None),
            (
                lambda: e.update("e1", "n"),
                "PATCH",
                "entitlements/e1",
                {"display_name": "n"},
            ),
            (lambda: e.delete("e1"), "DELETE", "entitlements/e1", None),
            (
                lambda: e.attach_products("e1", ["p"]),
                "POST",
                "entitlements/e1/attach_products",
                {"product_ids": ["p"]},
            ),
            (
                lambda: e.detach_products("e1", ["p"]),
                "POST",
                "entitlements/e1/detach_products",
                {"product_ids": ["p"]},
            ),
            (p.list, "GET", "products", None),
            (
                lambda: p.create({"identifier": "x"}),
                "POST",
                "products",
                {"identifier": "x"},
            ),
            (lambda: p.get("p1"), "GET", "products/p1", None),
            (
                lambda: p.update("p1", {"name": "n"}),
                "PATCH",
                "products/p1",
                {"name": "n"},
            ),
            (o.list, "GET", "offerings", None),
            (
                lambda: o.create({"identifier": "x"}),
                "POST",
                "offerings",
                {"identifier": "x"},
            ),
            (lambda: o.get("o1"), "GET", "offerings/o1", None),
            (
                lambda: o.update("o1", {"name": "n"}),
                "PATCH",
                "offerings/o1",
                {"name": "n"},
            ),
            (lambda: o.delete("o1"), "DELETE", "offerings/o1", None),
            (x.list, "GET", "experiments", None),
            (lambda: x.create({"name": "n"}), "POST", "experiments", {"name": "n"}),
            (lambda: x.get("x1"), "GET", "experiments/x1", None),
            (lambda: x.stop("x1"), "POST", "experiments/x1/stop", None),
            (i.list, "GET", "integrations", None),
            (
                lambda: i.put("slack", {"url": "u"}),
                "PUT",
                "integrations/slack",
                {"url": "u"},
            ),
            (lambda: i.delete("slack"), "DELETE", "integrations/slack", None),
            (lambda: i.test("slack"), "POST", "integrations/slack/test", None),
        ]
        for call, method, path, body in cases:
            call()
            self.assertEqual(self.last(), (method, BASE + path, body))

    def test_metrics_and_renewal_prompts(self):
        m = self.client.metrics()
        m.get()
        self.assertEqual(self.last()[:2], ("GET", BASE + "metrics"))
        m.get("2026-01-01", "2026-01-31")
        self.assertEqual(
            self.last()[:2], ("GET", BASE + "metrics?from=2026-01-01&to=2026-01-31")
        )
        s = self.client.subscriptions()
        s.list_renewal_prompts()
        self.assertEqual(
            self.last()[:2], ("GET", BASE + "subscriptions/renewal_prompts")
        )
        s.list_renewal_prompts("sub_1")
        self.assertEqual(
            self.last()[:2],
            ("GET", BASE + "subscriptions/renewal_prompts?subscription_id=sub_1"),
        )
        s.list_renewal_prompts("sub_1", 2, 50)
        self.assertEqual(
            self.last()[:2],
            (
                "GET",
                BASE
                + "subscriptions/renewal_prompts?subscription_id=sub_1&page=2&page_size=50",
            ),
        )
        s.send_renewal_prompt("sub_1")
        self.assertEqual(
            self.last()[:2], ("POST", BASE + "subscriptions/sub_1/renewal_prompt")
        )

    def test_webhook_events(self):
        h = self.client.webhooks()
        base = {"id": "e", "timestamp": "t", "meta": {"app_id": "a"}}
        purchase = h.handle(
            {
                **base,
                "type": "purchase.completed",
                "source": "payment",
                "data": {
                    "external_customer_id": "u1",
                    "entitlement_ids": ["pro"],
                    "store": "MPESA",
                    "period_type": "NORMAL",
                    "expiration_at": None,
                    "product_id": "p1",
                    "amount": 10,
                },
            }
        )
        self.assertEqual(purchase.data.product_id, "p1")
        self.assertEqual(purchase.data.entitlement_ids, ["pro"])
        granted = h.handle(
            {
                **base,
                "type": "entitlement.granted",
                "source": "entitlement",
                "data": {"id": "g"},
            }
        )
        self.assertEqual(granted.data.id, "g")
        moved = h.handle(
            {
                **base,
                "type": "customer.transferred",
                "source": "customer",
                "data": {"transferred_from": ["a"], "transferred_to": ["b"]},
            }
        )
        self.assertEqual(moved.data.transferred_to, ["b"])
        sub = h.handle(
            {
                **base,
                "type": "subscription.billing_issue",
                "source": "subscription",
                "data": {
                    "subscription_id": "s",
                    "external_customer_id": "u1",
                    "product_id": "p",
                    "entitlement_ids": ["pro"],
                    "grace_period_expiration_at": "g",
                },
            }
        )
        self.assertEqual(sub.data.grace_period_expiration_at, "g")
        self.assertEqual(sub.data.entitlement_ids, ["pro"])
        self.assertEqual(sub.data.external_customer_id, "u1")


if __name__ == "__main__":
    unittest.main()
