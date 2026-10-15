"""Typed lifecycle contracts; accepted requests do not imply money moved."""

from __future__ import annotations

from typing import Literal, TypedDict

RefundReason = Literal["requested_by_customer", "duplicate", "fraudulent", "other"]
RefundStatus = Literal[
    "pending_review", "processing", "approved", "failed", "refunded", "rejected"
]
PayoutStatus = Literal["pending_approval", "approved", "processing", "paid", "rejected"]
CancellationStatus = Literal[
    "requested", "processing", "cancelled", "rejected", "outcome_unknown"
]


class _RefundRequestRequired(TypedDict):
    reason: RefundReason


class RefundRequest(_RefundRequestRequired, total=False):
    amount: float
    note: str


class _RefundRequired(TypedDict):
    id: str
    payment_id: str
    amount: float
    currency: str
    reason: RefundReason
    source: str
    status: RefundStatus
    created_at: str
    updated_at: str


class Refund(_RefundRequired, total=False):
    requested_by_app_id: str
    note: str
    execution: str
    provider_refund_id: str
    manual_reference: str
    rejection_reason: str
    failure_message: str
    reviewed_at: str
    completed_at: str


class _RefundCapabilityRequired(TypedDict):
    supported: bool
    partial: bool
    reasons: list[str]
    max_amount: float
    review_required: bool
    execution: str


class RefundCapability(_RefundCapabilityRequired, total=False):
    unavailable_reason: str


class RefundHistory(TypedDict):
    refunded_amount: float
    refundable_amount: float
    refund_capability: RefundCapability
    refunds: list[Refund]


class RefundResult(TypedDict):
    refund: Refund
    payment: PaymentDetail
    replayed: bool


class _PaymentDetailRequired(TypedDict):
    id: str
    status: str
    amount: float
    currency: str


class PaymentDetail(_PaymentDetailRequired, total=False):
    refundable_amount: float
    refund_capability: RefundCapability
    refunds: list[Refund]


class _PayoutMethodRequired(TypedDict):
    id: str
    method_type: str
    currency: str
    status: str
    is_verified: bool
    is_default: bool
    masked_destination: str


class PayoutMethod(_PayoutMethodRequired, total=False):
    provider: str


class WithdrawalFeeRule(TypedDict):
    fixed: float
    percent: float
    min: float
    max: float


class WithdrawalArrival(TypedDict):
    min: int
    max: int
    unit: str


class PayoutQuote(TypedDict):
    method_type: str
    currency: str
    amount: float | None
    fee_amount: float
    net_amount: float | None
    fee: WithdrawalFeeRule
    review_time: str
    arrival: WithdrawalArrival | None
    arrival_text: str
    configured: bool
    is_estimate: bool


class PayoutRequest(TypedDict):
    payout_method_id: str
    amount: float
    currency: str
    expected_fee_amount: float


class _PayoutRequired(TypedDict):
    id: str
    account_id: str
    payout_method_id: str
    amount: float
    currency: str
    fee_amount: float
    net_amount: float
    status: PayoutStatus
    requested_at: str
    created_at: str
    updated_at: str


class Payout(_PayoutRequired, total=False):
    source: str
    requested_by_app_id: str
    requested_by_user_id: str
    rejection_reason: str
    approved_at: str
    processing_at: str
    paid_at: str
    rejected_at: str


class PayoutResult(TypedDict):
    withdrawal: Payout
    replayed: bool


class Pagination(TypedDict):
    page: int
    per_page: int
    total: int
    total_pages: int


class PayoutPage(TypedDict):
    payouts: list[Payout]
    pagination: Pagination


class CancellationRequest(TypedDict):
    reason: str


class _CancellationRequired(TypedDict):
    id: str
    payment_id: str
    status: CancellationStatus
    reason: str
    reason_code: str
    source: str
    created_at: str
    updated_at: str


class Cancellation(_CancellationRequired, total=False):
    payment_conflict: bool
    requested_by_app_id: str
    completed_at: str
    failure_message: str


class CancellationCapability(TypedDict):
    supported: bool
    eligible: bool
    reason_code: str


class CancellationHistory(TypedDict):
    has_more: bool
    cancellations: list[Cancellation]
    capability: CancellationCapability


class CancellationResult(TypedDict):
    cancellation: Cancellation
    replayed: bool


class _PayoutFiltersRequired(TypedDict):
    pass


class PayoutFilters(_PayoutFiltersRequired, total=False):
    page: int
    per_page: int
    status: PayoutStatus
    currency: str


class _PayoutQuoteRequestRequired(TypedDict):
    payout_method_id: str
    amount: float


class PayoutQuoteRequest(_PayoutQuoteRequestRequired, total=False):
    currency: str
