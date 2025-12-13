# Organization Management Backend


## Table of Contents
- System Overview
- Architecture
- Tech Stack
- API Reference
- Local Development
- Deployment Notes
- Security Considerations
- Limitations & Future Improvements
- Troubleshooting
- Migration Script
- License

FastAPI backend implementing Organization CRUD with per-organization tenant databases in MongoDB. The system uses a master database for metadata and admin credentials, bcrypt for password hashing, and JWT for admin authentication. A migration script supports safe renaming of tenant databases.

## System Overview
- Master database stores `organizations` and `admins` collections.
- Each organization has an isolated tenant database named `org_<sanitized_name>` containing `tenant_metadata`.
- Admin login returns a JWT used for protected operations (e.g., org deletion). The token currently includes the `sub` (admin email) and `exp` claim.
- Organization creation enforces uniqueness on sanitised names and initialises tenant metadata, with a rollback on failure.

## Architecture
- FastAPI app exposes routes under `/admin` and `/org`.
- Motor (`AsyncIOMotorClient`) provides async MongoDB access.
- `app/` modules separate configuration, DB client, models, schemas, routers, and auth helpers.
- Tenant database naming is `org_<sanitize_org_name(name)>` where sanitization lowercases, replaces spaces with `_`, and removes non-alphanumeric `_`.

## Tech Stack
- `FastAPI` for the HTTP API
- `Motor` (async MongoDB driver)
- `passlib[bcrypt]` for password hashing
- `python-jose[jwt]` for JWT
- `Pydantic` models and settings
- `Docker` + `Docker Compose` for local dev
- `pytest` + `pytest-asyncio` for testing

## API Reference

- `GET /health`
  - Returns service status and environment.
  - Response example:
    ```json
    {"status": "ok", "env": "development"}
    ```

- `POST /admin/login`
  - Form data: `username` (email), `password`
  - Returns JWT bearer token.
  - Example:
    ```bash
    curl -X POST http://localhost:8000/admin/login \
      -d 'username=admin@example.com&password=secret123'
    ```
    Response:
    ```json
    {"access_token": "<jwt>", "token_type": "bearer"}
    ```

- `POST /org/create`
  - JSON body:
    ```json
    {
      "organization_name": "Acme Corp",
      "email": "owner@acme.com",
      "password": "strongpassword123"
    }
    ```
  - Behavior:
    - Sanitizes `organization_name` → `organization_name_lower`.
    - Ensures uniqueness in `master.organizations`.
    - Creates admin in `master.admins` with hashed password.
    - Initializes tenant DB `org_<sanitized>` with `tenant_metadata`.
  - Response example:
    ```json
    {
      "organization_name": "Acme Corp",
      "admin_email": "owner@acme.com",
      "created_at": "2024-01-01T12:00:00Z"
    }
    ```

- `GET /org/get?organization_name=<name>`
  - Retrieves org metadata by sanitized name.
  - Response example:
    ```json
    {
      "organization_name": "Acme Corp",
      "admin_email": "owner@acme.com",
      "created_at": "2024-01-01T12:00:00Z"
    }
    ```

- `DELETE /org/delete?organization_name=<name>`
  - Requires `Authorization: Bearer <token>`.
  - Only the org’s admin (matched by `sub` email in token) can delete.
  - Deletes org and admin from master DB and drops the tenant DB.
  - Response: `204 No Content`.

- `PUT /org/update`
  - JSON body:
    ```json
    {
      "organization_name": "Acme Corp",
      "email": "owner@acme.com",
      "password": "strongpassword123",
      "new_name": "Acme International"
    }
    ```
  - Behavior:
    - Requires admin token; only the org’s admin can rename.
    - Validates the new name does not already exist.
    - Updates the master metadata (`organization_name`, `organization_name_lower`).
    - Does not move tenant data. Use `scripts/migrate_org_name.py` to copy data to the new tenant database name, then update config.
  - Response example:
    ```json
    {
      "organization_name": "Acme International",
      "admin_email": "owner@acme.com",
      "created_at": "2024-01-01T12:00:00Z"
    }
    ```

## Local Development

### Environment Setup
1. Clone and enter the backend directory:
   ```bash
   git clone <repository_url>
   cd backend
   ```
2. Create environment file:
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

### Run with Docker
```bash
docker-compose up --build -d
```
This starts MongoDB and the FastAPI app on `http://localhost:8000`.

### Run Locally (without Docker)
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Ensure `MONGO_URI` in `.env` points to your local MongoDB.

## Deployment Notes
- Use MongoDB Atlas or a managed MongoDB. Configure `MONGO_URI` with proper credentials and TLS.
- Set a strong `JWT_SECRET`; rotate periodically. Consider storing in a secrets manager.
- Configure `MASTER_DB` to a distinct production database name.
- Restrict MongoDB users to least-privilege (read/write only to allowed DBs).

## Security Considerations
- Input sanitization: `sanitize_org_name` enforces lowercase, underscores, and alphanumerics.
- Passwords hashed via bcrypt using `passlib`.
- JWT has expiration (`exp`) and carries `sub` email claim and `org_id` identifier; signature HS256.
- Admin-only deletion: token is validated; email in token must match org admin.
- Database isolation: per-org tenant databases prevent cross-tenant reads by design.
- Rollback: on partial failures during creation, master records are cleaned up; tenant DB cleanup is documented for manual handling.

## Limitations & Future Improvements
- Tokens include `org_id`; they do not embed the tenant database name.
- Transactional creation across master and tenant DBs is limited; consider using multi-document transactions if using Mongo replica sets.
- Tenant DB cleanup on rollback is manual; add safe automation.
- Admin roles are minimal; introduce role-based access control.

## Troubleshooting
- "Organization name already exists": another org with same sanitized name exists.
- Mongo connection issues: verify `MONGO_URI` and that MongoDB is reachable.
- Unauthorized deletion: ensure you use the admin’s token for the target org.
- JWT validation errors: verify `JWT_SECRET` is consistent across environments.

## Migration Script
The script `scripts/migrate_org_name.py` performs a copy-based migration from `org_<old>` to `org_<new>`:
- Sanitizes names and computes source/target DBs.
- Copies documents in batches, supports resume by skipping existing `_id`s.
- Verifies counts and performs sample hash checks.
- Provides manual cutover guidance; does not auto-drop old DB.

## License
This repository is for an engineering assessment. Use as reference or with permission.
