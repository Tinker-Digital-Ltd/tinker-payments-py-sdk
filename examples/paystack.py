from tinker import TinkerClient
from tinker.core.schemas.payment import PaystackPaymentRequest

paystack =TinkerClient().paystack

data =PaystackPaymentRequest(
    amount=0.0,
    callbackUrl='...',
    currency="KES",
    customerEmail="...",
    merchantReference="...",
    transactionDesc="...",
    metadata=None
)

payment =paystack.initiate(data)

print(payment)