# Bug Report

## Bug 1: Serializer Validation Bypassed on Financing POST

### Bug Summary

`FinancingListView.post()` in `financing/views.py` called `FinancingRequest.objects.create()`
directly with raw request data, completely skipping `FinancingRequestSerializer` and all its
validators. Invalid financial records — negative amounts, zero amounts, amounts above 1,000,000,
unrecognised currencies, and one-word purposes — were accepted and persisted with HTTP 201.

### Why It Matters

This is a financial ledger. A merchant could submit `amount=-50000` or `currency="FAKE"` and the
record would be stored as valid. Downstream systems — approval workflows, lender dashboards,
disbursement pipelines — would operate on corrupt data. In a live deployment, a negative-amount
financing request that passes validation and reaches a lender's approval queue could trigger an
erroneous disbursement or block a legitimate request that conflicts with it. The serializer's
rules existed precisely to prevent this; the view simply never invoked them.

### Root Cause

The view extracted fields with `data.get('amount', 0)` and passed them straight to the ORM.
`FinancingRequestSerializer` — which defines `validate_amount`, `validate_currency`, and
`validate_purpose` — was never instantiated in the POST path. The serializer existed and was
correct; the view bypassed it entirely.

**Broken code (`financing/views.py` before fix):**
```python
fr = FinancingRequest.objects.create(
    merchant=merchant,
    amount=data.get('amount', 0),
    currency=data.get('currency', 'USD'),
    purpose=data.get('purpose', ''),
)
```

**Fix applied:**
```python
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

`financing/tests.py` — `TestFinancingValidation` (5 tests):

| Test | Invalid input | Expected | Before fix | After fix |
|------|--------------|----------|------------|-----------|
| `test_negative_amount_rejected` | `amount=-500` | 400 | 201 | 400 |
| `test_zero_amount_rejected` | `amount=0` | 400 | 201 | 400 |
| `test_amount_over_ceiling_rejected` | `amount=1000001` | 400 | 201 | 400 |
| `test_invalid_currency_rejected` | `currency=FAKE` | 400 | 201 | 400 |
| `test_short_purpose_rejected` | `purpose="Too short"` | 400 | 201 | 400 |

```bash
python -m pytest financing/tests.py::TestFinancingValidation -v
```

### Residual Risk

- `payback_date` validation (must be a future date) is active through the serializer but has no dedicated API-level regression test. A past date returns 400 but this path is not exercised in the integration suite.
- The `merchant` field is resolved via a manual integer lookup before the serializer runs. Under concurrent load, if a `MerchantIndex` row is deleted between the lookup and `serializer.save()`, the ORM raises an `IntegrityError` rather than a clean 400 — the error surface at the API boundary is not fully sealed against this race.
- Decimal values with more than two decimal places (e.g. `"1000.555"`) are silently coerced by the database layer. The serializer does not explicitly reject excess precision, which could mask data-entry errors in high-value requests.

---

## Bug 2: Cross-Merchant Impersonation on Financing POST

### Bug Summary

`FinancingListView.post()` resolved the target merchant from the integer ID in the request body
but never verified that the authenticated user owns that merchant. Any user with the merchant
role could submit financing requests using a different merchant's ID.

### Why It Matters

In a live system this is direct financial fraud. Merchant A could create debt obligations on
behalf of Merchant B without their knowledge or consent. The `IsMerchant()` permission gate
only checks the user's *role* — it cannot know which merchant record the POST body is targeting,
so it cannot substitute for an ownership check in the view. Left unfixed, a merchant with
knowledge of a competitor's integer index ID could accumulate unauthorised debt against them.

### Root Cause

The RBAC permission class (`common/permissions.py`) is intentionally scoped to role only — it
is reused across endpoints and has no knowledge of the request body. The view was responsible
for checking `request.user.profile.merchant == merchant` before acting on the resolved
merchant, but that check was missing entirely.

**Fix applied (`financing/views.py`, after merchant lookup):**
```python
if (request.user.profile.merchant_id is not None and
        request.user.profile.merchant_id != merchant.pk):
    return Response(
        {'detail': 'You may only submit financing requests for your own merchant account.'},
        status=status.HTTP_403_FORBIDDEN,
    )
```

### Regression Evidence

`financing/tests.py` — `TestMerchantOwnership` (2 tests):

| Test | Scenario | Expected | Before fix | After fix |
|------|----------|----------|------------|-----------|
| `test_merchant_cannot_submit_for_another_merchant` | merchant_a POSTs with merchant_b's ID | 403 | 201 | 403 |
| `test_merchant_can_submit_for_own_merchant` | merchant_a POSTs with their own ID | 201 | 201 | 201 |

```bash
python -m pytest financing/tests.py::TestMerchantOwnership -v
```

### Residual Risk

- The check is conditional: if `profile.merchant` is `None`, the guard does not fire and the user can submit for any merchant. This is intentional for backward compatibility with F1-era setups that create merchant-role users without linking a specific merchant record. In production, a merchant user with no linked merchant is an incomplete account and should be blocked at provisioning time — not silently permitted at the API layer.
- There is no object-level permission check on the GET path. The queryset filter in `get_visible_indexes()` prevents cross-merchant data reads, but the filter relies on `profile.merchant` being correctly set — the same provisioning gap applies to the read path.

---

## Bug 3: Non-Atomic Dual Write Leaves Orphaned FinancingRequest

### Bug Summary

`FinancingListView.post()` created a `FinancingRequest` and a `FinancingIndex` in two
sequential ORM calls with no `transaction.atomic()` wrapper. If the second write failed,
the first was already committed — leaving a `FinancingRequest` row with no index entry,
invisible to the API but permanently in the database.

### Why It Matters

Every financing record in this system is a debt obligation. An orphaned record that cannot be
retrieved, reviewed, or approved creates a reconciliation gap. In a financial audit, a row that
exists in the database but cannot be accessed through the API is unexplained money — exactly
the kind of discrepancy that triggers compliance investigations and regulatory findings. In a
high-concurrency environment where database connections can drop mid-request, this failure mode
is not hypothetical.

### Root Cause

The two ORM calls were written as independent statements. Without `transaction.atomic()`,
Django's autocommit behaviour commits each operation the moment it succeeds. There is no
rollback mechanism unless a savepoint is explicitly opened.

**Before fix:**
```python
fr = serializer.save()                                     # committed immediately
idx = FinancingIndex.objects.create(financing_request=fr)  # if this fails, fr is stranded
```

**Fix applied:**
```python
with transaction.atomic():
    fr = serializer.save()
    idx = FinancingIndex.objects.create(financing_request=fr)
```

### Regression Evidence

`financing/tests.py` — `TestFinancingAtomicity` (1 test):

| Test | Scenario | Expected | Before fix | After fix |
|------|----------|----------|------------|-----------|
| `test_no_orphaned_request_when_index_creation_fails` | `FinancingIndex.create` raises `IntegrityError` | `FinancingRequest.objects.count() == 0` | count is 1 (orphan) | count is 0 |

```bash
python -m pytest financing/tests.py::TestFinancingAtomicity -v
```

### Residual Risk

- `MerchantCreateView` in `merchants/views.py` lines 61 and 70 uses two sequential `get_or_create` calls without `transaction.atomic()`. The risk is lower because `get_or_create` is idempotent, but a failure between the two calls still produces a `Merchant` row without a `MerchantIndex`, making it invisible to the API. This should be hardened in a follow-up.
- The `log_access()` call is intentionally placed inside the `transaction.atomic()` block. If the audit log write fails, the entire financing creation rolls back. This is the correct choice — a financing request without an audit trail should not be committed — but it means a transient `AccessLog` write failure surfaces as a 500 to the caller rather than a partial success.

---

## Bug 4: Financing Creation Never Written to Audit Log

### Bug Summary

`FinancingListView.post()` had no `log_access()` call. Every financing request creation
happened without any entry in `AccessLog`, leaving no record of who submitted what or when.
The GET handler on the same view correctly called `log_access()` — the omission was in POST only.

### Why It Matters

In a regulated financial system, creating a debt obligation is an auditable event. Without a
log entry, there is no way to answer "who submitted this request?" during a compliance review
or fraud investigation. The gap is asymmetric and dangerous: reads were audited, writes were
not. A merchant could submit and later deny a financing request with no system-level evidence
to the contrary.

### Root Cause

Two causes combined: (1) `AccessLog.Action` had no `CREATE_FINANCING` choice — the vocabulary
to describe the event did not exist. (2) The POST handler was written without a `log_access()`
call, so even after adding the constant the view had to be updated to emit the log.

**Fix Part A — `common/models.py`, added to `AccessLog.Action`:**
```python
CREATE_FINANCING = 'create_financing', 'Created a financing request'
```

**Fix Part B — `financing/views.py`, added inside the atomic block:**
```python
log_access(
    request,
    action=AccessLog.Action.CREATE_FINANCING,
    record_ids=[idx.id],
    resource_type='financing_request',
)
```

### Regression Evidence

`financing/tests.py` — `TestFinancingAuditLog` (2 tests):

| Test | What it checks | Before fix | After fix |
|------|---------------|------------|-----------|
| `test_financing_creation_is_audit_logged` | `AccessLog` count for `'create_financing'` == 1 | 0 (no entry) | 1 |
| `test_audit_log_records_correct_user` | log entry username matches authenticated user | entry is None | matches |

```bash
python -m pytest financing/tests.py::TestFinancingAuditLog -v
```

### Residual Risk

- Rejected POST attempts (validation errors, 403s) are not logged. A systematic attempt to probe the API with invalid data or to impersonate another merchant leaves no trace in `AccessLog`. In a production deployment under financial regulation, rejected requests — especially 403s — should be recorded as security events in a separate audit channel.
- `AccessLog` has no expiry or archival policy. As the system scales, the table grows unboundedly. A production deployment would require a retention policy (e.g. archive after 90 days), indexing on `created_at` and `user_id`, and a read path for compliance officers to query the log without direct database access.
