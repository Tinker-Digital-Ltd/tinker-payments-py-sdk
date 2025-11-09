import requests
from typing import Dict, Any
from tinker.core.schemas import HttpError
from tinker.core.utils.exceptions import APIError


class HttpClient:

    def _headers(
            self, extra: Dict[str, str] | None = None
        ) -> Dict[str, str]:

        headers = { "Content-Type": "application/json" }
        if extra: headers.update(extra)
        return headers
    
    def request(
            self, method: str, url:str, *, 
            data: Dict[str, Any] | None =None,
            json: Dict[str, Any] | None =None,
            headers: Dict[str, str] | None =None
        )->Dict[str, Any]:
        try:
            method =method.upper()
            headers =self._headers(headers)
            request = requests.request(
                method =method,
                url =url,
                data =data,
                json =json,
                headers =headers
            )
            if request.status_code >= 400:
                text:Dict[str, str] = request.json()
                message =text.get('error', 'Unknown error occured')
                error = HttpError(text=message, status_code=request.status_code)
                raise APIError(error) 

            return request.json()
        except Exception as e:
            print(e)
            if isinstance(e, APIError): raise e
            error = HttpError(text=f"{e}", status_code=500)
            raise APIError(error)