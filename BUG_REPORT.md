# Bug Report

## Bug 1: Input Checks Were Being Skipped When Creating a Financing Request

### What Happened

When a merchant submitted a financing request through the API, the system was supposed to run a set of input checks (**serializer**) before saving anything to the database.  it inspects every piece of incoming data and rejects anything that does not meet the rules. The bug was that the serializer was never called. The system went straight to saving the data without checking it first.

### Why It Matters

Because the checks were skipped, a merchant could submit a financing request with an amount of `-50,000`, a currency code that does not exist, or a purpose field left completely blank, and the system would accept all of it and store it as a valid record. This is equivalent to a financial ledger that accepts any number typed into it, including invalide data. Downstream systems such as lender dashboards, approval workflows, and payment pipelines would then operate on corrupted data. In a real deployment, a negative amount that passes through to a lender's approval queue could trigger an incorrect payment or block a legitimate request sitting alongside it.

### Root Cause

The view  was pulling values directly out of the request with calls like `data.get('amount', 0)` and handing them straight to the database layer. The serializer, `FinancingRequestSerializer`, which defines validators for amount, currency, and purpose, existed and was correct. The view simply never used it.

**Code before the fix (financing/views.py):**
```python
fr = FinancingRequest.objects.create(
    merchant=merchant,
    amount=data.get('amount', 0),
    currency=data.get('currency', 'USD'),
    purpose=data.get('purpose', ''),
)
```

**Code after the fix:**
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

### Regression Tests

The tests below live in `financing/tests.py` under the class `TestFinancingValidation`. Each one sends a deliberately broken request and confirms the API now returns HTTP `400`  instead of HTTP `201` response. Before the fix, all five returned `201` and stored corrupt data.

1. `test_negative_amount_rejected` sends `amount = -500` and expects 400
2. `test_zero_amount_rejected` sends `amount = 0` and expects 400
3. `test_amount_over_ceiling_rejected` sends `amount = 1000001` and expects 400
4. `test_invalid_currency_rejected` sends `currency = FAKE` and expects 400
5. `test_short_purpose_rejected` sends a purpose of fewer than ten characters and expects 400

```bash
python -m pytest financing/tests.py::TestFinancingValidation -v
```

### Residual Risk

- The `payback_date` field  is validated by the serializer and correctly rejected if it is in the past, but there is no dedicated integration test for this path. A past date returns 400, but the check is not exercised in the automated test suite.

- The `merchant` field is resolved through a manual lookup before the serializer runs. Under high traffic, if the merchant record is deleted between the lookup step and the save step, the database raises an error rather than a  `400` response. The error boundary at the API level is not fully sealed against this timing issue.

- Decimal amounts with more than two decimal places (for example, `1000.555`) are  rounded by the database layer. The serializer does not explicitly reject excess precision, which could mask a data entry error on a high value request.


## Bug 2: Any Merchant Could Submit a Financing Request on Behalf of Any Other Merchant

### What Happened

The API had a permission gate `IsMerchant` that checked whether the logged in user had the merchant role. What it did not check was whether the merchant ID included in the request body actually belonged to that user. A merchant who knew a competitor's  ID could include it in their request and the system would accept it.

### Why It Matters

In a live system this is `financial fraud`. `Merchant A` could create debt obligations in the name of `Merchant B` without their knowledge or consent. The permission class is intentionally generic as it is reused across many endpoints and has no way of knowing what the request body contains, so it cannot substitute for a direct ownership check inside the view itself.

### Root Cause

The permission class `IsMerchant` in `common/permissions.py` only answers the question "does this user have the merchant role?" It does not answer "does this user own the merchant they are acting on?" The view was responsible for that second check and it was missing entirely.

**Fix applied in financing/views.py after the merchant lookup:**
```python
if (request.user.profile.merchant_id is not None and
        request.user.profile.merchant_id != merchant.pk):
    return Response(
        {'detail': 'You may only submit financing requests for your own merchant account.'},
        status=status.HTTP_403_FORBIDDEN,
    )
```

### Regression Tests

The tests below live in `financing/tests.py` under `TestMerchantOwnership`.

1. `test_merchant_cannot_submit_for_another_merchant` logs in as merchant A, sends a request targeting merchant B's ID, and expects HTTP 403 (forbidden)
2. `test_merchant_can_submit_for_own_merchant` logs in as merchant A, sends a request targeting merchant A's own ID, and expects HTTP 201 (created)

Before the fix, both tests returned 201 regardless of which merchant ID was in the request.

```bash
python -m pytest financing/tests.py::TestMerchantOwnership -v
```

### Residual Risk

- The ownership check only fires when `profile.merchant` is set. If a user has the merchant role but no linked merchant record (an incomplete account), the guard does not fire and they can submit for any merchant. This is an acceptable edge case for this MVP but should be blocked at account provisioning time in a production deployment.

- The read path (GET requests) relies on a queryset filter in `get_visible_indexes()` rather than this ownership check, so the read path has its own guard. Both guards depend on `profile.merchant` being correctly set at the time the account is created.


## Bug 3: A Partial Write Could Leave a Financing Request Stranded in the Database

### What Happened

- Creating a financing request involved two sequential database writes: first saving the `FinancingRequest` record, then creating a `FinancingIndex` entry that acts as a numeric pointer to it. These two writes were not wrapped in a `transaction.atomic()` block. A transaction is an all or nothing rule: if anything inside it fails, everything is rolled back as if nothing happened. Without it, if the second write failed, the first was already permanently committed.

### Why It Matters

Every financing record in this system represents a debt obligation. A `FinancingRequest` row that exists in the database but has no corresponding `FinancingIndex` entry cannot be accessed through the API. It is permanently isolated in a way: invisible to merchants, lenders, and compliance officers, but still occupying space and potentially conflicting with other records. In a financial audit, an unexplained row in the database is a reconciliation gap. In a high traffic environment where database connections can drop mid request, this failure mode is not hypothetical.

### Root Cause

The two ORM  calls were written as plain sequential statements. Without an explicit transaction, Django commits each write the moment it succeeds. There is no automatic rollback if the next statement fails.

**Before fix:**
```python
fr = serializer.save()
idx = FinancingIndex.objects.create(financing_request=fr)
```

**After fix:**
```python
with transaction.atomic():
    fr = serializer.save()
    idx = FinancingIndex.objects.create(financing_request=fr)
```

### Regression Test

The test lives in `financing/tests.py` under `TestFinancingAtomicity`.

`test_no_orphaned_request_when_index_creation_fails` forces the second write to fail by replacing `FinancingIndex.objects.create` with a simulated error. It then checks that `FinancingRequest.objects.count()` is zero, proving the first write was rolled back. Before the fix, the count was one (an orphaned record had been committed and left behind).

```bash
python -m pytest financing/tests.py::TestFinancingAtomicity -v
```

### Residual Risk

- The `MerchantCreateView` in `merchants/views.py` makes two sequential `get_or_create` calls without wrapping them in `transaction.atomic()`. The risk there is lower because `get_or_create` is idempotent, but a failure between the two calls can still leave a `Merchant` row without a `MerchantIndex`, making it invisible to the API. This could be addressed in a follow up.

- The `log_access()` call sits inside the `transaction.atomic()` block. If the audit log write fails, the entire financing creation rolls back. This is the correct choice, as a financing request without an audit trail should not be committed but it means a transient write failure on the audit log surfaces as an HTTP 500 error to the caller rather than a partial success.


## Bug 4: Financing Request Creation Was Never Recorded in the Audit Log

### What Happened

The audit log is a compliance record that tracks who accessed or changed what data and when. The GET handler wrote an entry to the audit log every time it ran. The POST handler wrote nothing. Every financing request creation happened in silence from a compliance perspective.

### Why It Matters

In a regulated financial system, creating a debt obligation should be an auditable event. Without a log entry there is no way to answer "who submitted this request?" during a compliance review or fraud investigation. The gap was fishy: reads were audited, writes were not. A merchant could submit a financing request and later deny having done so with no system level evidence to the contrary. 

### Root Cause

Two problems combined. First, the `AccessLog.Action` choices in `common/models.py` had no `CREATE_FINANCING` constant, meaning the vocabulary to describe the event did not exist in the system. Second, even after adding that constant, the POST handler had no `log_access()` call to emit the record.

**Fix Part A — common/models.py, added to AccessLog.Action:**
```python
CREATE_FINANCING = 'create_financing', 'Created a financing request'
```

**Fix Part B — financing/views.py, added inside the atomic block after the index is created:**
```python
log_access(
    request,
    action=AccessLog.Action.CREATE_FINANCING,
    record_ids=[idx.id],
    resource_type='financing_request',
)
```

### Regression Tests

The tests live in `financing/tests.py` under `TestFinancingAuditLog`.

1. `test_financing_creation_is_audit_logged` submits a valid financing request and counts `AccessLog` entries with action `create_financing`. Before the fix the count was zero. After the fix it is one.
2. `test_audit_log_records_correct_user` checks that the log entry captures the username of the authenticated user who made the request. Before the fix there was no entry to check.

```bash
python -m pytest financing/tests.py::TestFinancingAuditLog -v
```

### Residual Risk

- Rejected POST attempts such as validation errors (HTTP 400) and ownership violations (HTTP 403) are not logged. A systematic attempt to probe the API with invalid data or to impersonate another merchant leaves no trace in `AccessLog`. In a production deployment under financial regulation, rejected requests, especially 403 responses, should be recorded as security events in a separate audit channel.

- `AccessLog` has no expiry or archival policy. As the system scales, the table grows without limit. A production deployment would require a data retention policy (for example, archive entries older than ninety days), database indexes on `created_at` and `user_id`, and a read path that allows compliance personnel to query the log without needing direct database access.

