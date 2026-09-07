# ADR 0013 — AI Models and Agents Are Never Authorization Authorities

- Status: Accepted
- Date: 2026-09-07

## Context

NovaScale includes AI capabilities such as RAG and an Agent that can reason about a user's request and select application tools.

Agent tools may interact with sensitive tenant-owned business capabilities, including shipments, documents, customers, billing information, and future operational actions.

Large language models process untrusted and semi-trusted input, including:

- User prompts.
- Retrieved document content.
- Tool results.
- Potentially malicious prompt-injection instructions.
- External content introduced by future integrations.

An LLM may also produce incorrect, manipulated, or unexpected output.

The model therefore cannot be trusted to determine security-sensitive facts such as:

- Which Tenant the User belongs to.
- Which Tenant should be accessed.
- Which Membership is valid.
- Which Permissions the User has.
- Which SaaS Entitlements are active.
- Whether a protected business operation is authorized.

Allowing model-generated arguments to establish authorization context would allow prompt injection or model errors to cross security boundaries.

## Decision

AI models and Agents in NovaScale will never act as authorization authorities.

Authentication, Tenant context, Membership, Permissions, Entitlements, and business authorization must be established by trusted application code independently from model output.

The Agent will receive a trusted server-created context containing the authorization context required for its execution.

Conceptually:

Authenticated Request
        ↓
Membership Validation
        ↓
Permission / Entitlement Checks
        ↓
Trusted Agent Context
        ↓
Agent / LLM
        ↓
Tool Selection
        ↓
Application Use Case
        ↓
Authorized Tenant-Scoped Operation

The LLM may decide which available tool is useful for completing a request.

It may provide non-security-sensitive arguments required by that tool.

It must not be allowed to choose or override trusted security context such as Tenant identity or authenticated User identity.

If model output contains a different Tenant identifier, User identifier, Role, Permission, or other authorization claim, that output must not override the trusted application context.

Agent tools must call NovaScale application use cases or application services rather than repositories or the database directly.

Existing authorization and tenant-isolation rules therefore remain effective when an operation is initiated through AI.

The Agent must not receive tools that allow it to bypass application authorization boundaries.

Tool capabilities should follow least privilege.

Read-only tools and write-capable tools should remain distinguishable, and future write-capable Agent actions may require stronger controls such as:

- Explicit user confirmation.
- Additional authorization checks.
- Idempotency protection.
- Audit logging.
- Restricted tool availability.
- Validation of proposed actions before execution.

Retrieved RAG content must be treated as data, not trusted instructions.

Instructions contained inside documents, emails, external pages, or retrieved chunks must not be allowed to redefine NovaScale authorization policy or trusted Agent context.

## Alternatives considered

### Allow the LLM to determine Tenant context

The model could extract or infer a Tenant identifier from the user's prompt and use it when calling tools.

This was not selected because model output is not a trusted security source.

A malicious prompt or model error could cause cross-Tenant access attempts.

### Give the Agent direct repository access

Agent tools could query repositories or PostgreSQL directly.

This may reduce implementation layers but would create an alternative execution path around NovaScale application use cases and authorization rules.

It was not selected because AI-initiated operations must obey the same application boundaries as normal API operations.

### Trust retrieved RAG content as Agent instructions

Documents retrieved from the vector store could provide instructions that influence tool authorization or security context.

This was not selected because retrieved content may contain malicious or unintended prompt-injection instructions.

Retrieved content is evidence or data for answering the request, not an authorization authority.

### Use trusted application context and application-level tools

The application establishes authorization before Agent execution and exposes only controlled tools that invoke existing application capabilities.

This model was selected because it preserves NovaScale's security boundaries independently from model behavior.

## Consequences

### Positive

- Prompt injection cannot legitimately grant additional Tenant access or Permissions.
- Model hallucinations cannot redefine authenticated identity.
- AI operations reuse existing application authorization boundaries.
- Agent tools remain testable independently from the LLM.
- Tenant isolation remains consistent between normal APIs and AI workflows.
- Future AI providers can be replaced without changing the authorization model.
- Write-capable Agent functionality can be introduced progressively with stronger controls.
- AI security failures are less likely to become direct authorization failures.

### Negative

- Agent tools require explicit application integration rather than unrestricted database access.
- Trusted context must be propagated carefully through Agent execution.
- Tool schemas must distinguish model-controlled arguments from trusted server-controlled context.
- Prompt injection remains a concern for model behavior even when authorization boundaries are protected.
- Future write-capable Agent tools require additional security and UX design.
- AI workflows require dedicated authorization and cross-Tenant security tests.