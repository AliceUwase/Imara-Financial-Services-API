# Imara Financial Services — Deployment Guide

---

## Environment Variables

Copy `.env.example` to `.env` and fill in every value before starting the application.
Never commit `.env` — it is listed in `.gitignore`.

| Variable | Required | Safe default (dev) | Production value |
|----------|----------|--------------------|-----------------|
| `DJANGO_SECRET_KEY` | Yes | *(see .env.example)* | Long random string, unique per environment |
| `DEBUG` | Yes | `True` | `False` |
| `ALLOWED_HOSTS` | Yes | `localhost,127.0.0.1,testserver` | Your domain or server IP |
| `CELERY_BROKER_URL` | Yes | `redis://localhost:6379/0` | `redis://redis:6379/0` (Docker Compose) |
| `CELERY_RESULT_BACKEND` | Yes | `redis://localhost:6379/0` | `redis://redis:6379/0` (Docker Compose) |
| `SECURE_COOKIES` | Yes | `False` | `True` (requires HTTPS) |

> **Note:** The variable name is `DJANGO_SECRET_KEY`, not `SECRET_KEY`.
> Copying `.env.example` without renaming the key will silently fall back
> to the insecure development default.

---

## Local Development

**Prerequisites**
- Python 3.13
- Redis running locally
- A virtual environment activated

**Steps**

```bash
git clone <repo-url>
cd <repo-directory>
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env — set DJANGO_SECRET_KEY, leave DEBUG=True
# Set CELERY_BROKER_URL=redis://localhost:6379/0
python manage.py migrate
python manage.py runserver
```

To run the Celery worker in a second terminal:

```bash
celery -A imara worker --loglevel=info
```

---

## Running the Test Suite

Tests use an in-memory SQLite database and require no running services.

```bash
# Full suite (60 tests)
python manage.py test --verbosity=2

# Single app
python manage.py test financing.tests --verbosity=2
python manage.py test merchants.tests --verbosity=2
python manage.py test common.tests --verbosity=2
```

Expected output: `Ran 60 tests in Xs ... OK`

| Layer | Test classes | Focus |
|-------|-------------|-------|
| Unit | `TestPermissionClasses`, `TestGetRole`, `TestGetClientIp`, `TestFinancingSerializerUnit` | Individual functions and validators |
| Integration | `TestMerchantCreate`, `TestTokenLogin`, `TestMerchantDetail` | Full HTTP request/response cycle |
| Security / role-boundary | `TestFinancingListRoleBoundaries`, `TestMerchantOwnership` | Privacy guarantees and auth gates |
| Bug regression | `TestFinancingValidation`, `TestFinancingAtomicity`, `TestFinancingAuditLog` | Guards against the four confirmed bugs |

---

## Docker Deployment

**Prerequisites**
- Docker and Docker Compose installed
- No other local dependencies required

**Steps**

```bash
git clone <repo-url>
cd <repo-directory>
cp .env.example .env
# Edit .env — set at minimum:
#   DJANGO_SECRET_KEY=<long-random-string>
#   DEBUG=False
#   ALLOWED_HOSTS=<your-domain-or-IP>
#   CELERY_BROKER_URL=redis://redis:6379/0
#   CELERY_RESULT_BACKEND=redis://redis:6379/0
docker compose up --build
```

The API is available at `http://localhost:8000`.

---

## What Runs on Startup

The `web` container executes three steps in order before accepting traffic:

1. `python manage.py migrate` — applies all pending database migrations
2. `python manage.py collectstatic --no-input` — writes static files to `staticfiles/`
3. `gunicorn imara.wsgi:application --bind 0.0.0.0:8000 --workers 2` — starts the production WSGI server

The `worker` container starts the Celery background worker connected to Redis.

---

## Runtime Architecture

```
┌──────────────────────────────────────────┐
│             Docker Compose               │
│                                          │
│  ┌──────────┐      ┌──────────┐         │
│  │   web    │      │  worker  │         │
│  │ gunicorn │      │  celery  │         │
│  │ 2 workers│      │          │         │
│  └────┬─────┘      └────┬─────┘         │
│       │                 │               │
│       └────────┬─────────┘              │
│                │                        │
│          ┌─────▼──────┐                 │
│          │   redis    │                 │
│          │  broker    │                 │
│          └────────────┘                 │
│                                         │
│  Database: SQLite (inside container)    │
└──────────────────────────────────────────┘
```

---

## Operational Readiness Signals

| Signal | Status | Location |
|--------|--------|---------|
| `DEBUG` from env var | ✅ | `settings.py` — `config('DEBUG', ...)` |
| `ALLOWED_HOSTS` from env var | ✅ | `settings.py` — `config('ALLOWED_HOSTS', ...)` |
| `DJANGO_SECRET_KEY` from env var | ✅ | `settings.py` — `config('DJANGO_SECRET_KEY', ...)` |
| `SECURE_COOKIES` from env var | ✅ | `settings.py` — `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` |
| `gunicorn` as production server | ✅ | `docker-compose.yml` web command; `requirements.txt` |
| `collectstatic` runs before server start | ✅ | `docker-compose.yml` web command; `STATIC_ROOT` in `settings.py` |
| `.env` excluded from version control | ✅ | `.gitignore` |
| `.env.example` documents all variables | ✅ | `.env.example` |
| Health endpoint available | ✅ | `GET /api/health/` → `{"status": "ok"}` |
| Full test suite passes | ✅ | 60 tests, 0 failures |

---

## Stopping and Restarting

```bash
docker compose down        # stop and remove containers
docker compose up          # restart (skips image rebuild)
docker compose up --build  # restart and rebuild the image
```
