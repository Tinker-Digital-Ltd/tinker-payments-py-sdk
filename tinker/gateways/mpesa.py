from typing import Dict, Any
from tinker.core.http import PaymentClient
from tinker.core.schemas.payment import MpesaPaymentRequest, PaymentQueryResponse, PaymentResponse, PaymentQueryRequest


class Mpesa(PaymentClient):

    def __init__(self, api_key: str | None = None, api_secret: str | None = None, base_url: str | None = None) -> None:
        super().__init__(api_key =api_key, api_secret =api_secret, base_url =base_url)
    
    def initiate(self, data: MpesaPaymentRequest) -> PaymentResponse:
        payload: Dict[str, Any] ={ **data.model_dump(), 'gateway': 'mpesa' }
        return super().initiate(payload)

    def query(self, payment_reference:str) -> PaymentQueryResponse: # pyright: ignore[reportIncompatibleMethodOverride]
        data =PaymentQueryRequest(
            gateway='mpesa',
            payment_reference=payment_reference
        )
        return super().query(data)