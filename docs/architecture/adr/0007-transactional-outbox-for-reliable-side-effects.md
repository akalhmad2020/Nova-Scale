# ADR 0007 — Use a Transactional Outbox for Reliable Asynchronous Side Effects

- Status: Accepted
- Date: 2026-09-07

## Context

NovaScale performs business operations that may need to trigger asynchronous work after a successful database transaction.

Examples include:

- Sending emails.
- Delivering webhooks.
- Indexing documents for RAG.
- Processing notifications.
- Triggering external integrations.
- Performing other background work caused by business events.

Writing business state to PostgreSQL and independently sending a message or calling an external service creates a dual-write problem.

For example, a shipment transaction could commit successfully while the subsequent webhook, email, or event publication fails.

The opposite ordering is also unsafe: an external action could succeed before the database transaction later rolls back.

NovaScale therefore needs a reliable way to record that asynchronous work must occur without requiring the database transaction and an external system to participate in one distributed transaction.

NovaScale already has a transactional outbox foundation and uses it for post-transaction processing.

## Decision

NovaScale will continue to use the transactional outbox pattern for reliable asynchronous side effects that originate from committed business transactions.

When a business operation produces an event that requires asynchronous processing, the business state change and the corresponding outbox event will be persisted in the same PostgreSQL transaction.

Conceptually:

BEGIN

Persist business changes
Persist outbox event

COMMIT

A background worker will process committed outbox events separately.

The processing lifecycle will support states such as:

- PENDING
- PROCESSING
- PROCESSED
- FAILED

Processing may include retries, leases, attempt limits, failure visibility, and recovery after worker restarts.

Consumers must be designed to tolerate duplicate processing where necessary.

NovaScale will not claim exactly-once delivery from the transactional outbox.

The expected reliability model is based on durable event recording, retryable processing, and idempotent consumers where duplicate external effects would otherwise be unsafe.

The outbox will be reused for suitable asynchronous workflows rather than creating unrelated reliability mechanisms for email, webhooks, AI document indexing, and similar post-transaction work.

Introducing a dedicated message broker such as Kafka or RabbitMQ is not required at the current scale.

A broker may be introduced later if measured throughput, independent service scaling, delivery topology, or other operational requirements justify the additional distributed-system complexity.

## Alternatives considered

### Perform external side effects directly inside the business transaction

NovaScale could call email, webhook, AI, or other external providers while processing the request.

This was not selected because external systems can be slow or unavailable and cannot participate reliably in the PostgreSQL transaction.

Holding database transactions open while waiting for external services would also increase latency and resource contention.

### Commit the database transaction and then perform the side effect

NovaScale could commit business state first and then call the external service.

This was not selected because a process crash or provider failure between the commit and the external action could permanently lose required work.

### Publish an external message before committing the database transaction

NovaScale could publish the event first and then commit the business transaction.

This was not selected because consumers could observe and act on an event representing business state that later fails to commit.

### Introduce a dedicated message broker immediately

NovaScale could use Kafka, RabbitMQ, or another broker for asynchronous processing.

This was not selected at the current scale because a broker would add infrastructure and operational complexity without removing the need to solve consistency between the database transaction and event publication.

A transactional outbox provides the required reliability while using PostgreSQL, which NovaScale already operates.

## Consequences

### Positive

- Business changes and the intent to perform asynchronous work are recorded atomically.
- Required post-transaction work is not silently lost when an external provider is temporarily unavailable.
- Background processing can retry failures independently from the original user request.
- API requests do not need to wait for slow external side effects when synchronous completion is unnecessary.
- Email, webhooks, AI indexing, and future integrations can reuse a common reliability mechanism.
- Failed events can be inspected and operationally recovered.
- NovaScale avoids introducing a message broker before there is a demonstrated need for one.
- The architecture provides a path toward broker-based event publication later if scale or topology requires it.

### Negative

- Background workers must be operated and monitored.
- Outbox records require lifecycle management and retention policies.
- Consumers may receive the same event more than once and must handle duplicates safely where required.
- Retries require careful backoff and failure policies.
- External side effects cannot generally participate in the same atomic transaction as PostgreSQL.
- Processing is eventually consistent rather than immediately completed with the original transaction.