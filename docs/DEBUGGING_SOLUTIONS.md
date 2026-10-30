# Debugging solutions (spoilers)

Try each exercise first. Format: root cause, diagnosis, fix, verification.

## 01. Wrong URL → 404
**Root cause:** the frontend calls `/api/ticket/` (singular); the router defines `tickets/`.
**Diagnosis:** 1) Network shows `GET .../api/ticket/` → 404. 2) Compare with `tickets/urls.py` (`router.register("tickets", ...)`) and Swagger. 3) The body is Django's HTML 404 page, not our JSON error: URL resolution fails *before* any DRF view runs, so `config/exceptions.py` never sees it. That is why `describeError` falls back to "Unexpected server response (HTTP 404)". Contrast with `GET /api/tickets/999999/`, which reaches the view and returns the JSON envelope.
**Fix:** restore `"/tickets/"`. **Verify:** list loads. Lesson: JSON 404 = routed but object missing/hidden; HTML 404 = no route.

## 02. Serializer rule too strict
**Root cause:** `validate_description` compares against 100 while the message (and the frontend) say 10.
**Diagnosis:** the 400 body has `fields.description`; `pytest -k create -x` shows a failing validation test; reading `validate_description` shows the mismatch between condition and text; `git diff`/`git log -p -- backend/tickets/serializers.py` shows the change.
**Fix:** `< 10`. **Verify:** tests pass; add boundary test with 10 and 9 characters. Lesson: keep client rules, server rules and messages in one place or at least tested together.

## 03. Missing migration
**Root cause:** the model has `due_date`; no migration adds the column, so PostgreSQL has no such column and every `SELECT` including it fails.
**Diagnosis:** server log: `column tickets_ticket.due_date does not exist`. `python manage.py makemigrations --check --dry-run` prints `Add field due_date to ticket`. `showmigrations` shows nothing pending, because the migration doesn't exist yet. `\d tickets_ticket` confirms the column is absent. Tests fail since pytest builds its database from migrations.
**Fix:** `python manage.py makemigrations tickets` (creates `0002_ticket_due_date.py`), read it, `sqlmigrate tickets 0002`, `migrate`. **Verify:** list works; `makemigrations --check` clean; commit the migration with the model change. Never fix this with `--fake` or by hand-adding the column.

## 04. Foreign key to a non-existent user
**Root cause:** `created_by_id` is set to `request.user.id + 1000`, an id with no row in `accounts_user`.
**Diagnosis:** the client sees only `integrity_error` (by design). The server console has the logged exception: `insert or update on table "tickets_ticket" violates foreign key constraint ... Key (created_by_id)=(1004) is not present in table "accounts_user"`. The traceback's first project frame is `tickets/views.py` `create`.
**Fix:** `serializer.save(created_by=request.user, ...)`. **Verify:** curl returns 201; `test_customer_creates_ticket_and_it_is_persisted` asserts the creator. Lesson: FK constraints protect data even when code is wrong; generic client errors are safe, detailed logs are where you debug.

## 05. Role check inverted to admin-only
**Root cause:** `IsSupportStaff` now requires `is_admin_role`, so agents fail the permission class.
**Diagnosis:** 403 (not 401) means authentication worked. The message text identifies the class. `SELECT username, role FROM accounts_user;` shows `dave.agent` is `agent`. The `assign` action's `permission_classes=[IsAuthenticated, IsSupportStaff]` leads to `accounts/permissions.py`.
**Fix:** use `user.is_support_staff`. **Verify:** `test_agent_assigns_ticket_and_it_starts_progress` and `test_agent_can_list_agents_for_the_assignment_dropdown` (these tests *would have failed*, so run the suite before committing).

## 06. Field name disagreement
**Root cause:** the frontend now reads `assignee`; the API sends `assigned_to`. `undefined` is falsy, so the UI shows "Unassigned".
**Diagnosis:** Network → Response shows `"assigned_to": {...}`; the code reads `t.assignee`. TypeScript passed because the *type* was edited to match the code, not the server. Types describe what you *believe* the API returns; nothing checks that at runtime.
**Fix:** `git restore` the three files (backend serializer is the contract). **Verify:** assignees show. If the contract must change, change serializer, `docs/API.md`, backend tests and types together.

## 07. Wrong API base URL
**Root cause:** `VITE_API_BASE_URL` points at port 8001 where nothing listens.
**Diagnosis:** the request goes to `localhost:8001` (Network), Console `ERR_CONNECTION_REFUSED`, no HTTP status (it never reached Django); `/api/health/` on 8000 is fine. A CORS failure would instead show a *response* in the server log but a blocked read in the browser; a refused connection shows nothing in the server log at all.
**Fix:** correct `.env` and **restart Vite** (values are read at startup). Other causes of the same symptom: backend not running, firewall/VPN, HTTP vs HTTPS mix, wrong host inside Docker.

## 08. Wrong database host
**Root cause:** `POSTGRES_HOST=db` is a Compose-internal hostname; on your machine it doesn't resolve.
**Diagnosis:** `migrate` prints `could not translate host name "db" to address`. `diffsettings` shows `HOST: 'db'`. `/api/health/` is 503 (the endpoint itself works; its DB check fails).
**Fix:** `POSTGRES_HOST=localhost` for local runs (Compose overrides it for containers). Password variant: error is `FATAL: password authentication failed for user "helpdesk"`: the host resolved and the server answered, the credentials were wrong (also remember the stale-volume-password gotcha in `DATABASE.md`).

## 09. Pagination parameter silently ignored
**Root cause:** DRF only reads the query parameter named by `page_size_query_param`; with `"limit"`, `?page_size=100` is an unknown parameter and is ignored.
**Diagnosis:** compare `len(results)` with the requested size; read `config/pagination.py`; grep tests for `page_size`: none.
**Fix:** restore `"page_size"` and add the regression test:
```python
def test_page_size_parameter_is_honoured(login, agent, customer):
    for i in range(12):
        make_ticket(customer, title=f"Ticket number {i:02d}")
    assert len(login(agent).get("/api/tickets/", {"page_size": 12}).data["results"]) == 12
```
**Verify:** fails with the bug, passes after the fix.

## 10. Render condition hides data
**Root cause:** the table is rendered only when `data.count > 10`, so 1-10 tickets render neither table nor empty message (the empty branch requires `results.length === 0`).
**Diagnosis:** Network shows 200 and 3 results; `console.log(data)` confirms state is populated; reading the JSX conditions shows no branch matches. Backend is innocent: the frontend is the failing layer.
**Fix:** `data.results.length > 0`. **Verify:** 0, 3 and 25 tickets each show the right UI. Lesson: enumerate every state (loading, error, empty, populated); a missing branch renders nothing silently.

## 11. Test forgot to authenticate
**Root cause:** the test never logs in, so the API correctly returns 401. Test bug, not app bug.
**Diagnosis:** `assert 401 == 200`: the actual value tells you auth. Other tests call `login(agent)` (fixture in `conftest.py`) to attach credentials. The manual browser request works because the browser has a token.
**Fix:**
```python
def test_agent_lists_tickets(login, agent, ticket):
    response = login(agent).get("/api/tickets/")
    ...
def test_anonymous_cannot_list(api):
    assert api.get("/api/tickets/").status_code == 401
```
**Verify:** both pass. Lesson: reproduce manually first; if the app obeys its documented rules, fix the test.

## 12. N+1 queries
**Root cause:** without `select_related`, serializing each ticket's nested `created_by`, `assigned_to`, `updated_by` triggers one extra query per relation per row (≈ 3×N + 2).
**Diagnosis:** SQL log shows `SELECT ... FROM "accounts_user" WHERE "accounts_user"."id" = 5 LIMIT 21` repeated; `test_list_uses_constant_number_of_queries` fails with "Expected to perform at most 4 queries, 27 done" (the failure lists the queries).
**Fix:** restore `select_related("created_by", "assigned_to", "updated_by")`. **Verify:** test green; in psql `EXPLAIN ANALYZE` of the joined query. Lesson: fast on 10 dev rows, slow on 10,000 production rows; guard with a query-count test.
