from typing import Optional
from pydantic import BaseModel, Field

class HttpError(BaseModel):
    status_code: Optional[int] = Field(None, description="Error Status Code")
    text: Optional[str] = Field(None, description="Error message")
