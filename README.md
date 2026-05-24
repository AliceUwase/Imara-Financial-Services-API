# Imara Financial Services — MVP

Imara is an MVP merchant onboarding and financing-request platform built
for users on unstable mobile data. This repository contains the F1
increment: a runnable Django REST API with merchant registration,
financing request creation, a lender-facing feed, and an async alert
flow.

The architecture is documented in [`ADR.md`](./ADR.md). The API schema is in [`docs/openapi.yaml`](./docs/openapi.yaml).

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

## Running the Async Worker

Financing request creation and updates dispatch a background alert via
Celery. The Django web process does not block on alert delivery — the
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

All examples assume the Django server is running at
`http://127.0.0.1:8000/`. Replace `MERCHANT_TOKEN`, `LENDER_TOKEN`, and
`MERCHANT_UUID` with the values from your setup. Token authentication
uses the header `Authorization: Token <key>` (note the literal word
`Token`).

### Register a new merchant

`POST /api/v1/merchants/` is open to unauthenticated callers, since
registration must work before a token exists.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/merchants/ \
  -H "Content-Type: application/json" \
  -d '{"business_name":"Sunrise Bakery","owner_name":"Jane Doe","email":"jane@sunrise.com","phone":"+250788123456","country":"Rwanda"}'
```

Expected response: `201 Created` with the merchant record including a
generated UUID `id` and `status: "pending"`.

### Retrieve a merchant profile

```bash
curl http://127.0.0.1:8000/api/v1/merchants/MERCHANT_UUID/ \
  -H "Authorization: Token MERCHANT_TOKEN"
```

Expected response: `200 OK` with the merchant's full record.

### Submit a financing request

```bash
curl -X POST http://127.0.0.1:8000/api/v1/financing-requests/ \
  -H "Authorization: Token MERCHANT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"merchant":"MERCHANT_UUID","amount":"5000.00","currency":"USD","purpose":"Inventory restocking for the upcoming quarter"}'
```

Expected response: `201 Created` with the new financing request, status
`submitted`. An `AlertAttempt` will appear in the admin within a second
as the async alert is processed.

### List submitted financing requests as a lender

```bash
curl http://127.0.0.1:8000/api/v1/lender/financing-requests/ \
  -H "Authorization: Token LENDER_TOKEN"
```

Expected response: `200 OK` with a paginated payload:

```json
{
  "next": "http://127.0.0.1:8000/api/v1/lender/financing-requests/?cursor=...",
  "previous": null,
  "results": [
    { "id": "...", "amount": "5000.00", "currency": "USD", "status": "submitted", ... }
  ]
}
```

Default page size is 10. Override with `?page_size=N` up to a maximum of
50.

### Verify a validation error

```bash
curl -X POST http://127.0.0.1:8000/api/v1/financing-requests/ \
  -H "Authorization: Token MERCHANT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"merchant":"MERCHANT_UUID","amount":"-100","currency":"USD","purpose":"Should fail"}'
```

Expected response: `400 Bad Request` in the consistent error envelope:

```json
{
  "error": {
    "code": "ValidationError",
    "message": "Amount must be greater than zero.",
    "details": {"amount": ["Amount must be greater than zero."]}
  }
}
```

---

## API Documentation

The API is documented via OpenAPI 3. Three views of the schema are
available:

- **Static schema file:** [`docs/openapi.yaml`](./docs/openapi.yaml) —
  versioned in this repository, readable without running the server.
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
├── common/                 # Shared infrastructure (permissions, exception handler, pagination, UserProfile)
├── docs/                   # ADR template, OpenAPI schema
├── .env.example            # Environment variable template
├── manage.py               # Django entry point
├── requirements.txt        # Python dependencies
├── README.md               # This file
└── ADR.md                  # The rationale behind the bounded-app structure
```

## Troubleshooting
 **`ConnectionRefusedError` when starting the Celery worker.** Redis is not running. Confirm with the ping check in the [Running the Async Worker](#running-the-async-worker) section. 

 **`OperationalError: table ... has no column named ...`.** Migrations have not been applied after a model change. Run `py manage.py makemigrations` and `py manage.py migrate`. 

 **Celery worker on Windows hangs or fails to pick up tasks.** The `--pool=solo` flag is mandatory on Windows. The default pool relies on `fork()`, which Windows does not support. 

 **`PermissionDenied: This endpoint is restricted to merchant accounts.`** The token in your `Authorization` header belongs to a user without the merchant role. Either use a different token or update the user's `UserProfile.role` through the Django admin.

 --- 
