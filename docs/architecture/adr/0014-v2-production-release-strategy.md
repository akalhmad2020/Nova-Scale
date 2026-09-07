# ADR 0014 — Use NovaScale V2 as the First Production Release

- Status: Accepted
- Date: 2026-09-07

## Context

NovaScale V1 established a substantial technical foundation for the platform.

The existing system includes capabilities such as:

- A Modular Monolith backend architecture.
- PostgreSQL persistence and migrations.
- Multi-tenant identity and authorization foundations.
- Core logistics and financial domains.
- Transactional outbox infrastructure.
- Production-oriented configuration and Docker support.
- Automated quality gates and integration tests.
- A Next.js frontend using a BFF authentication architecture.
- AI, RAG, and Agent capabilities.
- Provider abstractions for external AI infrastructure.

V1 demonstrates that the major architectural layers and end-to-end workflows function together.

However, deploying a technically functional application is different from operating a production SaaS product.

Before NovaScale is treated as a public production service, additional product and operational capabilities are required, including:

- Company onboarding.
- Invitation-based employee onboarding.
- SaaS subscription architecture.
- Tenant entitlements.
- Stronger tenant-isolation verification.
- Authentication and browser-security hardening.
- Production email delivery.
- Reliable notification and webhook processing.
- Production observability.
- Backup and restore procedures.
- Deployment security.
- Secrets management.
- Migration safety.
- End-to-end and security regression testing.
- Operational lifecycle management.

Releasing V1 publicly and adding these capabilities afterward would expose the platform before its SaaS and operational lifecycle is sufficiently mature.

## Decision

NovaScale V1 will be treated as the completed technical and product-development baseline.

NovaScale V2 will be developed as the first version intentionally prepared for public production deployment.

The target public production release will be:

NovaScale v2.0.0

V2 development will prioritize production-critical SaaS and security capabilities before optional feature expansion.

The V2 release process will include explicit production-readiness gates covering areas such as:

- SaaS onboarding and Tenant lifecycle.
- Membership and invitation lifecycle.
- Subscription and entitlement behavior.
- Tenant isolation.
- Authentication and authorization.
- Browser security.
- AI security.
- Background processing reliability.
- Production email and external integrations.
- Observability and error reporting.
- Database backup and restore.
- Migration safety.
- Secrets and production configuration.
- HTTPS and network exposure.
- Automated testing.
- Security regression testing.
- CI/CD.
- Operational documentation.

A feature being implemented does not automatically make it production-ready.

Production readiness requires that its security, failure behavior, observability, deployment behavior, and recovery characteristics are also understood and verified.

NovaScale will prefer Continuous Delivery for the initial production lifecycle.

Production deployment may require explicit human approval after automated CI, build, staging, migration, and smoke-test gates succeed.

Automatic Continuous Deployment to production is not required for the initial v2.0.0 release.

The final production release will only be tagged after the V2 production-readiness gate is completed.

## Alternatives considered

### Deploy V1 immediately

NovaScale could deploy the existing V1 baseline publicly and add SaaS and operational hardening incrementally afterward.

This was not selected because technical completeness does not imply sufficient production readiness.

Important SaaS lifecycle, security, recovery, and operational capabilities still need to be designed and verified.

### Continue development without a defined production target

NovaScale could continue adding capabilities indefinitely and decide later when the application is ready for production.

This was not selected because it encourages uncontrolled scope growth and makes production readiness difficult to measure.

A defined v2.0.0 target provides a concrete release boundary.

### Treat V2 as a feature-only release

V2 could primarily add more logistics and AI functionality.

This was not selected because the highest-value work before public launch is not simply increasing feature count.

Production SaaS lifecycle, security, reliability, and operations are higher priorities.

### Prepare V2 explicitly for production

V1 remains the strong engineering baseline while V2 adds the product, security, operational, and reliability capabilities required for a public SaaS launch.

This model was selected because it provides a clear transition from a functioning system to an intentionally production-operated product.

## Consequences

### Positive

- NovaScale has a clear production milestone.
- V1 remains a meaningful completed engineering baseline.
- V2 work can be prioritized according to production risk rather than feature count.
- Security and operations are treated as product requirements rather than last-minute deployment tasks.
- Production readiness can be verified through explicit gates.
- The project can demonstrate the full lifecycle from architecture through deployment and operations.
- The resulting portfolio case study can explain both implementation decisions and production trade-offs.

### Negative

- Public deployment is intentionally delayed until V2 readiness criteria are satisfied.
- Some attractive feature work may be postponed behind security and operational priorities.
- V2 requires work that may not be immediately visible in the user interface, such as backup verification, migration safety, observability, and security testing.
- Production readiness requires ongoing operational work even after v2.0.0 is released.