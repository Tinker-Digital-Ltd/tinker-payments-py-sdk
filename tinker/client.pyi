from typing import Optional
from tinker.gateways import Mpesa, Paystack, Stripe

class TinkerClient:
    api_key: str
    api_secret: str
    base_url: str

    def __init__(
        self,
        api_key: Optional[str] = ...,
        api_secret: Optional[str] = ...,
        base_url: Optional[str] = ...,
    ) -> None: 
        ...

    @property
    def mpesa(self) -> Mpesa: 
        ...

    @property
    def stripe(self) -> Stripe: 
        ...

    @property
    def paystack(self) -> Paystack: 
        ...
