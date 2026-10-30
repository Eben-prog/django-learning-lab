# Debugging exercises (problems only)

Twelve controlled bugs. **The shipped application contains none of them**; you inject each one yourself, so you can also
see the exact change. Answers are in `DEBUGGING_SOLUTIONS.md`: attempt each exercise first, using the method in `DEBUGGING.md`.

## How to run an exercise

```bash
git switch -c exercise/01            # work on a throw-away branch
# 1. make the BUG INJECTION edit below
# 2. restart the backend (or Vite for frontend/.env changes) and reproduce the symptom
# 3. diagnose using evidence (Network tab, server console, psql, pytest) BEFORE reading hints
# 4. when finished:   git restore . && git switch -   (discard the bug)
```
Run `cd backend && python -m pytest` on the clean code first so you know the baseline is green.
Seed data first (`python manage.py seed_demo_data`) and log in as `dave.agent` unless told otherwise.

---

## 01. The list page shows a vague error  (routing)
* **Symptom:** After logging in, the Tickets page shows "Unexpected server response (HTTP 404)". The backend console shows `Not Found: /api/ticket/`.
* **Files:** `frontend/src/api/tickets.ts`, `backend/tickets/urls.py`, `backend/config/urls.py`
* **BUG INJECTION:** in `frontend/src/api/tickets.ts`, inside `listTickets`, change `"/tickets/"` to `"/ticket/"`.
* **Hints:** 1) Open Network → click the failed request → compare *Request URL* with the routes in `urls.py`. 2) Why did the message not say "Not found" in our JSON error format? 3) Which layer produces a 404 for an unknown URL?
* **Reproduce:** reload `/tickets`. **Verify:** list loads; Swagger (`/api/docs/`) lists the real path.

## 02. A perfectly good ticket is rejected  (serializer validation)
* **Symptom:** Creating a ticket with a 40-character description returns an error saying "at least 10 characters". Backend tests also fail.
* **Files:** `backend/tickets/serializers.py`, `backend/tests/test_tickets.py`
* **BUG INJECTION:** in `TicketCreateSerializer.validate_description`, change `< 10` to `< 100`.
* **Hints:** 1) Read the 400 body's `error.fields`. 2) Run `pytest tests/test_tickets.py -k create`. 3) Compare the error *message* with the *condition*.
* **Verify:** the tests pass; add a boundary test (exactly 10 characters is accepted, 9 is rejected).

## 03. 500 errors on every ticket page after a "small" model change  (migrations)
* **Symptom:** The ticket list returns 500 `database_error`; the server log mentions a missing column. `pytest` fails almost everywhere.
* **Files:** `backend/tickets/models.py`, `backend/tickets/migrations/`
* **BUG INJECTION:** add `due_date = models.DateTimeField(null=True, blank=True)` to `Ticket` (after `closed_at`). Do **not** run `makemigrations`.
* **Hints:** 1) Read the first lines of the log message, not the traceback's framework frames. 2) `python manage.py makemigrations --check --dry-run` and `showmigrations`. 3) In psql, `\d tickets_ticket`: is the column there?
* **Verify:** list works, `makemigrations --check` reports no changes, tests green.

## 04. Creating a ticket returns 500  (foreign key)
* **Symptom:** `POST /api/tickets/` returns 500 `integrity_error` ("A database error occurred"). Existing tickets load fine.
* **Files:** `backend/tickets/views.py`, `backend/config/exceptions.py`
* **BUG INJECTION:** in `TicketViewSet.create`, replace `created_by=request.user` with `created_by_id=request.user.id + 1000`.
* **Hints:** 1) The client message is deliberately vague: where does the *real* reason go? 2) Look for `violates foreign key constraint`. 3) Which table does it say the id must exist in?
* **Verify:** curl a create and confirm 201; add a test asserting `created_by` equals the caller.

## 05. Agents are told they are forbidden  (authorization)
* **Symptom:** As `dave.agent`, assigning a ticket shows "Only support agents and administrators can do this." and the Assign dropdown is empty. As admin everything works.
* **Files:** `backend/accounts/permissions.py`, `backend/tickets/views.py`, `backend/tests/test_assignment_status.py`
* **BUG INJECTION:** in `IsSupportStaff.has_permission`, replace `user.is_support_staff` with `user.is_admin_role`.
* **Hints:** 1) 403 vs 401: what does each tell you? 2) Which `permission_classes` does the `assign` action use? 3) Check the user's `role` in psql.
* **Verify:** agent can assign; run the whole suite; name the test that should have caught this earlier.

## 06. Every ticket says "Unassigned"  (contract mismatch)
* **Symptom:** The list and detail pages show assignee "Unassigned" for tickets that are clearly assigned (psql confirms). No error anywhere, and `npm run typecheck` passes.
* **Files:** `frontend/src/types/index.ts`, `frontend/src/pages/TicketListPage.tsx`, `frontend/src/pages/TicketDetailPage.tsx`, `backend/tickets/serializers.py`
* **BUG INJECTION:** `cd frontend/src && sed -i 's/\bassigned_to\b/assignee/g' types/index.ts pages/TicketListPage.tsx pages/TicketDetailPage.tsx`
* **Hints:** 1) Network → Response: what is the field called in the JSON? 2) Why did TypeScript not complain? 3) Which side is the source of truth for the contract?
* **Verify:** assignees display; explain why a type definition cannot protect you from a wrong server response.

## 07. The whole app says it cannot reach the server  (wrong API URL)
* **Symptom:** Login fails with "Cannot reach the server. Check that the backend is running…". The Console shows `ERR_CONNECTION_REFUSED`. `curl localhost:8000/api/health/` works.
* **Files:** `frontend/.env`, `frontend/src/api/client.ts`
* **BUG INJECTION:** create/edit `frontend/.env` with `VITE_API_BASE_URL=http://localhost:8001/api`, then restart `npm run dev`.
* **Hints:** 1) Network → request URL. 2) Is it a CORS error or a connection error? How can you tell? 3) When are `VITE_*` values read?
* **Verify:** login works; write down three different causes that produce the *same* "no response" symptom.

## 08. Django cannot connect to the database  (environment)
* **Symptom:** `python manage.py runserver` starts but every API call is 500; `/api/health/` returns 503; `python manage.py migrate` fails.
* **Files:** `.env`, `backend/config/settings.py`, `docker-compose.yml`
* **BUG INJECTION:** with Django running on your machine (not in Docker), set `POSTGRES_HOST=db` in `.env`. (Variant: set a wrong `POSTGRES_PASSWORD`.)
* **Hints:** 1) Read the exact error text of `migrate`. 2) What does the hostname `db` mean outside Docker Compose? 3) `python manage.py diffsettings | grep -A8 DATABASES`.
* **Verify:** `curl localhost:8000/api/health/` returns ok. Try the password variant: how does its error differ?

## 09. `page_size` is ignored  (pagination)
* **Symptom:** `GET /api/users/?page_size=100` returns only 10 results, so with many agents the Assign dropdown would be incomplete.
* **Files:** `backend/config/pagination.py`, `backend/tests/`
* **BUG INJECTION:** in `StandardPagination`, change `page_size_query_param = "page_size"` to `"limit"`.
* **Hints:** 1) Compare the response `count`/`results` length with the query. 2) Does any existing test cover `page_size`? 3) Silently ignored parameters are a bug class: why do they not produce errors?
* **Verify:** write a regression test (create 12 tickets, request `page_size=12`, expect 12 results), watch it fail, then fix.

## 10. The API returns tickets but the page shows nothing  (frontend rendering)
* **Symptom:** Tickets page says nothing at all (no table, no "No tickets match" message) for an account that has 3 tickets. Network shows 200 with 3 results.
* **Files:** `frontend/src/pages/TicketListPage.tsx`
* **BUG INJECTION:** change the condition `data.results.length > 0` (the one wrapping the table) to `data.count > 10`.
* **Hints:** 1) Prove the data arrived (Network → Response). 2) Add `console.log(data)`. 3) Walk the three states: loading, empty, populated: which branches render?
* **Verify:** table shows for 1, 3 and 25 tickets.

## 11. A new test fails but the app is fine  (bad test assumption)
* **Symptom:** You write a test for "agents can list tickets" and it fails with `assert 401 == 200`. Manually in the browser it works.
* **Files:** `backend/tests/conftest.py`, new file `backend/tests/test_exercise_11.py`
* **BUG INJECTION (the broken test):**
```python
import pytest

@pytest.mark.django_db
def test_agent_lists_tickets(api, agent, ticket):
    response = api.get("/api/tickets/")
    assert response.status_code == 200
    assert response.data["count"] == 1
```
* **Hints:** 1) Read the failing assertion's *actual* value. 2) What identifies the user in this test? 3) Look at how other tests obtain an authenticated client.
* **Verify:** after fixing, the test passes **and** a second test proves anonymous callers get 401 (so you know the test can fail).

## 12. The ticket list gets slower as data grows  (N+1 queries)
* **Symptom:** Listing 10 tickets issues ~30 SQL queries. `test_list_uses_constant_number_of_queries` fails.
* **Files:** `backend/tickets/views.py`, `backend/tickets/serializers.py`
* **BUG INJECTION:** in `TicketViewSet.get_queryset`, change `Ticket.objects.select_related("created_by", "assigned_to", "updated_by")` to `Ticket.objects.all()`.
* **Hints:** 1) Start the server with `DJANGO_DEBUG=True DJANGO_SQL_LOG=True`, load the list page and read the console. 2) Look for the same `SELECT ... FROM accounts_user WHERE id = N` repeating. 3) Why do nested serializers trigger this?
* **Verify:** query count is constant again (test passes); `EXPLAIN` the remaining queries.
