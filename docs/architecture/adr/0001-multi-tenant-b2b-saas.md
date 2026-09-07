# ADR 0001 — Keep NovaScale as a Multi-Tenant B2B SaaS

- Status: Accepted
- Date: 2026-09-06

## Context

NovaScale is a B2B shipping and logistics platform designed to serve logistics companies and their employees.

The existing architecture already models organizations as tenants and separates a user's identity from their relationship with an organization through memberships, roles, and permissions.

Several product models were considered for NovaScale:

- A system dedicated to a single logistics company.
- A dedicated NovaScale deployment for each customer.
- A shared multi-tenant SaaS platform serving multiple logistics companies.

NovaScale is also intended to demonstrate production-oriented software engineering practices, including multi-tenancy, authorization, tenant isolation, SaaS lifecycle management, integrations, observability, and AI capabilities.

The product direction therefore needs to be explicit before expanding the V2 identity, onboarding, subscription, and authorization models.

## Decision

NovaScale will remain a multi-tenant B2B SaaS platform.

Each logistics company using NovaScale will be represented by a Tenant.

A User represents a person's identity in NovaScale and is not itself owned by a specific Tenant.

A Membership represents the relationship between a User and a Tenant.

Roles and permissions are applied in the context of that membership rather than globally to the User.

A user may belong to more than one Tenant when a valid membership exists for each Tenant.

Tenant data must remain isolated from other tenants throughout the application, including business data, documents, background processing, and AI/RAG capabilities.

The V2 SaaS model will build on these boundaries rather than replacing them.

## Alternatives considered

### Single-company system

NovaScale could be deployed as an internal system for one logistics company.

This would simplify onboarding and remove much of the visible tenant lifecycle.

It was not selected because it would unnecessarily limit NovaScale to one organization and would remove important SaaS and multi-tenancy capabilities that the project is intended to support.

### Dedicated deployment per customer

Each customer could receive an independent NovaScale deployment with its own infrastructure and database.

This provides strong infrastructure-level isolation but increases deployment, maintenance, monitoring, upgrade, and operational costs for every customer.

It was not selected as the default model.

Dedicated deployments may still be considered in the future for enterprise customers when contractual, regulatory, performance, or isolation requirements justify them.

### Shared multi-tenant SaaS

Multiple logistics companies share the NovaScale application infrastructure while their data and authorization boundaries remain isolated by Tenant.

This model was selected because it supports centralized product development and operations while preserving the ability to evolve toward dedicated infrastructure for specific customers if required.

## Consequences

### Positive

- NovaScale can serve multiple logistics companies from one product platform.
- Existing Tenant, Membership, Role, and Permission boundaries remain useful.
- Users can participate in multiple organizations without duplicating their identity.
- SaaS subscriptions and entitlements can be associated with the Tenant rather than individual employees.
- The architecture can support both shared infrastructure and future dedicated enterprise deployments.
- Tenant-aware AI, RAG, documents, background jobs, and integrations can evolve consistently around the same tenant boundary.
- The project demonstrates realistic B2B SaaS architecture and security concerns.

### Negative

- Every tenant-owned resource must enforce tenant isolation correctly.
- Authorization is more complex than in a single-company application.
- Background jobs, documents, AI retrieval, webhooks, caching, and future integrations must preserve tenant context.
- Security testing must explicitly cover cross-tenant access attempts.
- SaaS lifecycle concerns such as onboarding, subscriptions, entitlements, suspension, and tenant deletion must be implemented.
- Operational monitoring may need to understand usage and failures at both platform and tenant levels.