# Django Full-Stack Learning Lab: Helpdesk and Support Portal

A small but realistic helpdesk (customers raise tickets, agents work them, admins manage users) built to
teach you **how a Django + React company application fits together and how to debug it**. The code is
deliberately conventional; the documentation is where the teaching happens.

> **Status honesty:** this project was written without network access, so dependencies were not installed and
> PostgreSQL was never started while it was generated. Python syntax was checked; **tests, migrations and the
> frontend build have not been executed yet.** Your first job is the "Verify the project" section below. Treat any
> failure there as your first real debugging exercise (see `docs/DEBUGGING.md`).

## Architecture at a glance

```
Browser (React + TypeScript + Vite, :5173)
   │  Axios, JSON over HTTP, Bearer access token + HttpOnly refresh cookie
   ▼
Django + Django REST Framework (:8000)      urls.py → authentication → permissions → serializer → view → ORM
   │  Django ORM (psycopg 3)
   ▼
PostgreSQL 16 (:5432)                       tables created by migrations
```

| Layer | Folder | What lives there |
|---|---|---|
| Project config | `backend/config/` | `settings.py`, root `urls.py`, error format, pagination, health check |
| Users and auth | `backend/accounts/` | custom `User` (role), JWT login/refresh/logout, profile, admin user management |
| Tickets | `backend/tickets/` | `Ticket`, `Comment`, API, business rules (`services.py`), seed command |
| Dashboard | `backend/dashboard/` | aggregate statistics |
| Tests | `backend/tests/` | pytest API + database tests |
| Frontend | `frontend/src/` | `api/` (Axios), `pages/`, `components/`, `hooks/`, `types/` |
| Docs | `docs/` | see the table below |

Chosen versions: Python 3.10-3.13 (Docker uses 3.12), Django 5.1, DRF 3.15, SimpleJWT 5.3, PostgreSQL 16,
React 18, TypeScript 5.6, Vite 5, React Router 6, Axios 1.7. They are pinned in `backend/requirements.txt` and
`frontend/package.json`. They were pinned from knowledge, not resolved by an installer, so if `pip` or `npm`
reports a conflict, bump the version it names and note it in your commit message.

## Prerequisites

* Docker + Docker Compose (easiest), **or** Python 3.12, Node 20+, and PostgreSQL 16 installed locally.
* Optional: `psql` or pgAdmin to look at the database.

## Setup: Docker (recommended)

```bash
cp .env.example .env            # then edit the two "change-me" passwords and the secret key
docker compose up --build       # starts db, backend (runs migrations), frontend
docker compose exec backend python manage.py seed_demo_data          # sample data (uses SEED_PASSWORD from .env)
docker compose exec backend python manage.py createsuperuser         # your own admin account (optional)
```

Open http://localhost:5173 (app), http://localhost:8000/api/docs/ (Swagger UI), http://localhost:8000/admin/ (Django Admin).

## Setup: local processes (database in Docker, code on your machine)

```bash
cp .env.example .env
docker compose up -d db                                 # only PostgreSQL

cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver                              # http://localhost:8000

cd ../frontend                                          # second terminal
cp .env.example .env
npm install
npm run dev                                             # http://localhost:5173
```

Sample logins after seeding: `alice.customer`, `bob.customer`, `carol.customer`, `dave.agent`, `erin.agent`,
`frank.admin`, all with the password you set as `SEED_PASSWORD`. No default password exists anywhere in the repo.

## Database access

```bash
docker compose exec db psql -U helpdesk -d helpdesk        # inside the container
psql -h localhost -p 5432 -U helpdesk -d helpdesk          # from your machine (uses POSTGRES_PASSWORD)
cd backend && python manage.py dbshell                     # via Django, using settings.py credentials
```
Inside psql: `\dt` lists tables, `\d tickets_ticket` shows columns, indexes and constraints. pgAdmin: add a server
with host `localhost`, the port/user/password from `.env`. Details in `docs/DATABASE.md`.

## Verify the project (do this first)

```bash
cd backend
python manage.py check                         # settings, apps, URL wiring
python manage.py makemigrations --check --dry-run   # expect "No changes detected": models and migrations agree
python manage.py migrate                       # creates all tables in an empty database
python -m pytest                               # whole backend suite (creates/destroys test_helpdesk automatically)
cd ../frontend && npm run typecheck && npm run build
```
If `makemigrations --check` reports changes, the hand-written migrations drifted from the models; run
`python manage.py makemigrations` and read the generated diff, that is a good migrations lesson.

## Running tests

```bash
cd backend
python -m pytest                       # everything
python -m pytest tests/test_tickets.py -k pagination -v      # one file, tests matching a keyword
python -m pytest -x --pdb              # stop at first failure and open the debugger
python -m pytest --create-db           # rebuild the test database if schema and tests disagree
```
Frontend checks: `npm run typecheck` (TypeScript) and `npm run build` (typecheck + bundle). There are no
frontend unit tests; the API contract is covered by backend tests plus the TypeScript types.

## Troubleshooting (quick table; full guide in `docs/DEBUGGING.md`)

| Symptom | Likely cause | First check |
|---|---|---|
| `ImproperlyConfigured: Environment variable ... required` | no `.env` | `cp .env.example .env` |
| `connection refused` / `could not translate host name "db"` | DB not running, or `POSTGRES_HOST` wrong for where Django runs (`localhost` on your machine, `db` in Compose) | `docker compose ps`, `curl localhost:8000/api/health/` |
| `password authentication failed` | `.env` password differs from the one the DB volume was first created with | Compose only reads `POSTGRES_PASSWORD` the first time; see `docs/DATABASE.md` section on credentials |
| `relation "tickets_ticket" does not exist` | migrations not applied | `python manage.py showmigrations`, then `migrate` |
| Browser: CORS error | origin not in `CORS_ALLOWED_ORIGINS` | Network tab, response headers; `docs/DEBUGGING.md` |
| Every request 401 after some minutes | access token expired and refresh cookie missing/blocked | Application tab → Cookies |
| Port 5432 already in use | local PostgreSQL | change `POSTGRES_HOST_PORT` in `.env` |

## Documentation map

| File | Read it to learn |
|---|---|
| `docs/LEARNING_GUIDE.md` | the 10-stage study path (start here after setup) |
| `docs/ARCHITECTURE.md` | request lifecycle with diagram, every Django component, auth design, security |
| `docs/PYTHON_THROUGH_THE_CODE.md` | the Python you need, taught from this codebase, compared with Java/JS |
| `docs/DATABASE.md` | schema, ER diagram, SQL vs ORM, transactions, migrations, backups |
| `docs/API.md` | every endpoint, auth, errors, examples |
| `docs/DEBUGGING.md` | the debugging method, DevTools, tracebacks, Git workflow |
| `docs/DEBUGGING_EXERCISES.md` | 12 deliberate-bug exercises (no answers) |
| `docs/DEBUGGING_SOLUTIONS.md` | the answers, kept separate so you can try first |

## What is NOT production-ready

Not reviewed or built for deployment: no HTTPS termination, rate limiting/lockout on login, refresh-token rotation
and revocation, email verification or password reset, file attachments, structured/centralised logging,
monitoring, backup automation, CSP headers, dependency vulnerability scanning, or a production web server
(`runserver` is for development only). `docs/ARCHITECTURE.md` section 10 lists a deployment review checklist.
