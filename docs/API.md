# API reference

Base URL (dev): `http://localhost:8000/api`. Interactive docs generated from the code: `/api/docs/` (Swagger UI), schema at `/api/schema/`.
All bodies are JSON. Authenticated calls send `Authorization: Bearer <access token>`.

## Conventions

* **Pagination** (list endpoints): `?page=2&page_size=25` (default 10, max 100) → `{"count": 42, "next": "...", "previous": null, "results": [...]}`. A page past the end returns **404**.
* **Errors** always look like this:
```json
{"error": {"status": 400, "code": "validation_error", "message": "Some fields are invalid.", "fields": {"title": ["Title must be at least 5 characters."]}}}
```
Non-validation errors omit `fields`. Codes seen: `validation_error`, `authentication_failed`, `not_authenticated`, `permission_denied`, `not_found`, `method_not_allowed`, `integrity_error`, `database_error`.
* **Status codes:** 200 OK, 201 Created, 204 No Content, 400 invalid input, 401 not authenticated (missing/expired/invalid token or bad login), 403 authenticated but not allowed, 404 not found *or hidden from you*, 405 method not allowed, 500 server fault.
* **Roles:** C = customer, A = agent, Ad = admin. "Staff" = A or Ad.

## Auth

| Method & URL | Auth | Purpose |
|---|---|---|
| `POST /auth/register/` | none | create a **customer** account |
| `POST /auth/login/` | none | get access token, set refresh cookie |
| `POST /auth/refresh/` | refresh cookie | new access token |
| `POST /auth/logout/` | none | delete refresh cookie (204) |
| `GET/PUT/PATCH /auth/me/` | any user | read/update own profile |
| `POST /auth/change-password/` | any user | change own password (204) |

**Register** request `{"username","email","password","first_name","last_name"}`; 201 returns the user (no password). 400 if the username/email is taken or the password fails Django's validators.

**Login**
```http
POST /api/auth/login/
{"username": "alice.customer", "password": "..."}
```
```json
200 {"access": "eyJhbGciOi...", "user": {"id": 1, "username": "alice.customer", "email": "alice.customer@example.test", "first_name": "Alice", "last_name": "Nguyen", "role": "customer", "is_active": true, "date_joined": "2026-10-22T09:00:00Z"}}
```
plus `Set-Cookie: refresh_token=...; HttpOnly; Path=/api/auth/; SameSite=Lax`. Errors: 400 missing field, 401 `"Invalid username or password."`.

**Refresh** needs no body; 401 when the cookie is missing, expired or the user is disabled.

**Profile**: writable `first_name`, `last_name`, `email` (unique); `username`, `role`, `id`, `date_joined` are read-only (sending `role` is silently ignored). `PUT` requires `email`; `PATCH` any subset.

**Change password**: `{"old_password","new_password"}` → 204; 400 `old_password` wrong or `new_password` too weak.

## Users

| Method & URL | Who | Purpose |
|---|---|---|
| `GET /users/?role=agent&search=da&is_active=true&page_size=100` | Staff | list users (assignment dropdown) |
| `GET /users/{id}/` | Ad | one user |
| `PATCH /users/{id}/` body `{"role": "agent", "is_active": true}` | Ad | change role / deactivate |

PUT is not allowed (405). Admins cannot change their own role or deactivate themselves (400). Customers get 403.

## Tickets

| Method & URL | Who | Purpose |
|---|---|---|
| `GET /tickets/` | any (customers see own only) | list, filter, search, order, paginate |
| `POST /tickets/` | any | create (customer or staff) |
| `GET /tickets/{id}/` | owner or staff | detail |
| `PATCH /tickets/{id}/` | owner (open tickets, title/description) or staff | partial update |
| `PUT /tickets/{id}/` | same | full update (`title`, `description` required) |
| `DELETE /tickets/{id}/` | Ad | delete ticket and its comments (204) |
| `POST /tickets/{id}/assign/` | Staff | `{"assigned_to": <user id or null>}` |
| `POST /tickets/{id}/status/` | Staff | `{"status": "in_progress"}` |
| `GET /tickets/{id}/comments/` | owner or staff | list comments (customers don't see internal notes) |
| `POST /tickets/{id}/comments/` | owner or staff | `{"body": "...", "is_internal": false}` |

**List query parameters:** `status`, `priority` (exact values), `assigned_to=<id>`, `created_by=<id>`, `unassigned=true`, `created_after=YYYY-MM-DD`, `created_before=`, `search=<text>` (title, description, requester username), `ordering=created_at|-created_at|updated_at|-id`, `page`, `page_size`.

**Create**
```http
POST /api/tickets/
{"title": "Cannot print invoices", "description": "Invoices print as blank pages.", "priority": "high"}
```
```json
201 {"id": 13, "title": "Cannot print invoices", "description": "Invoices print as blank pages.", "status": "open", "priority": "high",
     "created_by": {"id": 1, "username": "alice.customer", "first_name": "Alice", "last_name": "Nguyen", "role": "customer"},
     "assigned_to": null, "updated_by": {"id": 1, "username": "alice.customer", "first_name": "Alice", "last_name": "Nguyen", "role": "customer"},
     "created_at": "2026-10-22T09:30:00Z", "updated_at": "2026-10-22T09:30:00Z", "closed_at": null}
```
Rules: title ≥ 5 chars (max 200), description ≥ 10 chars, priority in `low|medium|high|urgent` (default `medium`). `created_by`, `status`, audit fields are set by the server; extra fields are ignored.
Errors: 400 validation, 401 no/invalid token.

**Update rules:** customers → 403 if they send `priority`; 400 if the ticket is no longer `open`; 404 on other people's tickets. Staff may change title/description/priority.

**Status workflow** (`POST /status/`): `open → in_progress|closed`; `in_progress → open|resolved|closed`; `resolved → in_progress|closed`; `closed → open`. Anything else, or the same status, is 400 with `fields.status`. Entering `closed` sets `closed_at`; leaving clears it.

**Assign:** target must be an active agent/admin (400 `fields.assigned_to` otherwise); closed tickets cannot be reassigned (400); assigning an `open` ticket moves it to `in_progress`; `null` unassigns. Both actions add a system comment in the same transaction.

**Comments:** closed tickets reject comments (400). Customers posting `is_internal: true` get 403. List response is a plain array (not paginated), oldest first.
```json
201 {"id": 31, "author": {"id": 4, "username": "dave.agent", "first_name": "Dave", "last_name": "Kimani", "role": "agent"}, "body": "Looking into it.", "is_internal": false, "is_system": false, "created_at": "2026-10-22T10:00:00Z"}
```

## Dashboard and health

`GET /dashboard/` (any user; staff see all tickets, customers their own)
```json
{"scope": "all", "total": 12, "by_status": {"open": 4, "in_progress": 3, "resolved": 2, "closed": 3},
 "by_priority": {"low": 4, "medium": 4, "high": 3, "urgent": 1}, "created_last_7_days": 8, "unassigned": 4, "assigned_to_me": 2}
```
`unassigned` and `assigned_to_me` are `null` for customers. `GET /health/` (public): `{"status":"ok","database":"ok"}` or 503 when PostgreSQL is unreachable.

## Trying it with curl
```bash
TOKEN=$(curl -s -X POST localhost:8000/api/auth/login/ -H 'Content-Type: application/json' \
        -d '{"username":"dave.agent","password":"<your SEED_PASSWORD>"}' | python -c 'import sys,json;print(json.load(sys.stdin)["access"])')
curl -s -H "Authorization: Bearer $TOKEN" 'localhost:8000/api/tickets/?status=open&page_size=3'
curl -i -X POST localhost:8000/api/tickets/ -H 'Content-Type: application/json' -d '{}'     # 401, no token
```
