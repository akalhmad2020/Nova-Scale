# NovaScale Production Deployment

This document defines the production deployment contract for the NovaScale backend.

## 1. Deployment Architecture

NovaScale must run behind a trusted edge component such as a reverse proxy,
load balancer, ingress controller, or API gateway.

Expected traffic flow:

    Internet
        |
        v
    Edge / Reverse Proxy
        |
        |-- TLS termination
        |-- Global/IP rate limiting
        |-- Request size limits
        |-- Request timeouts
        |-- Forwarded headers
        |
        v
    NovaScale Backend :8000
        |
        v
    PostgreSQL :5432

The backend and PostgreSQL must not be directly exposed to the public internet.

## 2. TLS

TLS termination is the responsibility of the edge layer.

Production traffic exposed to clients must use HTTPS.

Plain HTTP traffic should either:

- be rejected, or
- redirect to HTTPS at the edge.

NovaScale enables HSTS in production.

The production configuration requires:

    HSTS_ENABLED=true

The application emits:

    Strict-Transport-Security: max-age=31536000; includeSubDomains

TLS certificates and private keys must be managed outside the NovaScale
application container.

## 3. Trusted Proxy Headers

NovaScale accepts proxy headers so that the application can receive the
original client and protocol information from the edge.

The backend runs with:

    --proxy-headers
    --forwarded-allow-ips <trusted-proxy-addresses>

The following headers may therefore be processed from trusted proxies:

- X-Forwarded-For
- X-Forwarded-Proto
- X-Forwarded-Port

FORWARDED_ALLOW_IPS must contain only trusted proxy addresses or networks.

Do not use:

    FORWARDED_ALLOW_IPS=*

in production.

The actual value depends on the deployment environment and network topology.

## 4. Network Exposure

The production Compose configuration does not publish the backend port to the
host.

The backend listens internally on:

    8000/tcp

PostgreSQL listens internally on:

    5432/tcp

PostgreSQL must never be exposed directly to the public internet.

Only the edge component should expose public HTTP/HTTPS ports.

## 5. Rate Limiting

Global and IP-based rate limiting is an edge responsibility.

It should be implemented by the production reverse proxy, API gateway,
load balancer, or ingress layer.

NovaScale intentionally does not implement a process-local in-memory global
rate limiter.

Application-level authentication protection remains inside NovaScale,
including login failure tracking and account lockout.

The edge should provide protection against:

- excessive request rates
- abusive clients
- repeated automated requests
- traffic bursts
- denial-of-service patterns within the capabilities of the deployment stack

Rate-limit thresholds are deployment-specific and should be configured at the
edge rather than hard-coded into the application.

## 6. Request Limits

The edge layer should enforce request limits before traffic reaches NovaScale.

At minimum, production deployments should define:

- maximum request body size
- request header limits
- connection timeout
- request/read timeout
- response/write timeout
- idle/keep-alive timeout

Exact values depend on the deployment environment and expected workload.

Large limits should not be configured without a business requirement.

## 7. Health Endpoints

NovaScale exposes:

    /health
    /health/live
    /health/ready

`/health/live` indicates that the application process is alive.

`/health/ready` verifies application readiness, including database
connectivity.

Container liveness checks use:

    /health/live

Load balancers or orchestrators may use:

    /health/ready

when deciding whether the backend should receive traffic.

## 8. Database Migrations

Database migrations must run before application services begin serving
production traffic.

NovaScale provides the one-shot production Compose service:

    migrate

which executes:

    alembic upgrade head

Application replicas must not independently execute migrations during startup.

Backend and worker services depend on successful completion of the migration
service.

## 9. Workers

The outbox worker is part of the default production deployment.

The notification worker is optional and belongs to the Compose profile:

    notifications

It must not be enabled in production until real production notification
providers are configured.

Logging-only notification providers are restricted to local and test
environments.

## 10. Secrets

Production secrets must be supplied by the deployment environment.

Secrets must not be:

- committed to Git
- baked into Docker images
- stored in Dockerfiles
- copied into the image build context
- stored in production documentation

At minimum, the production environment must securely provide:

- POSTGRES_PASSWORD
- DATABASE_URL credentials
- AUTH_JWT_SECRET

AUTH_JWT_SECRET must be a strong randomly generated secret.

Local development placeholder values must never be reused in production.

A production secret manager or equivalent platform-native secret mechanism
should be preferred when available.

## 11. Container Runtime

Production NovaScale containers run as the non-root user:

    novascale

Development-only files and packages are excluded from the production image.

The production image must not contain:

- .env
- .git
- tests
- pytest
- mypy
- ruff

## 12. Production Deployment Requirements

Before a production deployment is considered ready:

- TLS is configured at the edge.
- HTTP-to-HTTPS behavior is configured.
- The backend is not directly public.
- PostgreSQL is not directly public.
- FORWARDED_ALLOW_IPS contains only trusted proxy addresses/networks.
- Global/IP rate limiting is configured at the edge.
- Request size limits are configured at the edge.
- Network and request timeouts are configured at the edge.
- Production secrets are supplied securely.
- Database migrations complete successfully.
- `/health/live` succeeds.
- `/health/ready` succeeds.
- Backend containers run as a non-root user.
- The notification worker remains disabled unless production providers exist.