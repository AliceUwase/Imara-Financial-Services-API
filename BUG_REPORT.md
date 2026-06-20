# Bug Report 

## Bug 1: Serializer Validation Bypassed on Financing POST

### Bug Summary

`FinancingListView.post()` in `financing/views.py` called `FinancingRequest.objects.create()`
directly with raw request data, and it was completely  skipping `FinancingRequestSerializer` and all its
validators. Invalid financial records like negative amounts, zero amounts, amounts above 1,000,000,
unknown currencies, and invalid purposes  were accepted and persisted with HTTP 201.

### Why It Matters

As a fintech project, A merchant could submit invalid data like `amount=-50000` or `currency="FAKE"` and the
record would be still be stored as valid. Downstream systems (approval workflows, lender dashboards, audits)
would run on corrupt data. In a real-world project, this is a  financial integrity failure that needs to be addressed.

### Root Cause

The view was written to manually extract fields with `data.get('amount', 0)` and pass them
straight to the DB. `FinancingRequestSerializer` defines `validate_amount`,
`validate_currency`, and `validate_purpose`  and was never instantiated in the POST path.
The serializer existed and was correct, but the view  never used it.


**Broken code (`financing/views.py:74-79` before fix):**
```python
fr = FinancingRequest.objects.create(
    merchant=merchant,
    amount=data.get('amount', 0),
    currency=data.get('currency', 'USD'),
    purpose=data.get('purpose', ''),
)
```
***fix applied:***
```
serializer = FinancingRequestSerializer(data={
    'merchant': merchant.pk,
    'amount': data.get('amount'),
    'currency': data.get('currency', 'USD'),
    'purpose': data.get('purpose', ''),
    'payback_date': data.get('payback_date'),
})
serializer.is_valid(raise_exception=True)
fr = serializer.save()
```
### Regression Evidence

financing/tests.py — TestFinancingValidation (5 tests):

| Test | Invalid input | Expected | Before fix | After fix |
|---|---|---:|---:|---:|
| `test_negative_amount_rejected` | `amount=-500` | 400 | 201 | 400 |
| `test_zero_amount_rejected` | `amount=0` | 400 | 201 | 400 |
| `test_amount_over_ceiling_rejected` | `amount=1000001` | 400 | 201 | 400 |
| `test_invalid_currency_rejected` | `currency=FAKE` | 400 | 201 | 400 |
| `test_short_purpose_rejected` | `purpose="Too short"` | 400 | 201 | 400 |
Run with:
```
python manage.py test financing.tests.TestFinancingValidation --verbosity=2
```

### Residual Risk

- The `merchant` field in the POST body is still an integer index ID resolved manually in the view, not with the serializer. A future refactor will unify this into a custom serializer field.


## Bug 2: Cross-Merchant Impersonation on Financing POST

### Bug Summary
`FinancingListView.post()` resolved the target merchant from the integer ID in the request body
but never verified that the authenticated user actually owns that merchant. Any user with the
merchant role could submit financing requests using a different merchant's ID.

### Why It Matters
In a real-world system, this is a financial fraud. Merchant A could create debt obligations on
behalf of Merchant B without their knowledge. The `IsMerchant()` permission gate only checks
the user's *role* , so, it cannot know which merchant record the POST body is targeting, so it
cannot substitute for an ownership check in the view.

### Root Cause
The RBAC permission class (`common/permissions.py`) is intentionally scoped to role only. it
is reused across endpoints and has no knowledge of the request body. The view was responsible
for checking `request.user.profile.merchant == merchant` before acting on the resolved
merchant, but that check was missing entirely.

**Fix applied (`financing/views.py`, after merchant lookup):**
```python
if request.user.profile.merchant_id != merchant.pk:
    return Response(
        {'detail': 'You may only submit financing requests for your own merchant account.'},
        status=status.HTTP_403_FORBIDDEN,
    )
```    

#### Regression Evidence
`financing/tests.py` — TestMerchantOwnership (2 tests):

| Test | Scenario | Expected | Before fix | After fix |
|---|---|---:|---:|---:|
| `test_merchant_cannot_submit_for_another_merchant` | merchant_a POSTs with merchant_b's ID | 403 | 201 | 403 |
| `test_merchant_can_submit_for_own_merchant` | merchant_a POSTs with their own ID | 201 | 201 | 201 |

run with:
```python
python manage.py test financing.tests.TestMerchantOwnership --verbosity=2
```

#### Residual Risk: 

- The ownership check is only enforced when the user profile has a merchant
explicitly linked (profile.merchant is not None). A merchant-role user without
a linked merchant record can still submit for any merchant.


## Bug 3 — Non-Atomic Dual Write Leaves Orphaned FinancingRequest

### Bug Summary
`FinancingListView.post()` created a `FinancingRequest` and a `FinancingIndex` in two
sequential ORM calls with no `transaction.atomic()` wrapper. If the second write failed,
the first was already committed which  left a `FinancingRequest` row with no index entry,
invisible to the API but permanently in the database.

### Why It Matters
Every financing record in this system is a debt obligation. An orphaned record that cannot
be retrieved, reviewed, or approved creates a reconciliation gap. In a financial audit, a
row that exists in the database but cannot be accessed through the API is unexplained money;
exactly the kind of discrepancy that triggers compliance investigations.

### Root Cause
The two ORM calls were written as independent statements. Without `transaction.atomic()`, 
Django's autocommit behaviour commits each operation the moment it succeeds. There is no 
rollback mechanism unless a savepoint is explicitly opened.

**Before fix (`financing/views.py`):**
```python
fr = serializer.save()                              # committed immediately
idx = FinancingIndex.objects.create(financing_request=fr)  # if this fails, fr is stranded
```

***Fix applied:***

```
from django.db import transaction

with transaction.atomic():
    fr = serializer.save()
    idx = FinancingIndex.objects.create(financing_request=fr)
```
#### Regression Evidence
| Test file | Test class | Tests | Scenario | Expected | Before fix | After fix |
|---|---|---:|---|---|---|---|
| `financing/tests.py` | `TestFinancingAtomicity` | 1 | `FinancingIndex.create` raises `IntegrityError` | `FinancingRequest.objects.count() == 0` | count is 1 (orphan) | count is 0 |

run with:
```
python manage.py test financing.tests.TestFinancingAtomicity --verbosity=2
```

### Residual Risk
The `MerchantIndex` creation in `MerchantCreateView` (merchants/views.py:70) has the same pattern (get_or_create then get_or_create) but uses idempotent calls, so the risk is lower. 

## Bug 4: Financing Creation Never Written to Audit Log

### Bug Summary
`FinancingListView.post()` had no `log_access()` call. Every financing request creation
happened without any entry in `AccessLog`, leaving no record of who submitted what or when.
The GET handler on the same view correctly called `log_access()`, the omission was in POST only.

### Why It Matters
In a regulated financial system, creating a debt obligation is an auditable event. Without a
log entry, there is no way to answer "who submitted this request?" during a compliance review
or fraud investigation. The gap is asymmetric: reads were audited, writes were not.

### Root Cause
Two causes combined: (1) `AccessLog.Action` had no `CREATE_FINANCING` choice, the vocabulary
to describe the event didn't exist. (2) The POST handler was written without a `log_access()`
call, so even after adding the constant, the view had to be updated to emit the log.

**Fix Part A — `common/models.py`, added to `AccessLog.Action`:**
```python
CREATE_FINANCING = 'create_financing', 'Created a financing request'

**Fix Part B — `financing/views.py`, added after the atomic block:**
```python
log_access(
    request,
    action=AccessLog.Action.CREATE_FINANCING,
    record_ids=[idx.id],
    resource_type='financing_request',
)
```

### Regression Evidence
`financing/tests.py` — TestFinancingAuditLog (2 tests):

| Test | What it checks | Before fix | After fix |
|---|---|---|---|
| `test_financing_creation_is_audit_logged` | AccessLog count for `'create_financing'` == 1 | 0 (no entry) | 1 |
| `test_audit_log_records_correct_user` | log entry username matches authenticated user | entry is None | matches |

run with:
```
python manage.py test financing.tests.TestFinancingAuditLog --verbosity=2
```

### Residual Risk
`AccessLog.Action` now has `CREATE_FINANCING` but the Django admin filter for `AccessLog` will show it automatically, no admin change needed.
Failed POST attempts (e.g. validation errors, 403s) are not logged. Only successful creations are audited. 

