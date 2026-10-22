"""API managers for transactions and subscriptions."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any, cast
from urllib.parse import quote, urlencode

from . import endpoints
from . import lifecycle as lc
from .auth import AuthenticationManager
from .configuration import Configuration
from .exceptions import ApiError, NetworkError
from .lifecycle_helpers import idempotency_headers, payment_path, positive_amount
from .managed_checkout import ManagedCheckout, unix_seconds
from .models import ApiMeta, Transaction

requests: Any
try:
    import requests
except ModuleNotFoundError:  # pragma: no cover
    requests = None


class BaseManager:
    def __init__(
        self,
        config: Configuration,
        auth_manager: AuthenticationManager,
        session: Any | None = None,
    ) -> None:
        self._config = config
        self._auth_manager = auth_manager
        if session is not None:
            self._session = session
        elif requests is not None:
            self._session = requests.Session()
        else:
            raise NetworkError(
                "requests is required unless a custom session is provided"
            )
        self._last_meta: ApiMeta | None = None

    def get_last_meta(self) -> ApiMeta | None:
        return self._last_meta

    def _request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        base_url = self._config.base_url.rstrip("/")
        url = f"{base_url}/{endpoint.lstrip('/')}"
        token = self._auth_manager.get_token()

        try:
            response = self._session.request(
                method=method,
                url=url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    **(headers or {}),
                },
                json=data if data else None,
                timeout=30,
            )
            try:
                result = response.json() if response.text else {}
            except ValueError:
                if response.status_code < 400:
                    raise
                result = {}

            if response.status_code >= 400:
                raise self._api_error(response, result)

            if isinstance(result, dict) and "success" in result:
                self._last_meta = ApiMeta.from_dict(
                    result.get("meta") if isinstance(result.get("meta"), dict) else {}
                )

                if result.get("success") is False:
                    raise self._api_error(response, result)

                payload = result.get("data")
                if isinstance(payload, (dict, list)):
                    return payload
                return {"value": payload}

            return result if isinstance(result, (dict, list)) else {}
        except ApiError:
            raise
        except Exception as exc:
            raise NetworkError(f"Failed to communicate with Tinker API: {exc}") from exc

    def _api_error(self, response: Any, result: Any) -> ApiError:
        return ApiError(
            self._extract_error_message(result),
            http_status=response.status_code,
            details=result,
            headers=getattr(response, "headers", {}),
        )

    @staticmethod
    def _extract_error_message(result: Any) -> str:
        if isinstance(result, dict):
            if isinstance(result.get("error"), dict):
                error = result["error"]
                return str(error.get("message") or error.get("code") or "Unknown error")
            if "message" in result:
                return str(result["message"])

        return "Unknown error"


class TransactionManager(BaseManager):
    def initiate(self, payload: dict[str, Any]) -> Transaction:
        response = self._request("POST", endpoints.PAYMENT_INITIATE_PATH, payload)
        if not isinstance(response, dict):
            response = {"value": response}
        return Transaction.from_dict(response)

    def query(self, payload: dict[str, Any]) -> Transaction:
        response = self._request("POST", endpoints.PAYMENT_QUERY_PATH, payload)
        if not isinstance(response, dict):
            response = {"value": response}
        return Transaction.from_dict(response)

    def refund(
        self, payment_id: str, payload: lc.RefundRequest, key: str
    ) -> lc.RefundResult:
        if "amount" in payload:
            positive_amount(payload["amount"])
        return cast(
            lc.RefundResult,
            self._request(
                "POST",
                payment_path(payment_id) + "/refund",
                dict(payload),
                idempotency_headers(key),
            ),
        )

    def refunds(self, payment_id: str) -> lc.RefundHistory:
        return cast(
            lc.RefundHistory,
            self._request("GET", payment_path(payment_id) + "/refunds"),
        )

    def get_refund(self, payment_id: str, refund_id: str) -> lc.Refund:
        return cast(
            lc.Refund,
            self._request(
                "GET",
                payment_path(payment_id) + "/refunds/" + quote(refund_id, safe=""),
            ),
        )

    def cancel_checkout(
        self, payment_id: str, payload: lc.CancellationRequest, key: str
    ) -> lc.CancellationResult:
        return cast(
            lc.CancellationResult,
            self._request(
                "POST",
                payment_path(payment_id) + "/cancellations",
                dict(payload),
                idempotency_headers(key),
            ),
        )

    def cancellations(self, payment_id: str) -> lc.CancellationHistory:
        return cast(
            lc.CancellationHistory,
            self._request("GET", payment_path(payment_id) + "/cancellations"),
        )

    def get_cancellation(self, payment_id: str, request_id: str) -> lc.Cancellation:
        return cast(
            lc.Cancellation,
            self._request(
                "GET",
                payment_path(payment_id)
                + "/cancellations/"
                + quote(request_id, safe=""),
            ),
        )


class PayoutManager(BaseManager):
    """Merchant wallet withdrawals to the merchant's verified destinations."""

    def methods(self) -> list[lc.PayoutMethod]:
        return cast(
            list[lc.PayoutMethod], self._request("GET", "merchant/payout-methods")
        )

    def quote(self, payload: lc.PayoutQuoteRequest) -> lc.PayoutQuote:
        positive_amount(payload["amount"])
        return cast(
            lc.PayoutQuote,
            self._request("GET", "merchant/payouts/quote?" + urlencode(payload)),
        )

    def request_payout(self, payload: lc.PayoutRequest, key: str) -> lc.PayoutResult:
        positive_amount(payload["amount"])
        if (
            not math.isfinite(payload["expected_fee_amount"])
            or payload["expected_fee_amount"] < 0
        ):
            raise ValueError("expected_fee_amount must be finite and non-negative")
        return cast(
            lc.PayoutResult,
            self._request(
                "POST", "merchant/payouts", dict(payload), idempotency_headers(key)
            ),
        )

    def list(self, filters: lc.PayoutFilters | None = None) -> lc.PayoutPage:
        query = "?" + urlencode(filters) if filters else ""
        return cast(lc.PayoutPage, self._request("GET", "merchant/payouts" + query))

    def get(self, payout_id: str) -> lc.Payout:
        return cast(
            lc.Payout,
            self._request("GET", "merchant/payouts/" + quote(payout_id, safe="")),
        )


class SubscriptionManager(BaseManager):
    def create_plan(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._request("POST", endpoints.SUBSCRIPTION_PLANS_PATH, payload)
        return response if isinstance(response, dict) else {"value": response}

    def list_plans(self) -> list[dict[str, Any]]:
        response = self._request("GET", endpoints.SUBSCRIPTION_PLANS_PATH)
        return response if isinstance(response, list) else []

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._request("POST", endpoints.SUBSCRIPTION_BASE_PATH, payload)
        return response if isinstance(response, dict) else {"value": response}

    def list(
        self,
        plan_id: str | None = None,
        external_customer_id: str | None = None,
    ) -> list[dict[str, Any]]:
        params = []
        if plan_id and plan_id.strip():
            params.append(f"plan_id={plan_id}")
        if external_customer_id and external_customer_id.strip():
            params.append(f"external_customer_id={external_customer_id}")

        endpoint = endpoints.SUBSCRIPTION_BASE_PATH
        if params:
            endpoint = f"{endpoint}?{'&'.join(params)}"

        response = self._request("GET", endpoint)
        return response if isinstance(response, list) else []

    def cancel(self, subscription_id: str) -> dict[str, Any]:
        endpoint = f"{endpoints.SUBSCRIPTION_BASE_PATH}/{subscription_id}/cancel"
        response = self._request("POST", endpoint)
        return response if isinstance(response, dict) else {"value": response}

    def checkout(self, request: ManagedCheckout) -> dict[str, Any]:
        return self._request("POST", "merchant/billing/checkout", request.to_dict())

    def expire_checkout(self, checkout_id: str, key: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "merchant/billing/checkout/" + quote(checkout_id, safe="") + "/expire",
            {"idempotency_key": key},
        )

    def billing_resource(self, resource_id: str) -> dict[str, Any]:
        return self._request("GET", self._billing_resource_path(resource_id))

    def change_quantity(
        self, resource_id: str, quantity: int, key: str
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            self._billing_resource_path(resource_id) + "/quantity",
            {"quantity": quantity, "idempotency_key": key},
        )

    def schedule_quantity(
        self, resource_id: str, quantity: int, key: str
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            self._billing_resource_path(resource_id) + "/schedule",
            {"quantity": quantity, "idempotency_key": key},
        )

    def clear_scheduled_quantity(self, resource_id: str, key: str) -> dict[str, Any]:
        return self._request(
            "POST",
            self._billing_resource_path(resource_id) + "/unschedule",
            {"idempotency_key": key},
        )

    def set_cancel_at_renewal(
        self, resource_id: str, cancel: bool, key: str
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            self._billing_resource_path(resource_id) + "/cancel",
            {"cancel": cancel, "idempotency_key": key},
        )

    def set_trial_end(
        self, resource_id: str, end: datetime, key: str
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            self._billing_resource_path(resource_id) + "/trial-end",
            {"trial_end": unix_seconds(end), "idempotency_key": key},
        )

    def end_trial(self, resource_id: str, key: str) -> dict[str, Any]:
        return self._request(
            "POST",
            self._billing_resource_path(resource_id) + "/end-trial",
            {"idempotency_key": key},
        )

    def billing_operation(self, key: str) -> dict[str, Any]:
        return self._request(
            "GET", "merchant/billing/operations/" + quote(key, safe="")
        )

    def payment_method_portal(
        self, resource_id: str, return_url: str, key: str
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            self._billing_resource_path(resource_id) + "/payment-method",
            {"return_url": return_url, "idempotency_key": key},
        )

    def billing_payment_history(
        self, resource_id: str, cursor: str = "", snapshot: int = 0
    ) -> dict[str, Any]:
        params = {}
        if cursor:
            params["starting_after"] = cursor
        if snapshot > 0:
            params["snapshot"] = str(snapshot)
        endpoint = self._billing_resource_path(resource_id) + "/payment-history"
        if params:
            endpoint += "?" + urlencode(params)
        return self._request("GET", endpoint)

    @staticmethod
    def _billing_resource_path(resource_id: str) -> str:
        return "merchant/billing/resources/" + quote(resource_id, safe="")
