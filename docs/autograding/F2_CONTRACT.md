# F2 Autograding Contract

`F2` retrofits the `F1` codebase with authentication, authorization, and compliance-minded controls.

## Branch

- `f2/compliance-retrofit`

## Required root artifacts

- `DECISION_LOG.md`

## Required authentication endpoints

Your project must expose these paths exactly:

- `POST /api/auth/session-login/`
- `POST /api/auth/token/`

The hidden checks submit:

```json
{
  "username": "grader_user",
  "password": "GraderPass123!"
}
```

Accepted token response shapes:

- a JSON object containing `token`
- a JSON object containing `access`

## Protected API expectation

The `F1` financing list endpoint must no longer be open to anonymous access.

`GET /api/financing/requests/` must return:

- `401` or `403` when the requester is unauthenticated

## RBAC expectation

The hidden checks create:

- one regular user
- one staff user

The financing list endpoint must enforce a real boundary:

- staff or lender-like user: `200`
- regular user: `403`

## Continuity expectation

The retrofit must preserve the original project rather than restarting from scratch.

The hidden checks look for:

- a working `manage.py`
- the original `F1` API paths still present
- existing repository continuity on the same branch model

## Privacy or auditability expectation

The hidden checks require at least one objective signal that privacy or auditability was added.

Accepted evidence includes:

- a Python file containing `audit`
- a Python file containing `AuditLog`
- a Python file containing `created_by`
- a Python file containing `updated_by`
- a Python file containing `request.user`

The hidden checks only confirm objective evidence exists. Your reasoning belongs in `DECISION_LOG.md`.
