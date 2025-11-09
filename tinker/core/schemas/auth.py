from pydantic import BaseModel, Field

class Token(BaseModel):
    token: str = Field(..., description="JWT access token")
    expires_in: int = Field(..., description="Token expiry duration in seconds")
    token_type: str = Field("Bearer", description="Token type, usually 'Bearer'")


class AuthRequest(BaseModel):
    credentials: str = Field(..., description="base64(pk:sk)")