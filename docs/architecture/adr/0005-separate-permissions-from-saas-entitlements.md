# ADR 0005 — Separate User Permissions from SaaS Entitlements

- Status: Accepted
- Date: 2026-09-06

## Context

NovaScale already uses roles and permissions to determine what a User is allowed to do inside a Tenant.

As NovaScale evolves into a SaaS product, Tenants will also subscribe to plans that determine which product capabilities are available to the organization.

These are different concerns.

Permissions answer:

- Is this User allowed to perform this action inside the Tenant?

SaaS entitlements answer:

- Has this Tenant purchased or been granted access to this product capability?

For example, a Tenant Owner may have permission to use AI features, but the Tenant's current subscription plan may not include the AI Assistant.

Likewise, a Tenant may have access to a feature through its subscription, while a particular employee may not have permission to use it.

Combining permissions and entitlements would mix user authorization with SaaS product packaging and subscription state.

## Decision

NovaScale will model user permissions and SaaS entitlements as separate authorization dimensions.

Permissions will remain responsible for user-level authorization within the Tenant.

Entitlements will represent product capabilities available to the Tenant through its SaaS subscription or other platform-level grants.

Access to a subscription-controlled capability may therefore require both:

- A valid Tenant Membership with the required permission.
- An active Tenant entitlement for the requested capability.

The effective access rule will conceptually follow:

Membership valid
+
Permission granted
+
Required Tenant entitlement enabled
=
Access allowed

Entitlements will belong to the SaaS subscription and platform control-plane domain rather than the existing RBAC identity model.

Application services that depend on subscription-controlled capabilities must enforce entitlements on the server side.

Frontend entitlement checks may improve user experience but must not be treated as a security boundary.

## Alternatives considered

### Represent subscription features as permissions

NovaScale could create permissions such as `ai.use`, `webhooks.use`, or `advanced_reports.use` and add or remove them based on the Tenant's subscription plan.

This was not selected because permissions describe what a User is authorized to do, while subscription features describe what the Tenant has purchased.

Mixing them would make it difficult to distinguish authorization policy from commercial product packaging.

### Represent permissions as subscription entitlements

NovaScale could make plan entitlements determine all access to features without separate user-level permissions.

This was not selected because a Tenant having access to a feature does not mean every employee should automatically be allowed to use it.

### Enforce entitlements only in the frontend

The frontend could hide unavailable features based on the Tenant's subscription.

This was not selected because clients cannot be trusted as authorization boundaries.

Server-side application logic must enforce subscription-controlled access.

## Consequences

### Positive

- User authorization and SaaS product packaging remain conceptually separate.
- The same subscription feature can be selectively available to different roles.
- Subscription plans can evolve without modifying the RBAC permission model.
- Roles and permissions can evolve without changing SaaS commercial packaging.
- Backend authorization remains the source of truth.
- Frontend UI can clearly distinguish unavailable plan features from insufficient user permissions.
- Future trials, promotional grants, enterprise overrides, and temporary entitlements can be modeled without altering user roles.

### Negative

- Feature access may require evaluating both authorization and entitlement state.
- Application services must know when a capability is subscription-controlled.
- Tests must cover combinations of permission and entitlement state.
- The frontend may need to explain different denial reasons, such as insufficient permission versus unavailable plan feature.
- Entitlement caching or synchronization may become necessary if the subscription system later depends on an external billing provider.