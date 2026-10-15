# Merchant lifecycle APIs (unreleased)

Added app-scoped refund requests/history, verified merchant withdrawal methods/quotes/requests/pages, and durable checkout-cancellation requests/history. Mutations use caller-supplied idempotency headers through the existing shared transport. Typed models retain review, rejected and uncertain states; structured errors retain persisted request IDs and fee-conflict details. Signed cancellation events retain their own resource without creating a payment transaction.

Compatibility: existing payment initiation/query, subscription and webhook methods remain available. App withdrawal permission is owner-controlled and defaults off. Backend routes must deploy before package publication. Sandbox parity, financial integration/recovery evidence and deployment are release gates; fixture checks do not establish deployed sandbox parity. No package has been published by this change.

Contract validation uses canonical fixtures from `tinker-payments-openapi/fixtures`, with checked-in snapshots for standalone CI and drift checks when the sibling repository exists. See README for operation examples and recovery behavior.
