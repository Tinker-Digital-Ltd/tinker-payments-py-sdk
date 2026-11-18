"""Customer access, catalogue, offerings, metrics, experiments and integrations."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote, urlencode

from .api import BaseManager


def _obj(response: Any) -> dict[str, Any]:
    return response if isinstance(response, dict) else {"value": response}


def _list(response: Any) -> list[dict[str, Any]]:
    return response if isinstance(response, list) else []


def _seg(value: str) -> str:
    return quote(value, safe="")


class CustomerManager(BaseManager):
    def _path(self, customer_id: str, suffix: str = "") -> str:
        return "merchant/customers/" + _seg(customer_id) + suffix

    def get(self, customer_id: str) -> dict[str, Any]:
        return _obj(self._request("GET", self._path(customer_id)))

    def get_entitlement(self, customer_id: str, identifier: str) -> dict[str, Any]:
        return _obj(
            self._request(
                "GET", self._path(customer_id, "/entitlements/" + _seg(identifier))
            )
        )

    def grant_promotional_entitlement(
        self,
        customer_id: str,
        identifier: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return _obj(
            self._request(
                "POST",
                self._path(
                    customer_id, "/entitlements/" + _seg(identifier) + "/promotional"
                ),
                payload,
            )
        )

    def revoke_promotional_entitlements(
        self, customer_id: str, identifier: str
    ) -> dict[str, Any]:
        return _obj(
            self._request(
                "POST",
                self._path(
                    customer_id,
                    "/entitlements/" + _seg(identifier) + "/revoke_promotionals",
                ),
            )
        )

    def alias(self, customer_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return _obj(self._request("POST", self._path(customer_id, "/alias"), payload))

    def transfer(self, customer_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return _obj(
            self._request("POST", self._path(customer_id, "/transfer"), payload)
        )

    def set_attributes(
        self, customer_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return _obj(
            self._request("POST", self._path(customer_id, "/attributes"), payload)
        )

    def get_offerings(self, customer_id: str) -> dict[str, Any]:
        return _obj(self._request("GET", self._path(customer_id, "/offerings")))

    def create_token(self, customer_id: str) -> dict[str, Any]:
        return _obj(self._request("POST", self._path(customer_id, "/token")))


class EntitlementManager(BaseManager):
    PATH = "merchant/entitlements"

    def _path(self, entitlement_id: str, suffix: str = "") -> str:
        return self.PATH + "/" + _seg(entitlement_id) + suffix

    def list(self) -> list[dict[str, Any]]:
        return _list(self._request("GET", self.PATH))

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        return _obj(self._request("POST", self.PATH, payload))

    def get(self, entitlement_id: str) -> dict[str, Any]:
        return _obj(self._request("GET", self._path(entitlement_id)))

    def update(self, entitlement_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return _obj(self._request("PATCH", self._path(entitlement_id), payload))

    def delete(self, entitlement_id: str) -> dict[str, Any]:
        return _obj(self._request("DELETE", self._path(entitlement_id)))

    def attach_products(
        self, entitlement_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return _obj(
            self._request(
                "POST", self._path(entitlement_id, "/attach_products"), payload
            )
        )

    def detach_products(
        self, entitlement_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return _obj(
            self._request(
                "POST", self._path(entitlement_id, "/detach_products"), payload
            )
        )


class ProductManager(BaseManager):
    PATH = "merchant/products"

    def list(self) -> list[dict[str, Any]]:
        return _list(self._request("GET", self.PATH))

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        return _obj(self._request("POST", self.PATH, payload))

    def get(self, product_id: str) -> dict[str, Any]:
        return _obj(self._request("GET", self.PATH + "/" + _seg(product_id)))

    def update(self, product_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return _obj(self._request("PATCH", self.PATH + "/" + _seg(product_id), payload))


class OfferingManager(BaseManager):
    PATH = "merchant/offerings"

    def list(self) -> list[dict[str, Any]]:
        return _list(self._request("GET", self.PATH))

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        return _obj(self._request("POST", self.PATH, payload))

    def get(self, offering_id: str) -> dict[str, Any]:
        return _obj(self._request("GET", self.PATH + "/" + _seg(offering_id)))

    def update(self, offering_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return _obj(
            self._request("PATCH", self.PATH + "/" + _seg(offering_id), payload)
        )

    def delete(self, offering_id: str) -> dict[str, Any]:
        return _obj(self._request("DELETE", self.PATH + "/" + _seg(offering_id)))


class MetricsManager(BaseManager):
    def get(
        self, from_date: str | None = None, to_date: str | None = None
    ) -> dict[str, Any]:
        query = urlencode(
            {k: v for k, v in (("from", from_date), ("to", to_date)) if v}
        )
        return _obj(
            self._request("GET", "merchant/metrics" + ("?" + query if query else ""))
        )


class ExperimentManager(BaseManager):
    PATH = "merchant/experiments"

    def list(self) -> list[dict[str, Any]]:
        return _list(self._request("GET", self.PATH))

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        return _obj(self._request("POST", self.PATH, payload))

    def get(self, experiment_id: str) -> dict[str, Any]:
        return _obj(self._request("GET", self.PATH + "/" + _seg(experiment_id)))

    def stop(self, experiment_id: str) -> dict[str, Any]:
        return _obj(
            self._request("POST", self.PATH + "/" + _seg(experiment_id) + "/stop")
        )


class IntegrationManager(BaseManager):
    PATH = "merchant/integrations"

    def list(self) -> list[dict[str, Any]]:
        return _list(self._request("GET", self.PATH))

    def upsert(self, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
        return _obj(self._request("PUT", self.PATH + "/" + _seg(kind), payload))

    def delete(self, kind: str) -> dict[str, Any]:
        return _obj(self._request("DELETE", self.PATH + "/" + _seg(kind)))

    def test(self, kind: str) -> dict[str, Any]:
        return _obj(self._request("POST", self.PATH + "/" + _seg(kind) + "/test"))
