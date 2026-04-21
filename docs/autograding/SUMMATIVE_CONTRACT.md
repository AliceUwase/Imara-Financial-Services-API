# Summative Autograding Contract

The Summative branch hardens the existing Imara codebase for release readiness.

## Branch

- `summative/release-hardening`

## Required root artifacts

- `BUG_REPORT.md`
- `Dockerfile`
- `DEPLOYMENT.md`

## Required command behavior

The repository must support:

```bash
pip install -r requirements.txt
python manage.py migrate --noinput
python -m pytest -q
```

## Regression expectation

The hidden checks rerun key `F1` and `F2` objective checks. The Summative must not break previously working core behavior unless the release notes justify a change and preserve equivalent functionality.

## Student test suite expectation

`python -m pytest -q` must execute successfully.

This requirement is about your own maintained test suite, not the hidden tests.

## Deployment and readiness evidence

The hidden checks expect:

- a `Dockerfile`
- a `DEPLOYMENT.md` with explicit run or release guidance
- environment handling documented in the repository

The hidden checks may also look for readiness signals such as:

- `gunicorn`
- `uvicorn`
- `collectstatic`
- `ALLOWED_HOSTS`
- `DEBUG`

The deployment reasoning itself is graded manually.
