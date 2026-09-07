# ADR 0011 — Establish Trusted Tenant Context and Enforce Tenant Isolation Server-Side

- Status: Accepted
- Date: 2026-09-07

## Context

NovaScale is a multi-tenant B2B SaaS platform.

Many application resources belong to a Tenant, including data such as:

- Shipments.
- Customers.
- Locations.
- Documents.
- Invoices.
- Notifications.
- AI and RAG content.
- Future integrations and background jobs.

Requests may contain a tenant identifier through mechanisms such as:

- URL path parameters.
- Query parameters.
- Request bodies.
- Frontend state.
- Cookies used for user interface context.

However, client-provided tenant identifiers cannot by themselves establish authorization.

For example, a request such as:

GET /api/v1/tenants/{tenant_id}/shipments/{shipment_id}

does not prove that the authenticated User belongs to the requested Tenant.

Trusting the tenant_id directly would allow an attacker to replace the identifier with another Tenant's identifier and potentially access another customer's data.

NovaScale therefore requires a trusted tenant context derived from authenticated identity and validated Membership rather than from client input alone.

## Decision

NovaScale will establish tenant context server-side using authenticated identity and validated Tenant Membership.

Client-provided tenant identifiers may identify the requested Tenant, but they will not be treated as proof of authorization.

For tenant-scoped requests, the backend must verify that:

- The User is authenticated.
- The requested Tenant exists when required by the use case.
- The User has a valid Membership in that Tenant.
- The Membership is in a state that permits access.
- The required role or permission is satisfied.
- Any required SaaS entitlement is satisfied.
- The requested resource belongs to the same Tenant.

Conceptually:

Authenticated User
        +
Requested Tenant
        ↓
Validate Membership
        ↓
Trusted Tenant Context
        ↓
Authorization
        ↓
Tenant-scoped resource access

Tenant-owned repositories and application services must preserve tenant boundaries explicitly.

Resource lookups should normally include Tenant ownership in the query rather than loading a resource globally and relying only on a later comparison.

For example, the preferred conceptual lookup is:

find shipment
where shipment.id = requested_shipment_id
and shipment.tenant_id = trusted_tenant_id

rather than:

find shipment by shipment_id globally
then trust the caller to use the correct Tenant

The backend remains the security authority.

Frontend tenant selection mechanisms, including any active-tenant cookie, are navigation and user-experience state only and must never grant access by themselves.

Tenant context used by background jobs, outbox consumers, AI tools, RAG retrieval, documents, webhooks, and integrations must also be established from trusted persisted data rather than arbitrary external input.

## Alternatives considered

### Trust tenant_id from the request

NovaScale could treat the Tenant identifier in the URL or request body as the active authorization context.

This was not selected because the client controls that value and can modify it.

A tenant identifier identifies a resource boundary but does not prove membership in that boundary.

### Store one active Tenant directly on User

NovaScale could maintain a single current Tenant on the User account and use it for authorization.

This was not selected because Users may legitimately belong to multiple Tenants.

It would also mix persistent identity state with request-specific organization context.

### Use frontend tenant selection as authorization

The frontend could prevent users from selecting Tenants they do not belong to and assume requests are therefore safe.

This was not selected because client-side checks are not security boundaries and can be bypassed.

### Validate Membership server-side

The backend derives trusted tenant context from the authenticated User and validated Membership, and tenant-owned resource queries preserve that boundary.

This model was selected because it provides an explicit and consistent security boundary for a multi-tenant SaaS system.

## Consequences

### Positive

- Client-controlled identifiers cannot independently grant Tenant access.
- Cross-tenant authorization rules are explicit.
- Users can safely participate in multiple Tenants.
- Repository queries can enforce Tenant ownership close to the data-access boundary.
- Backend authorization remains independent of frontend state.
- The same Tenant security model can be applied to API requests, background jobs, AI, RAG, documents, and integrations.
- Security tests can explicitly exercise cross-tenant access attempts.

### Negative

- Tenant-scoped requests require Membership resolution and authorization checks.
- Repository and use-case APIs must consistently carry trusted Tenant context.
- Developers must avoid global resource lookups that accidentally bypass Tenant ownership.
- Background processing must preserve Tenant identity alongside work items and events.
- Multi-tenant security requires dedicated regression tests and review discipline.