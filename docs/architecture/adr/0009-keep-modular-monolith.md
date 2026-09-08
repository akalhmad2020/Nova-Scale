# ADR 0009 — Keep NovaScale as a Modular Monolith

- Status: Accepted
- Date: 2026-09-07

## Context

NovaScale contains multiple business capabilities, including identity, shipments, customers, locations, billing, payments, documents, notifications, AI, and other logistics-related domains.

As the system grows, an architectural decision is required regarding whether these capabilities should remain inside one deployable application or be separated into independently deployed microservices.

Microservices can provide benefits such as independent deployment, isolated scaling, and stronger runtime boundaries.

However, they also introduce distributed-system complexity, including:

- Network communication between services.
- Distributed tracing.
- Service discovery.
- Independent deployment pipelines.
- Versioned service contracts.
- Distributed transactions and eventual consistency.
- More infrastructure to operate.
- More complex local development and testing.
- More difficult failure diagnosis.

NovaScale currently does not have scale, organizational structure, or operational requirements that justify this additional complexity.

At the same time, NovaScale needs strong internal boundaries so that business domains do not become tightly coupled inside a single codebase.

## Decision

NovaScale will remain a Modular Monolith.

The system will be deployed primarily as one backend application while business capabilities remain separated into explicit modules.

Each module should preserve clear architectural boundaries, typically including:

- Domain.
- Application.
- Infrastructure.
- API.

Modules should communicate through deliberate application-level contracts rather than accessing each other's infrastructure internals directly.

Business logic should remain independent from frameworks and infrastructure where practical.

The architecture should preserve dependency direction so that domain and application code do not depend directly on FastAPI, SQLAlchemy, external providers, or unrelated module infrastructure unless explicitly justified.

Shared code must remain limited to genuinely cross-cutting concepts and must not become a place for arbitrary business logic.

Database ownership and module boundaries should remain clear even though modules currently share a PostgreSQL instance.

NovaScale will not introduce microservices merely to demonstrate the architectural style.

A module may be considered for extraction into an independent service later when concrete requirements justify it, such as:

- Independent scaling requirements.
- Different availability requirements.
- Strong operational isolation.
- Independent deployment cadence.
- Separate team ownership.
- Regulatory or customer isolation requirements.
- Technology requirements that materially differ from the main application.
- Measured performance bottlenecks that cannot be addressed reasonably within the monolith.

Any future extraction should be based on observed requirements rather than predicted scale alone.

## Alternatives considered

### Traditional monolith without explicit module boundaries

NovaScale could remain a single application where business logic, database access, framework code, and domain concepts are freely shared across the codebase.

This would reduce short-term architectural overhead.

It was not selected because increasing business complexity would gradually create tight coupling, unclear ownership, and difficult-to-test business logic.

### Microservices from the beginning

Each NovaScale domain could run as an independently deployed service.

This could provide strong deployment and runtime boundaries.

It was not selected because the current product scale and development model do not justify the operational cost and distributed-system complexity.

Microservices would introduce additional failure modes and infrastructure before NovaScale has demonstrated a need for independent service scaling or deployment.

### Modular Monolith

NovaScale remains one primary backend deployment while maintaining explicit internal domain and application boundaries.

This model was selected because it provides much of the organizational clarity of service boundaries without prematurely introducing distributed infrastructure.

## Consequences

### Positive

- Development and local setup remain relatively simple.
- Cross-module transactions can use PostgreSQL transactions where appropriate.
- Deployment remains simpler than a distributed microservice architecture.
- Testing can cover complete workflows without requiring many independently running services.
- Business domains retain explicit ownership and boundaries.
- Modules can evolve independently at the code level.
- Future extraction into services remains possible when a real requirement appears.
- The architecture avoids distributed-system complexity that does not currently provide sufficient value.
- The project demonstrates architectural discipline without unnecessary infrastructure.

### Negative

- Modules share the same application process and can affect each other at runtime.
- Poor discipline could still allow boundaries to erode over time.
- A single backend deployment may eventually become a scaling constraint for specific workloads.
- Independent module deployment is not available without future extraction work.
- Shared database infrastructure requires care to preserve logical ownership between modules.
- Developers must actively review cross-module dependencies to prevent accidental coupling.