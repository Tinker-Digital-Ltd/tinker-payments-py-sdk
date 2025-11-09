from abc import ABC
from typing import Dict, Any
from tinker.core.http import AuthClient
from tinker.core.http.http_client import HttpClient
from tinker.core.schemas.payment import PaymentResponse, PaymentQueryRequest, PaymentQueryResponse

class PaymentClient(ABC):

    def __init__(self, 
        api_key: str | None =None, api_secret: str | None =None,
        base_url: str | None =None
        ) -> None:
        
        self.api_key =api_key
        self.base_url =base_url
        self.api_secret =api_secret

        self.client =HttpClient()
        self.auth =AuthClient(
            api_key =self.api_key,
            api_secret =self.api_secret,
            base_url= self.base_url
        )

    def initiate(self, data: Any )->PaymentResponse:
        headers =self._headers
        response = self.client.request(
            method ='POST',
            headers =headers,
            json =data,
            url =f'{self.base_url}/api/payment/initiate',
        )
        return PaymentResponse(**response)
    
    def callback(self):
        ...
    
    def query(self, data: PaymentQueryRequest)->PaymentQueryResponse:
        headers =self._headers
        response = self.client.request(
            method='POST',
            headers=headers,
            json =data.model_dump(),
            url=f'{self.base_url}/api/payment/query',
        )
        return PaymentQueryResponse(**response)
    
    @property
    def _headers(self) ->Dict[str, str]:
        token =self.auth.get_access_token()
        return {'Authorization': f'Bearer {token}'}