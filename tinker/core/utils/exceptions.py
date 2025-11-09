from tinker.core.schemas import HttpError

class APIError(Exception):
    def __init__(self, response:HttpError):
        self.status_code = response.status_code
        self.message = response.text
        super().__init__(f"API Error {self.status_code}: {self.message}")

class UnsupportedGatewayError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(f"Invalid Gateway: {self.message}")

class GatewayNameRequiredError(Exception):
    def __init__(self, message: str ="Gateway name was not provided"):
        self.message = message
        super().__init__(f"Gateway Required: {self.message}")