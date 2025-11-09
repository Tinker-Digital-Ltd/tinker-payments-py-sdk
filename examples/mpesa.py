from tinker import TinkerClient
from tinker.core.schemas.payment import MpesaPaymentRequest

mpesa =TinkerClient().mpesa

data =MpesaPaymentRequest(
    amount=0.0,
    callbackUrl='...',
    currency="KES",
    customerPhone="...",
    merchantReference="...",
    transactionDesc="...",
    metadata=None
)

# Initiate Payment
payment =mpesa.initiate(data)
print(payment)

# Query Payment Status
status =mpesa.query(payment.payment_reference)
print(status)