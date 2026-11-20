# Imara Financial Services — MVP

Imara is an MVP merchant onboarding and financing-request platform built
for users on unstable mobile data. This repository contains all three
increments: F1 (core API), F2 (compliance and RBAC), and the summative
release-hardening stage which fixes four security and data-integrity bugs,
adds Docker deployment support, and extends the test suite to 66 tests.

See [`BUG_REPORT.md`](./BUG_REPORT.md) for a full description of the four
bugs found and fixed in the summative increment.

 `schema.yaml` at the repository root

---

## Prerequisites

You will need the following installed before starting:

- **Python 3.11 or newer** (tested on 3.13)
- **A Redis-compatible server** running on `localhost:6379`. On Windows
  the easiest option is [Memurai](https://www.memurai.com/get-memurai)
  (free Developer Edition); on macOS or Linux, install Redis through
  your package manager. Docker is also fine: `docker run -d -p 6379:6379 redis:7-alpine`.
- **Git** for cloning the repository.

---

## Local Setup

Run these commands in order, in a new terminal, from the directory
where you cloned the repository.

### 1. Create and activate a virtual environment

On Windows (Git Bash):

```bash
py -m venv .venv
source .venv/Scripts/activate
```

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

You should see `(.venv)` at the start of your prompt.

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create your environment file

```bash
cp .env.example .env
```

Open `.env` in an editor and confirm the default values are appropriate
for your machine. See the [Environment Variables](#environment-variables)
section below for what each variable controls.

### 4. Apply database migrations

```bash
py manage.py migrate
```

This creates a SQLite database file (`db.sqlite3`) with all the
required tables.

### 5. Create a superuser for the Django admin

```bash
py manage.py createsuperuser
```

Pick any username, email, and password. You will use this to log in to
The admin at `/admin/` for inspecting data.

### 6. Create test users for API access

The API uses token authentication with two roles (merchant and lender).
Create one user of each role through the Django shell:

```bash
py manage.py shell
```

Then inside the shell:

```python
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from common.models import UserProfile

merchant_user = User.objects.create_user(username='merchant1', password='testpass123', email='merchant1@test.com')
UserProfile.objects.create(user=merchant_user, role='merchant')
merchant_token = Token.objects.create(user=merchant_user)
print(f'Merchant token: {merchant_token.key}')

lender_user = User.objects.create_user(username='lender1', password='testpass123', email='lender1@test.com')
UserProfile.objects.create(user=lender_user, role='lender')
lender_token = Token.objects.create(user=lender_user)
print(f'Lender token: {lender_token.key}')

exit()
```

Save both tokens — you will use them in the example requests below.

### 7. Start the Django development server

```bash
py manage.py runserver
```

The API is now reachable at `http://127.0.0.1:8000/`. Visit
`http://127.0.0.1:8000/api/schema/swagger-ui/` for interactive API
documentation.

### 8. Run the test suite

```bash
python -m pytest --tb=short -q
```

All 66 tests should pass. The suite covers serializer validation,
cross-merchant ownership enforcement, atomic writes, audit logging,
role boundary checks, token login, session login, and the health
endpoint. No additional setup is required, the tests use an isolated
in-memory database and do not depend on Redis or the Celery worker.

---

## Environment Variables

The application reads configuration from a `.env` file at the project
root using `python-decouple`. A template is provided in `.env.example`;
copy it to `.env` before running.

| Variable | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | `change-me` | Django's cryptographic key. Set to a unique random value in production. |
| `DEBUG` | `True` | Enables Django's debug mode. Must be `False` in production. |
| `ALLOWED_HOSTS` | `127.0.0.1,localhost` | Comma-separated list of hostnames the server will accept. |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Where Celery queues tasks. Must match your Redis instance. |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/0` | Where Celery stores task results. |

`.env` is gitignored. Never commit real secrets to the repository;
`.env.example` documents the structure without leaking values.

---

## Docker Deployment

The project ships a `Dockerfile` and `docker-compose.yml` for
containerised deployment. Docker Compose starts the Django application
(via Gunicorn), a Celery worker, and a Redis instance together.

```bash
docker compose up
```

The API will be available at `http://localhost:8000/`. Migrations run
automatically on container startup.

For full environment variable requirements, production configuration
notes, and manual deployment steps, see [`DEPLOYMENT.md`](./DEPLOYMENT.md).

---

## Running the Async Worker

Financing request creation and updates dispatch a background alert via
Celery. The Django web process does not block on alert delivery, the
API returns immediately and the worker processes the alert
asynchronously.

### 1. Confirm Redis is running

```bash
py -c "import redis; r = redis.Redis(); print(r.ping())"
```

You should see `True`. If you see `ConnectionRefusedError`, your Redis
server is not running.  Check [Prerequisites](#prerequisites).

### 2. Start the Celery worker (in a separate terminal)

Activate the virtual environment in the new terminal, then:

```bash
celery -A imara worker --loglevel=info --pool=solo
```

The `--pool=solo` flag is required on Windows. On macOS or Linux you
can omit it to use Celery's default pool.

The worker prints a banner listing registered tasks. Confirm that
`financing.tasks.send_financing_alert` appears under the `[tasks]`
section.

### 3. Verify the async flow end-to-end

With the Django server running, the worker running, and Redis up,
create a financing request via the API (see
[Example Requests](#example-requests) below). The API should respond
within milliseconds. The worker terminal should log an `ALERT [created]:`
line shortly after, and a corresponding `AlertAttempt` row should
appear in the Django admin under **Financing → Alert attempts**.

---

## Example Requests

All examples assume the Django server is running at `http://127.0.0.1:8000/`.
The project exposes the F1-facing API on unversioned `/api/` paths so
that the autograder can reach them directly. Replace `MERCHANT_TOKEN`,
`LENDER_TOKEN`, and any `MERCHANT_ID` with values from your setup. Token
authentication uses the header `Authorization: Token <key>` (note the
literal word `Token`).

### Register a new merchant

`POST /api/merchants/` is open to unauthenticated callers (registration
must work before a token exists). The F1 autograder expects this
endpoint to return a small integer `id` that maps to the created
merchant (see Index models below).

```bash
curl -X POST http://127.0.0.1:8000/api/merchants/ \
  -H "Content-Type: application/json" \
  -d '{"business_name":"Sunrise Bakery","owner_name":"Jane Doe","email":"jane@sunrise.com","phone":"+250788123456","country":"Rwanda"}'
```

Expected response: `201 Created` with a JSON body containing a small
integer id, for example:

```json
{ "id": 1 }
```

Notes:
- Merchant creation is idempotent by `email`: if the email already
  exists the view returns `201` with the existing integer id rather
  than failing with a 400/IntegrityError. This supports repeatable
  autograder runs.
- Internally merchants use UUID primary keys; the integer `id` is
  provided by a separate `MerchantIndex` model that maps to the UUID.

### Obtain a token (token login)

Use this to get a token for a user created in step 6 of Local Setup.

```bash
curl -X POST http://127.0.0.1:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"merchant1","password":"testpass123"}'
```

Expected response: `200 OK`:

```json
{ "token": "abc123...", "username": "merchant1", "role": "merchant" }
```

Copy the `token` value and use it as `MERCHANT_TOKEN` in the requests
below. Wrong credentials return `400 Bad Request`.

### Session login (staff and admin users)

Staff and compliance users can authenticate via session cookie instead
of a token.

```bash
curl -X POST http://127.0.0.1:8000/api-auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"yourpassword"}'
```

Expected response: `200 OK`:

```json
{ "username": "admin", "role": "compliance" }
```

The session cookie is set automatically. Wrong credentials return `400
Bad Request`.

### Retrieve a merchant profile

```bash
curl http://127.0.0.1:8000/api/merchants/1/ \
  -H "Authorization: Token MERCHANT_TOKEN"
```

Expected response: `200 OK` with the merchant's public record. The
response includes the `contact_email` and other public fields; the
internal UUID is not required by the autograder.

### Submit a financing request

The POST endpoint accepts unauthenticated requests to preserve backwards
compatibility with the F1 contract. If an authenticated merchant token is
provided, the ownership check runs and the request is rejected with `403`
if the merchant ID in the body does not belong to that user.

```bash
curl -X POST http://127.0.0.1:8000/api/financing/requests/ \
  -H "Content-Type: application/json" \
  -d '{"merchant":1,"amount":"5000.00","currency":"USD","purpose":"Inventory restocking for the upcoming quarter"}'
```

Expected response: `201 Created` with a JSON body containing the new
integer `id` for the financing request, for example:

```json
{ "id": 1 }
```

An `AlertAttempt` should appear in the Django admin shortly after if
the Celery worker and Redis are running.

### List submitted financing requests as a lender

Lenders, compliance users, and merchants all use the same endpoint. The
records returned differ by role: merchants see only their own requests,
lenders and compliance see all of them.

```bash
curl http://127.0.0.1:8000/api/financing/requests/ \
  -H "Authorization: Token LENDER_TOKEN"
```

Expected response: `200 OK` with a plain list:

```json
[
  { "id": 1, "merchant": 1, "amount": "5000.00", "currency": "USD", "purpose": "Inventory restocking for the upcoming quarter", "status": "submitted" }
]
```

Unauthenticated callers and users with the support role receive `401` or
`403` respectively.

### Verify a validation error

Use the integer merchant id when testing validation errors against the
F1-facing endpoint:

```bash
curl -X POST http://127.0.0.1:8000/api/financing/requests/ \
  -H "Authorization: Token MERCHANT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"merchant":1,"amount":"-100","currency":"USD","purpose":"Should fail"}'
```

Expected response: `400 Bad Request`:

```json
{
  "amount": ["Amount must be greater than zero."]
}
```

---

## Authentication
The API uses two mechanisms for authentication according to the client type:

- **Staff (compliance/admin)** authenticate by **session** (cookie) login,
  via the Django admin and the browsable API at `/api-auth/login/`.
- **API consumers (merchants, lender partners)** use **token** auth. POST
  credentials to `/api/auth/token/` to receive a token, then send it on
  every request:

```
  Authorization: Token <your-token>
```
### Authentication vs authorization
- Missing / invalid credentials → **401 Unauthorized** (the system can't
  tell who you are).
- A valid user whose role isn't permitted → **403 Forbidden** (known
  identity, limited rights).

## Roles and access boundaries

Access is `role-based` and `data-aware`: the role decides which endpoints a
user may reach, and a per-record filter decides which rows they are to see.

| Role            | List financing (GET)         | Create financing (POST)              | Audit log   |
|-----------------|------------------------------|--------------------------------------|-------------|
| Unauthenticated | No (401)                     | Yes (no ownership check applied)     | No          |
| Merchant        | Own merchant's requests only | Yes (blocked if submitting for another merchant) | No |
| Lender          | All requests                 | Yes (no ownership check applied)     | No          |
| Compliance      | All requests                 | Yes (no ownership check applied)     | Yes (admin) |
| Support         | No (403)                     | Yes (no ownership check applied)     | No          |
| Staff (is_staff)| All requests                 | Yes (no ownership check applied)     | No          |

## Audit logging and privacy

Every read of sensitive financial records is recorded in an append-only
`AccessLog`. Each entry stores **references only**, meaning that the user, their role,
the action, the record ids returned, the IP, and a timestamp. It
deliberately stores **no** amounts, currencies, purposes, or personal data,
so the audit trail won't itself leak the data it protects. Compliance users
review the trail in the admin (**Common → Access logs**), where it is
read-only and cannot be edited or deleted.

## Configuration

Secrets are read from environment variables — copy `.env.example` to `.env`
and fill in:

- `SECRET_KEY` Django signing key
- `DEBUG`  `False` in any shared environment
- `ALLOWED_HOSTS`  comma-separated hosts
- `SECURE_COOKIES`  `True` in production for HTTPS-only session/CSRF cookies

## What changed in F2 (compliance retrofit)
| Area      | In F1                                 | In F2                                          |
|-----------|----------------------------------------------|-------------------------------------------------------|
| Auth      | Financing endpoint open (`AllowAny`)         | Authentication required; anonymous returns 401              |
| Access    | Any caller saw all records                   | Role gate + per-record filter (merchant sees their own )|
| Visibility| No record of who viewed sensitive data       |  `AccessLog` on every sensitive read      |
| Authorization | Role had no effect on allowed actions | Create restricted to merchants; other roles get 403 |
| Secrets   | Keys in settings                             | Secrets in environment variables                      |

## What changed in Summative (release hardening)
| Area | In F2 | In Summative |
|---|---|---|
| Input validation | Financing POST bypassed serializer; any data was accepted | All POST data runs through `FinancingRequestSerializer` before saving |
| Ownership | Any merchant could submit for any other merchant's ID | Ownership check blocks cross-merchant submissions with 403 |
| Data integrity | Two database writes with no transaction; partial failure left orphaned rows | Both writes wrapped in `transaction.atomic()` and rolled back together on failure |
| Audit trail | Financing reads were logged; creates were not | `log_access()` called on every successful create with action `create_financing` |
| Staff access | `IsMerchantLenderOrCompliance` blocked staff users with no `UserProfile` | `is_staff` bypass added so Django staff users pass the permission check |
| Deployment | No container support | `Dockerfile`, `docker-compose.yml`, and `DEPLOYMENT.md` added |
| Test coverage | Tests covered F1 and F2 surface | 66 tests covering all four bug fixes plus auth and deployment readiness |

## API Documentation

The API was documented using the OpenAPI 3 standard. Three views of the schema are
available:

- **Static schema file (human-readable):** [`schema.yaml`](./schema.yaml) —
  versioned in this repository for review and documentation.
- **Autograder schema (root):** [`schema.yaml`](./schema.yaml) — the F1
  autograder expects a schema at the repository root. Regenerate with
  `py manage.py spectacular --file schema.yaml` (see below).
- **Interactive Swagger UI:** `http://127.0.0.1:8000/api/schema/swagger-ui/`
  when the server is running.
- **ReDoc rendering:** `http://127.0.0.1:8000/api/schema/redoc/` when
  the server is running.

The schema is auto-generated by `drf-spectacular` from the DRF view and
serializer definitions, so it stays in sync with the code by construction.

---

## Project Structure

```text
advanced-python-imara-AliceUwase/
├── imara/                  # Project configuration (settings, urls, celery)
├── merchants/              # Merchant onboarding domain
├── financing/              # Financing requests and async alerts
├── common/                 # Shared infrastructure (permissions, audit, UserProfile)
├── docs/                   # ADR template
├── .env.example            # Environment variable template
├── Dockerfile              # Container image definition
├── docker-compose.yml      # Multi-service orchestration (web, worker, redis)
├── manage.py               # Django entry point
├── requirements.txt        # Python dependencies
├── BUG_REPORT.md           # Summative bug analysis and fix documentation
├── DEPLOYMENT.md           # Deployment instructions and environment reference
├── README.md               # This file
└── ADR.md, schema.yaml     # Architecture decisions and OpenAPI schema
```

## Troubleshooting
 **`ConnectionRefusedError` when starting the Celery worker.** Redis is not running. Confirm with the ping check in the [Running the Async Worker](#running-the-async-worker) section. 

 **`OperationalError: table ... has no column named ...`.** Migrations have not been applied after a model change. Run `py manage.py makemigrations` and `py manage.py migrate`. 

 **Celery worker on Windows hangs or fails to pick up tasks.** The `--pool=solo` flag is mandatory on Windows. The default pool relies on `fork()`, which Windows does not support. 

 **`PermissionDenied: This endpoint is restricted to merchant accounts.`** The token in your `Authorization` header belongs to a user without the merchant role. Either use a different token or update the user's `UserProfile.role` through the Django admin.

 --- 
