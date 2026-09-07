# ADR 0008 — Use a BFF with HttpOnly Cookies for Browser Authentication

- Status: Accepted
- Date: 2026-09-07

## Context

NovaScale has a Next.js frontend and a FastAPI backend.

The browser needs to authenticate users and call protected backend APIs.

One common approach is to return access and refresh tokens directly to browser JavaScript and store them in localStorage or another browser-accessible storage mechanism.

That approach makes token handling simple, but it exposes long-lived authentication credentials to JavaScript running in the browser.

If malicious JavaScript executes through an XSS vulnerability or a compromised dependency, browser-accessible tokens may be stolen and reused outside the victim's browser.

NovaScale therefore needs a browser authentication architecture that reduces direct exposure of authentication tokens to frontend JavaScript while still supporting access-token refresh and authenticated API requests.

The existing frontend already follows a Backend-for-Frontend (BFF) pattern using Next.js Route Handlers.

## Decision

NovaScale will use the Next.js application as a Backend-for-Frontend for browser-authenticated API access.

The browser will call NovaScale frontend API routes.

Those server-side route handlers will communicate with the FastAPI backend.

The authentication flow will conceptually follow:

Browser
    ↓
Next.js BFF
    ↓
FastAPI

Access and refresh tokens will be stored in cookies configured with HttpOnly so that normal browser JavaScript cannot directly read the token values.

The BFF will be responsible for:

- Reading authentication cookies on the server.
- Attaching bearer access tokens to FastAPI requests.
- Refreshing expired access tokens when appropriate.
- Updating authentication cookies after successful refresh.
- Clearing authentication state when refresh is no longer valid.
- Preventing token values from being unnecessarily exposed to browser JavaScript.

The browser application must not store access or refresh tokens in localStorage.

HttpOnly cookies reduce token exposure to JavaScript but do not by themselves solve every browser security concern.

Because cookies are automatically attached by the browser, cookie-authenticated mutation endpoints must also consider protections such as:

- CSRF defenses.
- Origin validation.
- SameSite cookie policy.
- Secure cookies in production.
- Appropriate request method and content-type controls where relevant.

Backend authorization remains responsible for determining what authenticated users are allowed to access.

The BFF is an authentication transport boundary and must not replace tenant membership, role, permission, or entitlement checks performed by the backend.

## Alternatives considered

### Store JWTs in localStorage

The frontend could receive access and refresh tokens directly and persist them in localStorage.

This simplifies direct browser-to-API calls but makes the token values accessible to JavaScript.

It was not selected because an XSS vulnerability or compromised frontend script could directly read and exfiltrate those credentials.

### Store tokens in browser JavaScript memory only

The frontend could keep access tokens only in application memory.

This reduces persistent exposure compared with localStorage, but refresh behavior, page reloads, and session restoration become more complex.

The browser still needs direct access to the token value while the application is running.

This was not selected as the primary authentication model.

### Browser calls FastAPI directly using authentication cookies

FastAPI could directly own the browser session cookies while the Next.js application calls it from the browser.

This is possible but introduces additional cross-origin, CORS, cookie, and deployment concerns when the frontend and API are served through different origins.

The BFF model was selected because it centralizes browser authentication handling at the frontend server boundary and keeps backend bearer-token handling away from browser JavaScript.

### Use the Next.js BFF with HttpOnly cookies

The browser communicates with Next.js Route Handlers while tokens remain server-readable but unavailable to normal browser JavaScript.

This model was selected because it provides a clear authentication boundary, supports token refresh centrally, and reduces direct exposure of credentials in the frontend application.

## Consequences

### Positive

- Access and refresh token values are not directly readable by normal browser JavaScript.
- Authentication logic is centralized in the BFF instead of duplicated across frontend components.
- Token refresh and authentication-state cleanup can be handled consistently.
- Browser code does not need to construct Authorization headers with stored JWT values.
- FastAPI remains responsible for application authorization and tenant security.
- The frontend can evolve independently from the backend authentication transport details.

### Negative

- The BFF introduces an additional request hop.
- Next.js Route Handlers must proxy protected API operations correctly.
- Cookie-authenticated requests require explicit CSRF and Origin security considerations.
- Refresh-token concurrency can create race conditions if multiple requests attempt refresh simultaneously.
- Authentication behavior exists across both Next.js and FastAPI and therefore requires end-to-end testing.
- Server-side cookie configuration must differ appropriately between local development and HTTPS production.