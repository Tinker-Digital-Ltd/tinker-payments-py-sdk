from tinker.core.utils.config import Config
from tinker.gateways import Mpesa, Paystack, Stripe

class TinkerClient:

    def __init__(self,
        api_key: str | None =None, api_secret: str | None =None,
        base_url: str | None =None
        ) -> None:
        self.api_key =api_key or Config.API_KEY
        self.base_url =base_url or Config.BASE_URL
        self.api_secret =api_secret or Config.API_SECRET

    @property   
    def mpesa(self):
        return Mpesa(
            api_key =self.api_key,
            api_secret =self.api_secret,
            base_url =self.base_url,
        )
    
    @property   
    def stripe(self):
        return Stripe(
            api_key =self.api_key,
            api_secret =self.api_secret,
            base_url =self.base_url,
        )
    
    @property   
    def paystack(self):
        return Paystack(
            api_key =self.api_key,
            api_secret =self.api_secret,
            base_url =self.base_url,
        )
    