# ADR 0006 — Keep External Providers Behind Application Ports

- Status: Accepted
- Date: 2026-09-07

## Context

NovaScale depends on external systems for several capabilities, including:

- AI model providers.
- Email delivery.
- SaaS payment processing.
- Object storage.
- Carrier integrations.
- Webhook delivery infrastructure.
- Potential future messaging or notification providers.

These external systems are implementation details and may change because of cost, reliability, regional availability, customer requirements, vendor limitations, or product evolution.

Coupling NovaScale application logic directly to vendor-specific SDKs or APIs would make business logic harder to test, harder to evolve, and more expensive to migrate.

NovaScale already applies this approach in the AI layer by defining application-owned abstractions and placing provider-specific integrations in infrastructure adapters.

## Decision

NovaScale application and domain layers will depend on NovaScale-owned ports or interfaces for external capabilities.

Vendor-specific implementations will live in infrastructure adapters.

The general dependency direction will be:

Application / Domain
        ↓
NovaScale Port
        ↓
Infrastructure Adapter
        ↓
External Provider

Examples include:

- LLMProvider → Ollama adapter, future hosted AI adapters.
- EmbeddingProvider → Ollama embedding adapter.
- PaymentProvider → future Stripe or alternative adapter.
- EmailSender → future email service adapter.
- ObjectStorage → S3-compatible or other storage adapter.
- CarrierProvider → DHL, FedEx, UPS, or local carrier adapters.

External provider SDK types must not leak into core domain models or application use-case interfaces unless there is a strong and explicitly documented reason.

Provider-specific configuration, authentication, retries, error translation, SDK usage, and transport concerns belong in infrastructure.

Application-facing ports should model NovaScale business needs rather than mirror an external provider API exactly.

## Alternatives considered

### Use provider SDKs directly inside application services

Application services could import and call external provider SDKs directly.

This may reduce initial implementation time but would tightly couple business workflows to vendor-specific APIs and data models.

It was not selected because it would make testing, replacement, and failure handling more difficult.

### Build a fully generic abstraction for every possible provider

NovaScale could design highly generic interfaces intended to support every future provider capability in advance.

This was not selected because overly generic abstractions tend to become complex and speculative.

Ports should be designed around current NovaScale use cases and extended when real requirements appear.

### Use infrastructure adapters behind application-owned ports

NovaScale defines the capabilities it needs while infrastructure adapters translate those capabilities to external services.

This model was selected because it keeps dependency direction clear, improves testability, and reduces vendor lock-in without over-generalizing the architecture.

## Consequences

### Positive

- Business logic remains independent from vendor SDKs.
- External services can be replaced with less impact on application code.
- Tests can use fakes or controlled adapters instead of real external services.
- Provider-specific failures can be translated into NovaScale-defined errors.
- Configuration and credentials remain isolated in infrastructure.
- The same architectural pattern can be reused consistently across AI, payments, email, storage, and carriers.
- Local development can use lightweight adapters while production uses managed providers.

### Negative

- Additional interfaces and adapter code must be maintained.
- Provider-specific capabilities may require extending application ports.
- Poorly designed abstractions can hide useful provider features or become unnecessarily generic.
- Developers must deliberately decide which concerns belong in the application contract and which remain provider-specific.