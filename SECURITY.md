# Security

## Baseline rules

- Never commit secrets, access tokens, passwords, or production `.env` files.
- Tenant identity must never be trusted directly from user-controlled request input.
- Database changes must go through deterministic application services and authorization boundaries.
- AI components must never receive unrestricted database write access.
- Report suspected vulnerabilities privately to the project maintainers rather than publishing exploit details.
