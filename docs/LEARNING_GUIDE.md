# Learning guide: ten stages

Work in order. Each stage ends with a self-assessment; move on only when you can answer without looking.
Rule of thumb: **read the code with the app running**: change something, watch what breaks.

## Stage 1: Run the app and understand its structure
* **Inspect:** `README.md`, `backend/config/settings.py`, `backend/config/urls.py`, folder tree, `frontend/src/App.tsx`.
* **Understand:** three processes (React, Django, PostgreSQL); what each app folder owns; where config comes from (`.env`).
* **Commands:** `docker compose up --build`, `python manage.py check`, `python manage.py migrate`, `python manage.py seed_demo_data`, open `/api/docs/`, `/admin/`, and the app. Log in as a customer, then an agent.
* **Modify/test:** run `python -m pytest`; fix any first-run failures using `DEBUGGING.md` (they count as practice).
* **Checklist:** ☐ I can start all three pieces ☐ I can say what each top-level folder is for ☐ I know where the DB password lives ☐ I can open the same data in the UI, Swagger and psql.

## Stage 2: Python concepts used in the code
* **Inspect:** `docs/PYTHON_THROUGH_THE_CODE.md` next to `tickets/models.py`, `tickets/services.py`, `config/settings.py`.
* **Understand:** `None`, dicts/sets, kwargs, classes/inheritance, decorators, `with`, type hints, comprehensions.
* **Commands:** `python manage.py shell`, then try `Ticket.objects.filter(status="open").values_list("title", flat=True)`.
* **Modify:** add a `__str__` detail to `Comment` and see it in Django Admin; write a tiny helper using a list comprehension in the shell.
* **Checklist:** ☐ I can explain `@transaction.atomic` ☐ I know what `**kwargs` does in `create(self, request, *args, **kwargs)` ☐ I can read `dict[str, set[str]]` ☐ I know why `is None` is used.

## Stage 3: Follow one request through the system
* **Inspect:** `docs/ARCHITECTURE.md` section 2; then open every file named in its table.
* **Understand:** how "create ticket" travels from `TicketCreatePage.tsx` to `INSERT`, and back.
* **Commands:** `DJANGO_DEBUG=True DJANGO_SQL_LOG=True python manage.py runserver`; create a ticket in the UI; watch the SQL; in DevTools → Network inspect request, headers, payload, response.
* **Modify:** put `breakpoint()` in `TicketViewSet.create`, create a ticket, inspect `serializer.validated_data` and `request.user`.
* **Checklist:** ☐ I can name the 14 steps and their files ☐ I know which step returns 401, 403, 400, 404 ☐ I can find the INSERT in the SQL log.

## Stage 4: Models and database relationships
* **Inspect:** `tickets/models.py`, `accounts/models.py`, both `migrations/0001_initial.py`, `docs/DATABASE.md`.
* **Understand:** FKs, `on_delete` choices, CHECK/UNIQUE constraints, indexes, how Meta becomes DDL.
* **Commands:** `python manage.py sqlmigrate tickets 0001`; in psql `\d tickets_ticket`; run the SQL examples from `DATABASE.md` and their ORM twins with `print(qs.query)`.
* **Modify:** add a nullable `due_date` field with a migration (follow `DATABASE.md` §6); try deleting a user who has tickets (observe `PROTECT`).
* **Checklist:** ☐ I can draw the ER diagram from memory ☐ I can explain N+1 and the fix ☐ I know why a model change alone doesn't alter PostgreSQL ☐ I can explain `select_for_update`.

## Stage 5: Authentication and permissions
* **Inspect:** `accounts/views.py`, `accounts/permissions.py`, `tickets/permissions.py`, `TicketViewSet.get_queryset`, `frontend/src/api/client.ts`, `hooks/useAuth.tsx`, `ARCHITECTURE.md` §3-4.
* **Understand:** access vs refresh token, HttpOnly cookie, 401 vs 403 vs 404, three layers of authorization, why hiding a button is not security.
* **Commands:** the curl examples in `docs/API.md`; DevTools → Application → Cookies; decode an access token's payload (middle segment, base64) to see `user_id`/`exp`.
* **Modify/test:** read `test_auth.py` and `test_permissions.py`; add a test that a customer cannot `PATCH` an agent-only field of someone else's ticket; call an agent-only endpoint as a customer with curl.
* **Checklist:** ☐ I can explain the login → refresh flow ☐ I know what each layer enforces ☐ I can explain CSRF vs CORS ☐ I know what is *not* done for production (rotation, throttling).

## Stage 6: React-to-Django integration
* **Inspect:** `frontend/src/api/*`, `api/errors.ts`, `types/index.ts`, `hooks/useFetch.ts`, `pages/TicketListPage.tsx`, `pages/TicketDetailPage.tsx`.
* **Understand:** service functions, interceptors, typed responses, loading/error/empty states, URL-driven filters and pagination, `describeError` and its three failure categories.
* **Commands:** `npm run typecheck`; in DevTools block the backend (stop it) and watch the UI error; filter *Fetch/XHR* and read a preflight `OPTIONS` request.
* **Modify:** add a `priority` column sort to the list (backend `ordering_fields` allows only `created_at/updated_at/id`: why?), or add an "Assigned to me" filter end-to-end (backend filter + API function + UI).
* **Checklist:** ☐ I can find a request in Network and match it to a function in `api/` ☐ I can tell CORS vs 401 vs 500 apart ☐ I know why the types can lie.

## Stage 7: Run and understand the automated tests
* **Inspect:** `tests/conftest.py`, then `test_tickets.py`, `test_assignment_status.py`, `test_db_constraints.py`.
* **Understand:** fixtures, `APIClient`, test DB created from migrations and rolled back per test, API vs database-level tests, `django_assert_max_num_queries`, why `mock.patch` proves transactions.
* **Commands:** `python -m pytest -v`, `-k pagination`, `-x --pdb`, `--create-db`, `python -m pytest --collect-only -q | head`.
* **Modify:** temporarily break a rule (e.g. allow customers to PATCH priority) and see exactly which tests fail; revert.
* **Checklist:** ☐ I can say what a failing test is telling me ☐ I can decide if the test or the app is wrong ☐ I know why each test runs in a transaction.

## Stage 8: Investigate and fix the deliberate bugs
* **Inspect:** `docs/DEBUGGING.md` (method, DevTools, tracebacks), then `DEBUGGING_EXERCISES.md`.
* **Understand:** the 9-step process; layer identification; symptom vs root cause.
* **Commands:** use a branch per exercise (`git switch -c exercise/NN`), `git diff` to see your injected change, `git restore .` to clean.
* **Modify:** do exercises 01-12 *without* the solutions; write a regression test for each fix where possible (09, 11 and 12 especially).
* **Checklist:** ☐ I reproduced before fixing ☐ I can name the failing layer in each case ☐ I wrote at least three regression tests ☐ I only read solutions after a real attempt.

## Stage 9: Make a small feature change
Suggested: **"Add a due date to tickets"** end-to-end.
1. Model field + migration (`DATABASE.md` §6). 2. Serializer fields (create/update/read). 3. Permission: only staff may set it.
4. Backend tests (create with date, customer cannot set, invalid date → 400). 5. `docs/API.md` update. 6. TypeScript type + form input + list column.
7. `git switch -c feature/due-date`, commit in small steps, run `pytest` and `npm run typecheck` before each commit.
* **Checklist:** ☐ migration reviewed with `sqlmigrate` ☐ tests written first or alongside ☐ contract updated in all four places (serializer, docs, types, UI) ☐ diff reviewed with `git diff main...HEAD`.

## Stage 10: Review the app as a lead engineer
Write a one-page review answering: What would you change before deployment (`ARCHITECTURE.md` §10)? Which indexes are redundant
(`pg_stat_user_indexes`)? Where could authorization drift? What is untested (frontend behaviour, refresh interceptor, concurrency)?
Which dependency/security checks belong in CI? What logs/metrics would you want when this breaks at 2 a.m.? What would a safe
rollout and rollback of a migration look like? How would you onboard a new developer using these docs?
* **Checklist:** ☐ I can walk someone through the request lifecycle in 5 minutes ☐ I can list five production gaps and propose fixes ☐ I can triage a bug report to a layer within minutes ☐ I know when AI help is useful (explaining a traceback, drafting a test) and how I verify its suggestions (reproduce, run tests, read the diff).

## Using AI tools effectively while debugging
Give the assistant *evidence*, not just the symptom: the exact error text/traceback, the failing request (cURL) and response body, the
relevant file(s), what you already tried. Ask for hypotheses and how to test each, not just a patch. Then **verify**: reproduce, apply the
smallest change, run tests, read the diff. Never paste secrets (`.env`, tokens, real data).
