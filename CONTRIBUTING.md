# Contributing

Thanks for your interest in contributing! This project aims to mirror professional backend standards.

## Branch Naming
- Use descriptive names: `feature/<short-desc>`, `fix/<short-desc>`, `docs/<short-desc>`.
- Examples: `feature/add-org-rename-endpoint`, `fix/jwt-exp-config`, `docs/update-readme`.

## Commit Style
- Use concise, imperative messages:
  - `Add sanitization tests for org names`
  - `Fix admin login form handling`
- Group related changes; avoid mixing code, tests, and docs unless tightly coupled.

## Code Style & Linting
- Python 3.11+.
- Run `ruff` (or `flake8`) locally before pushing.
- Keep functions small and focused; prefer explicit naming.

## Tests
- Use `pytest` + `pytest-asyncio`.
- Structure tests under `backend/tests/` by topic (auth, orgs, migration, etc.).
- Run tests locally:
  ```bash
  pytest
  ```
- Or via Docker:
  ```bash
  docker-compose exec app pytest
  ```

## Opening Issues
- Include environment details (`ENV`, Python version, MongoDB version).
- Provide reproduction steps and expected vs. actual behavior.
- Tag issues with scope: `auth`, `orgs`, `migration`, `docs`, `infra`.

## Pull Requests
- Link related issues and provide context.
- Include tests for new behavior and update docs when behavior changes.
- Keep PRs small; prefer incremental improvements.