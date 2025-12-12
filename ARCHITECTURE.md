# Architecture

This document describes the structure, flows, and design decisions of the backend.

## Directory Structure

```
backend/
  app/
    main.py          # FastAPI app setup and router inclusion
    config.py        # Pydantic settings (env-driven)
    db.py            # Motor client and tenant DB helper
    auth.py          # Bcrypt hashing and JWT helpers
    models.py        # Pydantic models for DB documents
    schemas.py       # Pydantic schemas for API requests/responses
    routers/
      admin.py       # Admin login endpoint
      orgs.py        # Organization CRUD endpoints
  scripts/
    migrate_org_name.py # Safe copy-based tenant DB rename
  tests/             # pytest test suite
  Dockerfile         # FastAPI app container
  docker-compose.yml # App + Mongo for local dev
```

## Data Layout

- Master DB (`settings.MASTER_DB`):
  - `organizations`: `{ _id, organization_name, organization_name_lower, admin_email, created_at }`
  - `admins`: `{ _id, email, hashed_password, organization_id, created_at }`
- Tenant DBs: `org_<sanitized_name>`:
  - `tenant_metadata`: `{ _id, organization_id, organization_name, created_at }`

## Request Flow

```
Client --> FastAPI --> Router --> DB Client --> MongoDB
            ^           ^
            |           +-- Pydantic (models/schemas)
            +-- Auth (JWT decode for protected routes)
```

### Example: Create Organization

```
POST /org/create
  -> sanitize_org_name(name)
  -> check uniqueness in master.organizations
  -> hash admin password
  -> insert organization
  -> insert admin
  -> init tenant DB (tenant_metadata)
  -> respond with org data
  -> on failure: rollback master inserts (documented tenant cleanup)
```

### Example: Delete Organization

```
DELETE /org/delete
  -> decode JWT -> get admin email
  -> find org in master by sanitized name
  -> compare token email to org.admin_email
  -> delete org + admin from master
  -> drop tenant DB
  -> 204
```

## Authentication Flow

```
POST /admin/login (OAuth2PasswordRequestForm)
  -> fetch admin by email
  -> verify bcrypt password
  -> create JWT { sub: email, exp }
  -> return bearer token

Protected routes use OAuth2PasswordBearer to decode and validate token.
```

## Error Handling Standards

- Uses `HTTPException` with appropriate status codes:
  - 401 for invalid credentials
  - 403 for unauthorized org deletion
  - 404 for org not found
  - 409 for duplicate org name
  - 500 for internal failures (with rollback)

## Key Design Decisions

- Per-tenant database isolation to simplify data boundaries.
- Sanitization rules are simple, predictable, and enforced consistently.
- Master DB stores minimal metadata for easy administration.
- JWT carries only admin email for explicit authorization checks; future improvement is to include org claims for tighter scoping.

## Diagram (ASCII)

```
            +------------------+
            |   FastAPI App    |
            +---------+--------+
                      |
                      v
          +-----------+-----------+
          |  Routers: admin/orgs  |
          +-----+-----------+-----+
                |           |
                v           v
        +-------+--+   +----+------+
        |  auth.py |   |  db.py    |
        +-----+----+   +----+------+
              |            |
              v            v
        +-----+----+   +---+----------------+
        | JWT/Bcrypt|  |  AsyncIOMotorClient|
        +-----+----+   +---+-------+--------+
              |                |    |
              v                |    v
        +-----+----+           |  Tenant DBs
        |  master   | <--------+  org_<name>
        | orgs/admin|             tenant_metadata
        +-----------+             (per org)
```