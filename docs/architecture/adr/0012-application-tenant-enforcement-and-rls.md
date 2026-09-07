# ADR 0012 — Use Application-Level Tenant Enforcement and Evaluate PostgreSQL RLS as Defense in Depth

- Status: Accepted
- Date: 2026-09-07

## Context

NovaScale is a multi-tenant B2B SaaS platform where tenant isolation is a critical security boundary.

ADR 0011 establishes that Tenant identifiers supplied by clients are identifiers rather than authorization evidence.

The application must derive trusted Tenant context from authenticated identity and validated Membership, and tenant-owned resource access must preserve that context.

NovaScale currently enforces these boundaries primarily through the application and repository layers.

For example, tenant-owned resource queries should conceptually include both the resource identifier and trusted Tenant identifier:

SELECT ...
FROM shipments
WHERE id = :shipment_id
  AND tenant_id = :trusted_tenant_id

PostgreSQL also provides Row-Level Security (RLS), which can enforce database policies restricting which rows a database session is allowed to access.

RLS could provide an additional isolation boundary if application code accidentally executes an insufficiently tenant-scoped query.

However, RLS also introduces additional complexity around connection pooling, transaction-scoped Tenant context, migrations, background workers, administrative operations, testing, debugging, and privileged database roles.

NovaScale therefore needs to distinguish between its primary authorization architecture and optional database-level defense in depth.

## Decision

NovaScale will continue to treat application-level Tenant enforcement as the primary tenant authorization mechanism.

Trusted Tenant context will be established by the application from authenticated identity and validated Membership.

Application services and repositories must explicitly preserve Tenant ownership boundaries.

Tenant-owned repository operations should be designed so that Tenant context is required where practical.

PostgreSQL RLS will not replace application authorization.

In particular, RLS must not be responsible for deciding:

- Whether a User has a valid Membership.
- Which Role the Membership has.
- Whether a Permission is granted.
- Whether the Tenant has a required SaaS Entitlement.
- Whether a business operation is valid.

These remain application-level responsibilities.

PostgreSQL RLS may be introduced as an additional defense-in-depth mechanism for selected tenant-owned tables after V2 evaluates the operational and implementation consequences.

Before enabling RLS, NovaScale must define and test:

- How trusted Tenant context is propagated to the database connection or transaction.
- How this behaves with SQLAlchemy asynchronous connection pooling.
- How context is cleared or reset before a connection is reused.
- How background workers establish Tenant context.
- How migrations and maintenance operations bypass policies safely when required.
- How platform administration and support workflows interact with RLS.
- How tests verify both application-level and database-level isolation.
- Which database roles are permitted to bypass RLS.
- How accidental cross-Tenant queries fail.

If RLS is introduced, Tenant context must originate from trusted server-side state.

Client-provided tenant identifiers must never be copied into database session context without application-level Membership validation.

The intended security model would therefore be:

Authentication
      ↓
Membership validation
      ↓
Trusted Tenant Context
      ↓
Application authorization
      ↓
Tenant-scoped repository access
      ↓
Optional PostgreSQL RLS
      ↓
Tenant-owned rows

RLS is therefore considered a potential additional security boundary, not a substitute for correct application design.

## Alternatives considered

### Application-level enforcement only

NovaScale could rely exclusively on application services and tenant-scoped repository queries.

This is simpler operationally and keeps authorization behavior explicit in application code.

It remains the current primary enforcement model.

The main disadvantage is that a programming mistake that executes an unscoped database query may bypass the intended Tenant boundary.

### PostgreSQL RLS as the primary authorization system

NovaScale could move most Tenant authorization responsibility into PostgreSQL policies.

This was not selected.

Database row policies do not naturally represent the complete NovaScale authorization model, including Membership lifecycle, Roles, Permissions, SaaS Entitlements, and business rules.

Moving these concerns into database policies would also distribute authorization logic between the application and database in ways that are harder to reason about.

### Application enforcement plus PostgreSQL RLS

NovaScale could preserve application-level authorization while using RLS as an additional database-level isolation boundary.

This provides defense in depth against some classes of accidental unscoped queries.

This remains a valid V2 hardening option, but it should only be enabled after its interaction with connection pooling, workers, migrations, privileged operations, and testing is explicitly designed and verified.

## Consequences

### Positive

- Application authorization remains explicit and understandable.
- Membership, Permission, Entitlement, and business rules remain in the appropriate application/domain layers.
- Repository APIs can continue to make Tenant ownership explicit.
- NovaScale does not introduce RLS complexity before understanding its operational consequences.
- RLS remains available as an additional isolation boundary.
- The architecture supports defense in depth without treating the database as the complete authorization system.
- The decision can be revisited using security testing and operational evidence.

### Negative

- Application code remains responsible for consistently applying Tenant-scoped access.
- Until RLS is introduced, an incorrectly implemented unscoped query may have fewer database-level protections.
- Adding RLS later will require careful integration with existing repositories and transaction handling.
- If RLS is introduced, connection-pool context leakage becomes a security concern that must be tested explicitly.
- Administrative and background workflows become more complicated under RLS.
- Developers must understand both application authorization and database isolation if both mechanisms are eventually enabled.