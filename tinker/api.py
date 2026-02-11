"""API managers for transactions and subscriptions."""

from __future__ import annotations

from typing import Any

from . import endpoints
from .auth import AuthenticationManager
from .configuration import Configuration
from .exceptions import ApiError, NetworkError
from .models import ApiMeta, Transaction

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
            raise NetworkError("requests is required unless a custom session is provided")
        self._last_meta: ApiMeta | None = None

    def get_last_meta(self) -> ApiMeta | None:
        return self._last_meta

    def _request(self, method: str, endpoint: str, data: dict[str, Any] | None = None) -> Any:
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
                },
                json=data if data else None,
                timeout=30,
            )
            result = response.json() if response.text else {}

            if response.status_code >= 400:
                raise ApiError(self._extract_error_message(result))

            if isinstance(result, dict) and "success" in result:
                self._last_meta = ApiMeta.from_dict(result.get("meta") if isinstance(result.get("meta"), dict) else {})

                if result.get("success") is False:
                    raise ApiError(self._extract_error_message(result))

                payload = result.get("data")
                if isinstance(payload, (dict, list)):
                    return payload
                return {"value": payload}

            return result if isinstance(result, (dict, list)) else {}
        except ApiError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise NetworkError(f"Failed to communicate with Tinker API: {exc}") from exc

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
