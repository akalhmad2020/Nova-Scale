# ADR 0010 — Use PostgreSQL as the Core Database and pgvector for RAG

- Status: Accepted
- Date: 2026-09-07

## Context

NovaScale stores strongly relational business data across domains such as identity, tenants, shipments, customers, billing, payments, documents, and other logistics workflows.

These domains require capabilities such as:

- Transactions.
- Referential integrity.
- Constraints.
- Relational queries.
- Reliable persistence.
- Schema migrations.
- Tenant-aware data access.

NovaScale also contains a RAG system that requires vector embeddings and similarity search over tenant-owned document content.

A separate specialized vector database could be introduced for this workload.

However, doing so would add another persistent data system that must be deployed, secured, monitored, backed up, restored, and kept consistent with NovaScale's relational data.

PostgreSQL already serves as NovaScale's primary transactional database, and pgvector adds vector storage and similarity-search capabilities directly to PostgreSQL.

The current RAG workload does not demonstrate a requirement that justifies operating a separate vector database.

## Decision

PostgreSQL will remain NovaScale's primary database for transactional and relational application data.

NovaScale will use the pgvector PostgreSQL extension for the current RAG vector-search requirements.

Vector chunks will remain tenant-aware and associated with the NovaScale resources from which they were derived.

The current embedding representation uses 768-dimensional vectors.

Vector retrieval must preserve Tenant isolation just like other tenant-owned application data.

The RAG architecture must continue to depend on a NovaScale-owned VectorStore application port rather than coupling application logic directly to pgvector.

Conceptually:

RAG Application Service
        ↓
VectorStore Port
        ↓
PostgreSQL / pgvector Adapter

This allows the current infrastructure choice to change later without redesigning the RAG application layer.

NovaScale will not introduce a separate vector database solely because specialized vector databases exist.

A dedicated vector-search system may be considered later if measured requirements justify it, including:

- Vector corpus size that PostgreSQL cannot serve efficiently enough.
- Search latency requirements that cannot reasonably be met with pgvector.
- High vector-query throughput requiring independent scaling.
- Advanced retrieval capabilities unavailable or unsuitable in the PostgreSQL solution.
- Operational requirements that justify independent vector infrastructure.

The decision to move away from pgvector must therefore be based on observed requirements and measurements.

## Alternatives considered

### Dedicated vector database from the beginning

NovaScale could use a specialized system such as a managed or self-hosted vector database.

This could provide specialized vector indexing, scaling, and retrieval capabilities.

It was not selected because NovaScale's current RAG workload does not justify another stateful infrastructure dependency.

A separate system would also introduce synchronization, backup, monitoring, tenant-isolation, and operational concerns.

### Store embeddings outside the relational data model

Embeddings could be stored in an unrelated external system without preserving strong relationships with NovaScale documents and tenants.

This was not selected because retrieval must preserve the ownership and tenant boundaries of the source data.

### PostgreSQL with pgvector

NovaScale stores vectors alongside its existing PostgreSQL infrastructure while accessing them through an application-owned VectorStore abstraction.

This model was selected because it satisfies the current retrieval requirements with lower operational complexity while preserving a migration path to another vector backend if necessary.

## Consequences

### Positive

- NovaScale operates fewer stateful infrastructure systems.
- Vector data can remain closely associated with Tenant and document identifiers.
- Existing PostgreSQL operational practices can also cover the vector data.
- Local development and deployment remain simpler.
- RAG tenant isolation can align with existing database boundaries.
- Application code remains independent from pgvector through the VectorStore port.
- A dedicated vector database can still be introduced later if measurements justify it.
- The architecture avoids infrastructure that does not currently solve a demonstrated problem.

### Negative

- Vector workloads share PostgreSQL resources with transactional workloads.
- Large-scale vector search may eventually require different scaling characteristics.
- pgvector may not provide every specialized retrieval capability available in dedicated vector databases.
- Vector indexes and queries require performance monitoring as the corpus grows.
- A future migration to dedicated vector infrastructure would require data migration and operational work.