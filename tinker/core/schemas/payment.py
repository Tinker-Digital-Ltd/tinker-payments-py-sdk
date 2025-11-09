from typing import TypeVar
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any



class PaymentRequest(BaseModel):
    amount: float = Field(..., description="Amount charged")
    currency: str = Field(..., description="Currency code (e.g. KES, USD)")
    merchantReference: str = Field(..., description="Unique merchant reference or order ID")
    transactionDesc: str = Field(..., description="Description of the payment transaction")
    callbackUrl: str = Field(..., description="Webhook URL for payment status updates")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata about the transaction")

T = TypeVar("T", bound=PaymentRequest)

class PaymentResponse(BaseModel):
    payment_reference: str = Field(..., description="Unique payment reference from the gateway")
    status: str = Field(..., description="Current payment status (e.g. pending, completed, failed)")
    authorization_url: Optional[str] = Field(None, description="URL to authorize the payment, if applicable")

class PaymentQueryRequest(BaseModel):
    payment_reference: str = Field(..., description="Unique payment reference from the gateway")
    gateway: str = Field(..., description="Payment gateway provider (Mpesa, Paystack, Stripe, Ayden)")

class PaymentQueryResponse(BaseModel):
    id: str = Field(..., description="Unique payment reference from the gateway")
    status: str = Field(..., description="Unique payment reference from the gateway")
    reference: str = Field(..., description="Unique payment reference from the gateway")
    amount: float = Field(..., description="Unique payment reference from the gateway")
    currency: str = Field(..., description="Unique payment reference from the gateway")
    paid_at: str = Field(..., description="Unique payment reference from the gateway")
    created_at: str = Field(..., description="Unique payment reference from the gateway")
    channel: str = Field(..., description="Unique payment reference from the gateway")


class MpesaPaymentRequest(PaymentRequest):
    customerPhone: str = Field(..., description="Customer phone number")

class CardPaymentRequest(PaymentRequest):
    customerEmail: str = Field(..., description="Customer email address for card payment")
