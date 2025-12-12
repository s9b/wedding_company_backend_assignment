# Security

This document lists implemented security measures and realistic guidance for production hardening. It reflects actual code behavior.

## Implemented Measures

- Sanitization Strategy
  - `sanitize_org_name` lowercases names, replaces spaces with `_`, and strips non-alphanumeric/underscore.
  - Prevents unsafe tenant DB names and enforces consistent uniqueness checks.

- Password Hashing
  - Uses `passlib` with `bcrypt` to hash admin passwords.
  - Verification via `pwd_context.verify(plain, hashed)`.

- JWT
  - HS256-signed tokens via `python-jose`.
  - Claims include `sub` (admin email) and `exp` (expiration).
  - Expiration configurable via `settings.JWT_EXP_SECONDS`.

- Authorization
  - Protected deletion uses `OAuth2PasswordBearer` to obtain the token.
  - The email from `sub` must match the organization’s admin email.

- Data Isolation
  - Per-organization tenant databases (`org_<sanitized_name>`) isolate reads/writes by design.

- Rollback Behavior
  - On creation failure, master DB inserts are removed.
  - Tenant DB cleanup on partial creation is documented for manual handling (to avoid unintended destructive operations).

## DB Permissions Advice

- Use least-privilege MongoDB users for the application (read/write only the master DB and tenant DBs as needed).
- In production, use distinct users per environment and enable TLS.
- For MongoDB Atlas, enforce IP allowlists and role-based permissions.

## Production Hardening Checklist

- Set a strong `JWT_SECRET`; rotate regularly.
- Use TLS for MongoDB connections.
- Configure resource quotas per tenant DB where applicable.
- Add rate limiting at the API gateway layer.
- Enable detailed audit logging for admin operations.
- Consider adding org claim to JWT for stricter scoping.
- Implement multi-document transactions for atomic org creation if replica sets are available.

## Sensitive Data Handling

- Do not log raw passwords or JWTs.
- Store secrets in environment variables or a secrets manager.
- Avoid embedding credentials in code or version control.

## Not Implemented (Transparent Disclosure)

- JWT does not include the org collection name claim.
- No RBAC beyond simple admin checks.
- No automatic tenant DB rollback on partial creation (manual cleanup recommended).