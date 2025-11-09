import time, base64
from .http_client import HttpClient
from tinker.core.schemas import Token, AuthRequest

class AuthClient:

    def __init__(self, api_key: str | None =None, api_secret: str | None =None,
        base_url: str | None =None) -> None:
        self.api_key =api_key
        self.base_url =base_url
        self.client =HttpClient()
        self.api_secret =api_secret
        self.token: Token | None = None
    
    
    def get_access_token(self)->str:
        if self._isTokenValid and self.token: return self.token.token
        credentials =base64.b64encode(f"{self.api_key}:{self.api_secret}".encode()).decode()
        headers ={ 'Content-Type': 'application/x-www-form-urlencoded'}
        data = AuthRequest(credentials=credentials).model_dump()
        url =f"{self.base_url}/auth/token"
        response = self.client.request(method ='POST', url =url, data =data, headers =headers)
        token =Token(**response)

        token.expires_in +=int(time.time())
        self.token =token
        return token.token

    
    @property
    def _isTokenValid(self):
        if not self.token: return False
        return time.time() >= self.token.expires_in