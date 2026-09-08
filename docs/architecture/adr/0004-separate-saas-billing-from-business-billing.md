# ADR 0004 — Separate SaaS Billing from Business Billing

- Status: Accepted
- Date: 2026-09-06

## Context

NovaScale already contains business billing capabilities used by logistics companies to manage invoices and related financial workflows for their own customers.

As NovaScale evolves into a SaaS product, the platform itself also needs to charge each Tenant for using NovaScale.

These are two different business domains:

- Business billing: a Tenant charges its customers for logistics services.
- SaaS billing: a Tenant pays NovaScale for access to the platform.

Combining these concepts into the same domain model would mix customer-facing logistics finance with NovaScale's own commercial subscription lifecycle.

The SaaS billing model will also need concepts that do not naturally belong to logistics business billing, such as subscription plans, trials, renewals, SaaS entitlements, failed subscription payments, cancellation, and account suspension.

## Decision

NovaScale will treat SaaS billing and business billing as separate bounded contexts.

The existing billing domain will continue to represent financial operations performed by a Tenant for its own customers.

A separate SaaS subscription domain will represent the commercial relationship between a Tenant and the NovaScale platform.

The SaaS subscription domain will own concepts such as:

- Subscription.
- Plan.
- Subscription status.
- Billing lifecycle.
- Trial state when supported.
- Renewal and cancellation state.
- SaaS entitlements.
- Usage limits or metering when required.

A Tenant, rather than an individual employee User, will be the primary subscriber to NovaScale.

The Tenant Owner will be responsible for managing the company subscription according to the authorization rules defined by the product.

External payment providers must remain infrastructure concerns behind application-defined ports or interfaces.

NovaScale domain and application code must not depend directly on a specific payment provider such as Stripe.

## Alternatives considered

### Reuse the existing billing module for SaaS subscriptions

NovaScale could place SaaS subscription functionality inside the existing billing module.

This was not selected because the two domains have different actors, terminology, workflows, and responsibilities.

Business billing represents money owed to a logistics company by its customers.

SaaS billing represents money owed to NovaScale by a Tenant.

Combining them would create unnecessary coupling and ambiguous domain models.

### Attach subscription information directly to User

Each User could independently subscribe to NovaScale.

This was not selected because NovaScale is a B2B SaaS platform where the company, represented by the Tenant, is the customer account.

Employees should normally consume capabilities provided by the Tenant's subscription rather than maintain individual NovaScale subscriptions.

### Couple the application directly to one payment provider

The SaaS billing implementation could directly use a provider SDK throughout the application layer.

This may be faster initially but would couple subscription business logic to a specific external service.

It was not selected because payment providers are infrastructure dependencies and may change over time.

## Consequences

### Positive

- Business billing and NovaScale platform billing remain conceptually clear.
- Existing invoice workflows do not need to absorb SaaS-specific concepts.
- Subscription logic can evolve independently from logistics billing.
- Tenant-level plans and entitlements can be modeled cleanly.
- Employees can inherit SaaS capabilities from their Tenant without individual subscriptions.
- External payment providers can be replaced or tested through adapters.
- The architecture avoids coupling core subscription rules to a specific payment vendor.

### Negative

- NovaScale will maintain two financial domains with different responsibilities.
- Developers must use precise terminology to avoid confusing customer invoices with SaaS subscription charges.
- Subscription events and payment-provider webhooks introduce additional lifecycle and failure-handling complexity.
- Cross-domain reporting may require explicit integration between SaaS operations and platform administration.