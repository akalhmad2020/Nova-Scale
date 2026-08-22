# Contributing

## Branches

Use short-lived branches from `main`:

- `feat/<name>`
- `fix/<name>`
- `refactor/<name>`
- `test/<name>`
- `docs/<name>`
- `chore/<name>`

## Commits

Use Conventional Commits, for example:

- `feat(identity): add tenant membership model`
- `fix(shipments): prevent duplicate submission`
- `test(identity): verify cross-tenant isolation`

## Pull request gate

A pull request is mergeable only when formatting, linting, type checking, tests, migrations, and the production Docker build pass.
