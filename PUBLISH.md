# PUBLISH: Evaluator Guide

This document explains how to run, review, and evaluate the backend project. It focuses on reproducibility and clarity for experienced backend engineers.

## How to Run

- Docker (recommended):
  ```bash
  cd backend
  cp .env.example .env
  # Edit .env with your values
  docker-compose up --build -d
  # App: http://localhost:8000, Mongo: localhost:27017
  ```

- Local (without Docker):
  ```bash
  cd backend
  cp .env.example .env
  pip install -r requirements.txt
  uvicorn app.main:app --reload --port 8000
  ```
  Ensure `MONGO_URI` in `.env` points to a running MongoDB instance.

## How to Understand the System

- Start at `app/main.py` to see router registrations and startup/shutdown hooks.
- Review `app/routers/admin.py` and `app/routers/orgs.py` for endpoints and authorization.
- Inspect `app/auth.py` for bcrypt hashing and JWT helpers.
- Check `app/db.py` for Mongo client handling and tenant DB selection.
- See `app/models.py` and `app/schemas.py` for Pydantic data models.
- Review `scripts/migrate_org_name.py` for safe tenant DB renames.

## Authentication Overview

- Admin login via `POST /admin/login` using form data: `username=<email>`, `password=<password>`.
- On success, returns `{ access_token, token_type }`.
- JWT includes `sub` (admin email) and `exp`. Signature is HS256 using `JWT_SECRET`.
- Protected operations (e.g., `DELETE /org/delete`) require `Authorization: Bearer <token>`.
  - The email in `sub` must match the organization’s admin to authorize deletion.

## Known Constraints

- JWT does not currently include the org collection name.
- Rollback during org creation cleans master DB records, but tenant DB cleanup may require manual steps.
- Multi-document transactions across master and tenant DBs are not implemented.

## External Steps Not Automated

- Creating MongoDB users and setting permissions in production.
- Managing `.env` secrets and rotation policies.
- Configuring MongoDB Atlas network access and TLS.
- CI/CD environment configuration (secrets, self-hosted runners).

## Review Tips

- Verify sanitization rules (`sanitize_org_name`) for DB naming.
- Confirm admin-only delete logic checks bearer token email.
- Inspect tests under `backend/tests/` for endpoint, auth, and migration coverage.