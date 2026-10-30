# Debugging guide

## 1. The process (use it every time)

1. **Reproduce** the issue reliably; write down exact steps, user/role, URL, input.
2. **Gather evidence** before theorising: browser Console + Network, backend console/traceback, database rows, `git log`.
3. **Identify the failing layer** (table below).
4. **Form a hypothesis** that predicts something you can check ("if the filter is dropped, the SQL has no WHERE").
5. **Test it** with the cheapest experiment (curl, `shell`, psql, one `print`/breakpoint).
6. **Smallest safe fix**, in the layer that is actually wrong.
7. **Run the relevant tests**, then the whole suite.
8. **Verify** the original reproduction now behaves.
9. **Check for regressions** (`git diff`, neighbouring features) and **add a regression test** that fails without the fix.

*Symptom vs root cause:* "the list is empty" is a symptom. Root cause might be a wrong URL, a 401 the UI swallowed, a filter
param, a scoping bug, or no rows. Do not "fix" by patching the symptom in the layer where you noticed it.

## 2. Which layer is failing?

| Evidence | Layer |
|---|---|
| Nothing in the Network tab when you click | frontend (handler not wired, JS error in Console, `preventDefault` missing, validation blocked it) |
| Request shows red, no status, Console says CORS / `net::ERR_*` | browser↔server connectivity: server down, wrong URL/port, CORS misconfig |
| 401 | authentication: missing/expired token, refresh cookie missing, wrong header format |
| 403 | authorization: valid user, forbidden by a permission/serializer rule |
| 404 | routing (wrong URL/prefix/slash), or object hidden by `get_queryset`, or really missing |
| 400 | validation: read `error.fields` in the response body |
| 500 | backend code or database: read the **server console** traceback |
| 200 but UI blank/stale | frontend rendering/state, or contract mismatch (field name/type) |
| Backend data right in psql but API wrong | serializer/queryset/filters |

**CORS vs auth vs server errors are different:** CORS errors have *no HTTP status* in the page (the browser blocks the
response; the server may well have processed it: check the server log). 401/403 are deliberate server answers about identity/permission.
500 means a server bug. Changing CORS settings never fixes a 401, and re-logging in never fixes CORS.

## 3. Browser DevTools

* **Console**: red errors with file:line (click through); `Access to XMLHttpRequest ... blocked by CORS policy` is CORS; `TypeError: Cannot read properties of undefined` usually means the data shape is not what the code expects.
* **Network** (filter *Fetch/XHR*, tick *Preserve log*): click a request → **Headers** (final URL, method, status, request `Authorization`, response `Access-Control-Allow-Origin`), **Payload** (what was sent), **Response/Preview** (raw JSON/HTML), **Timing**. A `OPTIONS` request before a `POST` is the CORS *preflight*; if it fails, the real request never happens.
* **Application → Cookies**: is `refresh_token` there? `HttpOnly` ticked? Path `/api/auth/`?
* Compare **Response** JSON to `frontend/src/types/index.ts` field by field.
* Right-click request → *Copy as cURL* → paste in a terminal to reproduce without the browser.

Symptom recipes: **button does nothing** → Console error? Network request at all? (handler, `type="button"` vs submit, disabled state). **404** → compare Request URL with `urls.py` (prefix `/api/`, trailing `/`). **400** → read `error.fields`. **401** → is `Authorization` present? expired? try `/auth/refresh/`. **403** → which role? which permission class? **500** → server traceback. **Stale data** → state not reloaded after mutation (`reload()`), cached query key (`useFetch` deps), or looking at the wrong page/filter. **Valid JSON but nothing shown** → wrong property name, `undefined` filtered out, rendering condition. **Field-name disagreement** → backend uses snake_case (`assigned_to`), JS tends toward camelCase; fix the *type* and the code, not the serializer, unless the contract itself changes.

## 4. Reading a Python traceback

```
Traceback (most recent call last):
  File ".../rest_framework/views.py", line 506, in dispatch      <- framework frames (usually not the bug)
  File "/app/tickets/views.py", line 62, in create                <- YOUR code: start here
    ticket = serializer.save(created_by=request.user)
  File "/app/tickets/serializers.py", line 44, in validate_title
    return value.strip().title
AttributeError: 'builtin_function_or_method' object has no attribute ...   <- the actual exception, last line
```
Read **bottom-up for the exception type and message**, then **upward to the first frame inside your project**. With chained
exceptions ("During handling of the above exception, another exception occurred") the **first** exception is usually the root cause.

## 5. Following a request through the code

URL → `config/urls.py` → app `urls.py` → View/ViewSet method → `get_queryset`/permissions → serializer (`is_valid`, `validate_*`) →
ORM call/service → SQL → response serializer. Put `breakpoint()` at the suspected frame (the dev server stops in a terminal debugger; `n` next, `s` step in, `p var`, `c` continue) or run tests with `pytest --pdb`.

## 6. Commands

```bash
python manage.py check                         # config + wiring
python manage.py check --deploy                # production readiness warnings
python manage.py showmigrations                # applied vs pending
python manage.py makemigrations --check --dry-run   # model/migration drift
python manage.py sqlmigrate tickets 0001
python manage.py dbshell                       # psql with Django's credentials
python manage.py shell                         # REPL with Django loaded
python manage.py diffsettings                  # settings that differ from defaults
curl -s localhost:8000/api/health/             # is the backend up and is the DB reachable?
DJANGO_DEBUG=True DJANGO_SQL_LOG=True python manage.py runserver    # every SQL statement printed
docker compose logs -f backend db              # container logs
docker compose ps
pip list | grep -i -E 'django|rest|psycopg'   # what is actually installed
python -c "import django,sys;print(django.get_version(), sys.executable)"   # which Python/venv are you in?
```
In `shell`:
```python
from tickets.models import Ticket
Ticket.objects.count(); Ticket.objects.filter(status="open").values("id", "title")[:5]
from tickets.serializers import TicketCreateSerializer
s = TicketCreateSerializer(data={"title": "abc", "description": "x"}); s.is_valid(); s.errors
```
SQL: `SELECT id, status, assigned_to_id FROM tickets_ticket ORDER BY id DESC LIMIT 5;` and `SELECT app, name FROM django_migrations ORDER BY id;`.

## 7. Configuration, migration, dependency and environment problems

* **Configuration:** `ImproperlyConfigured`, wrong host/port, CORS origin typos (scheme and port must match exactly: `http://localhost:5173` ≠ `http://127.0.0.1:5173`). Check `.env` vs `.env.example`, then `diffsettings`. Frontend env: `VITE_*` values are baked in when `npm run dev` starts, so **restart Vite** after editing `.env`.
* **Migrations:** "relation/column does not exist" → pending migration; `makemigrations --check` shows drift; conflicts → `makemigrations --merge`. Never "fix" by dropping tables.
* **Dependencies:** `ModuleNotFoundError` = wrong/inactive virtualenv or missing install (`which python`, `pip list`). Version mismatch after pulling → `pip install -r requirements-dev.txt`, `npm install`. Inspect `requirements.txt`/`package.json` diffs in `git log -p`.
* **Safe vs risky:** resetting a *local throw-away* database is fine for a local experiment. Dropping/truncating data, `migrate --fake`, or editing applied migrations are last resorts that need a backup and an understanding of why; never routine, never in production.

## 8. Logging and safe error handling

Use `logging.getLogger(__name__)`; `logger.exception("...")` inside `except` records the traceback. Do not log passwords, tokens, or full request bodies for auth routes. Clients get generic messages for 500s; developers get details in logs (see `config/exceptions.py`).

## 9. Tests: what failed, and is the test wrong?

Run one test: `python -m pytest tests/test_tickets.py::TestCreate::test_customer_creates_ticket_and_it_is_persisted -x -vv`.
Read: the `assert` line, the **actual vs expected** values pytest prints, then `response.data` (add `print(response.data)`; run with `-s`).
*Broken app or broken test?* Reproduce the same request manually (curl / Swagger). If the app behaves as the documented rules say and
the test disagrees, the test is wrong (stale assumption, wrong fixture user, missing authentication → 401 instead of the status you expected).
If the app violates the documented rule, the app is wrong. Also suspect test setup when many unrelated tests fail at once (DB
connection, migrations, missing `.env`): run `python manage.py check` and `pytest --create-db`.

## 10. Git workflow for maintenance

```bash
git status                       # what changed locally
git branch --show-current        # where am I
git log --oneline -10            # recent history
git log --oneline -- backend/tickets/views.py     # history of one file
git log -p -3 -- backend/tickets/serializers.py   # recent changes with diffs
git blame -L 40,60 backend/tickets/services.py    # who/when/why a line changed
git grep -n "assigned_to"        # find every use (also: git grep -n "def assign")
git diff                         # unstaged changes; `git diff --staged` for staged; `git diff main...HEAD` for a branch
git show <commit>                # one commit's message and diff; `git show --stat <commit>` for files only
git diff --name-only main        # which files does this change affect?
git switch -c fix/ticket-assign-null          # create a branch
cd backend && python -m pytest && cd ../frontend && npm run typecheck     # test BEFORE committing
git add -p                       # stage hunks deliberately
git commit -m "Fix: allow unassigning a ticket; add regression test"
```
Investigating an unfamiliar app: read `README.md` → `requirements.txt`/`package.json` (what stack?) → `settings.py` (apps, DB, middleware) → root `urls.py` → one feature end-to-end → `migrations/` (schema history) → tests (documented behaviour) → `git log` (what changed lately).
