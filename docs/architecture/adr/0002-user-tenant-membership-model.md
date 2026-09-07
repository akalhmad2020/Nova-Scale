# ADR 0002 — Separate User Identity from Tenant Membership

- Status: Accepted
- Date: 2026-09-06

## Context

NovaScale is a multi-tenant B2B SaaS platform where a person may interact with one or more logistics companies.

A person's identity and their relationship with a company are different concepts.

For example, the same person could be an Owner in one Tenant, an Operations user in another Tenant, and have no access to any other Tenant.

Attaching a Tenant or a global Role directly to the User would mix identity, organization membership, and authorization concerns.

NovaScale therefore needs an identity model that preserves these boundaries and supports tenant-scoped authorization.

## Decision

NovaScale will model identity and organization access using the following relationship:

User → Membership → Tenant

A User represents the identity of a person.

A Tenant represents a logistics company using NovaScale.

A Membership represents the relationship between a User and a Tenant.

Roles and permissions that determine what a user can do inside a Tenant are evaluated in the context of the Membership rather than as global properties of the User.

A User may have memberships in multiple Tenants.

Having a NovaScale User account alone does not grant access to a Tenant.

Access to tenant-owned resources requires a valid Membership in that Tenant together with the required authorization.

Tenant context must be established from trusted authenticated and membership information and must not be trusted solely from client-provided identifiers.

## Alternatives considered

### Store tenant_id directly on User

Each User could belong to exactly one Tenant through a tenant_id column.

This is simpler but tightly couples identity to a single organization and prevents legitimate multi-organization membership without redesigning the identity model.

It was not selected.

### Store a global role directly on User

A User could have a role such as Owner, Admin, Operations, or Viewer directly on their account.

This was not selected because roles in NovaScale describe what a person can do within a particular Tenant.

A person may have different responsibilities in different Tenants, so a global role would model authorization incorrectly.

### Separate User and Membership

User identity remains independent while Membership connects the User to a Tenant and provides the context for tenant-scoped authorization.

This model was selected because it preserves clear domain boundaries and supports multi-tenant B2B authorization without duplicating user identities.

## Consequences

### Positive

- User identity remains independent from any specific logistics company.
- A User can legitimately belong to multiple Tenants.
- The same User can have different authorization contexts in different Tenants.
- Tenant access can be revoked by changing or removing Membership without deleting the User identity.
- Invitations can create or establish Memberships without treating an invitation as a User account.
- The model supports future organization and team management capabilities.
- Authentication and tenant authorization remain separate concerns.

### Negative

- Authorization requires resolving Membership in addition to authenticating the User.
- Queries and application services must consistently preserve tenant context.
- Membership lifecycle management introduces additional states and business rules.
- Tests must cover users with memberships in multiple Tenants and cross-tenant access attempts.