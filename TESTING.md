# Testing

This project uses `pytest` with `pytest-asyncio` for async endpoint and helper tests.

## How to Run
- Local:
  ```bash
  pytest
  ```
- Docker:
  ```bash
  docker-compose exec app pytest
  ```

## Structure
- `tests/test_orgs.py`: integration-style tests for create/get/delete flows.
- `tests/test_sanitization.py`: unit tests for name sanitization helpers.
- `tests/test_auth.py`: unit tests for bcrypt and JWT helpers.
- `tests/test_migration.py`: dry-run style test for the migration script behavior.

## Test Database Configuration
- Tests use `settings.MONGO_URI` pointing to a local MongoDB (e.g., `mongodb://localhost:27017`).
- The test suite sets `settings.MASTER_DB` to a separate test DB to avoid interfering with development data.
- When running in CI, a MongoDB service runs and tests connect via `mongodb://localhost:27017`.

## Notes
- Tests avoid destructive operations wherever possible. The migration test validates copying behavior and presence of source/target DBs without dropping data.
- For endpoints, tests use `httpx.AsyncClient` against the FastAPI app object.