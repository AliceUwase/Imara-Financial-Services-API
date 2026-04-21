# F1 Autograding Contract

`F1` establishes the minimum API and repository contract for the first stage of the Imara Financial Services case.

## Branch

- `f1/mvp`

## Required root artifacts

- `ADR.md`
- `README.md`
- either `schema.yml` or `schema.yaml`

## Required endpoints

Your project must expose these paths exactly:

- `GET /api/health/`
- `POST /api/merchants/`
- `GET /api/merchants/<id>/`
- `POST /api/financing/requests/`
- `GET /api/financing/requests/`

## Health response

`GET /api/health/` must return `200`.

Any JSON body is acceptable as long as it is valid JSON.

## Merchant create contract

The hidden tests submit:

```json
{
  "name": "Imena Grocers",
  "registration_number": "IMARA-M-001",
  "contact_email": "ops@imenagrocers.test"
}
```

`POST /api/merchants/` must:

- return `201`
- return JSON containing an integer-like `id`

## Merchant detail contract

After merchant creation, `GET /api/merchants/<id>/` must:

- return `200`
- return JSON containing the same `id`

## Financing request create contract

The hidden tests submit:

```json
{
  "merchant": 1,
  "amount": "1200.00",
  "currency": "RWF",
  "term_days": 30,
  "purpose": "Inventory restock"
}
```

`POST /api/financing/requests/` must:

- return `201`
- return JSON containing an integer-like `id`

## Financing list contract

`GET /api/financing/requests/` must:

- return `200`
- return valid JSON
- show a pagination-minded list structure

Accepted list structures:

- a DRF-style pagination envelope containing `results`
- a top-level JSON list

If you use a top-level list, your README must explicitly explain the pagination or performance decision you chose instead.

## Async evidence contract

The hidden checks expect evidence that asynchronous work was designed intentionally.

At least one of the following must be visible in the codebase:

- a Python file containing `shared_task`
- a Python file containing `.delay(`
- a Python file containing `.apply_async(`
- a project-level `celery.py`

Your README must also describe how the async worker is started in your implementation.

## Performance evidence contract

The hidden checks expect evidence of at least one performance-minded design choice.

Accepted evidence includes any of:

- paginated list responses
- explicit cache configuration or cache usage
- documented query optimization in code comments or README

The hidden checks only score the objective evidence. Your rationale belongs in `ADR.md`.
