from tinker import TinkerClient
from tinker.core.schemas.payment import StripePaymentRequest

stripe =TinkerClient().stripe

data =StripePaymentRequest(
    amount=0.0,
    callbackUrl='...',
    currency="...",
    customerEmail="...",
    merchantReference="...",
    transactionDesc="...",
    metadata=None
)

payment =stripe.initiate(data)

print(payment)