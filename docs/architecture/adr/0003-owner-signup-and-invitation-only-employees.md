# ADR 0003 — Public Signup Creates Tenant Owners and Employees Join by Invitation

- Status: Accepted
- Date: 2026-09-06

## Context

NovaScale is a multi-tenant B2B SaaS platform where each Tenant represents a logistics company.

The product needs a clear distinction between:

- A person who starts a new company account on NovaScale.
- An employee who joins an existing company.

Allowing any authenticated User to freely create Tenants would blur this distinction and would make employee accounts capable of provisioning new customer organizations without going through the intended SaaS onboarding flow.

NovaScale also needs a clear ownership model because the Tenant Owner is responsible for the company account and, in the SaaS model, is the primary party associated with the Tenant's subscription and billing lifecycle.

## Decision

Public signup in NovaScale will represent the onboarding of a new customer company.

A successful public signup will create:

- A User.
- A Tenant.
- A Membership connecting the User to that Tenant.
- An Owner role for that Membership.

The public signup flow therefore creates the initial Owner of a newly provisioned Tenant.

Employees will not use the public signup flow to independently create NovaScale company accounts.

Employees will join an existing Tenant through an invitation flow.

An invitation will identify the intended Tenant, invited email address, and role or authorization context.

If the invited person does not yet have a NovaScale User account, the invitation flow may allow them to create one and then create the Membership in the existing Tenant.

If the invited person already has a NovaScale User account, they will authenticate and accept the invitation to create the Membership.

A normal authenticated User will not receive a general capability to create additional Tenants from inside the application.

The ability to belong to multiple Tenants remains supported when valid Memberships exist, for example through invitations from multiple organizations.

## Alternatives considered

### Allow every User to create Tenants

Any authenticated User could create one or more Tenants from inside NovaScale.

This provides flexibility but weakens the distinction between customer onboarding and employee membership.

It would also allow employees to provision organizations without going through the intended SaaS customer lifecycle.

It was not selected.

### Create employees directly without invitations

Tenant administrators could create employee User accounts directly.

This was not selected as the primary onboarding model because invitations provide a clearer ownership boundary for credentials and allow the invited person to establish or authenticate their own identity.

Administrative account creation may be reconsidered later for enterprise-specific requirements.

### Public signup for all Users, followed by optional Tenant creation

All people could create standalone NovaScale User accounts and later either create or join a Tenant.

This was not selected because NovaScale is primarily a B2B product rather than a consumer identity platform.

The public registration path should therefore represent company onboarding rather than creation of unused standalone accounts.

## Consequences

### Positive

- Public signup has a clear business meaning: create a new customer company.
- The initial Tenant Owner is established consistently.
- Employee onboarding is clearly separated from company provisioning.
- Employees cannot create additional Tenants simply because they have a NovaScale User account.
- The model aligns Tenant ownership with the future SaaS subscription lifecycle.
- Invitation-based onboarding provides a controlled path for adding employees.
- Existing User identities can join additional Tenants without creating duplicate accounts.
- Tenant switching remains useful for Users who legitimately belong to multiple organizations.

### Negative

- Registration and invitation acceptance require separate application flows.
- Invitation lifecycle management becomes a required product capability.
- Edge cases must be handled for expired, reused, mismatched, and duplicate invitations.
- Account recovery and email verification must work correctly with both public signup and invitation-based registration.
- Changing the ownership model later would require explicit product and migration decisions.