# PR-2 Subscription lifecycle

NovaScale separates domain billing (customer invoices) from the SaaS subscription that controls platform capabilities.

## Portfolio mode

`BILLING_PROVIDER=portfolio` is the current default. Starter and Professional are self-service plans and activate immediately without payment so portfolio reviewers can exercise NovaScale AI, RAG, and controlled agent actions.

Enterprise remains sales-assisted.

## Stripe-ready boundary

Plan changes are executed through the `SubscriptionProvider` application port. The current `PortfolioSubscriptionProvider` is an adapter that returns an active subscription immediately.

A future Stripe adapter should implement the same port and can replace instant activation with checkout + webhook-confirmed synchronization. Existing `TenantSubscription` provider/customer/subscription fields and `SyncSubscription` remain the source for provider-synchronized state.

When Stripe is added:

1. implement `StripeSubscriptionProvider`;
2. update the SaaS dependency factory for `BILLING_PROVIDER=stripe`;
3. change signup Professional provisioning from immediate portfolio activation to Stripe checkout;
4. update subscription state only from trusted Stripe webhook events via `SyncSubscription`;
5. keep entitlements derived only from the effective subscription state.

No database migration is required for this portfolio-mode PR.
