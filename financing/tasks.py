"""Celery tasks for the financing app.

The send_financing_alert task is the asynchronous handler invoked
when a financing request is created or updated. It records every
invocation as an AlertAttempt row, so audit evidence exists regardless
of whether the underlying send succeeds.
"""

import logging
from typing import Any

from celery import shared_task

from .models import AlertAttempt, FinancingRequest

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def send_financing_alert(self, financing_request_id: str, event: str = 'created') -> dict[str, Any]:
    """Send an alert about a financing request and record the attempt.

    For the MVP this only logs the event and writes an AlertAttempt row.
    A real implementation would dispatch to email, SMS, or webhook
    channels here.

    Args:
        financing_request_id: UUID of the FinancingRequest to alert about.
        event: What happened to the request ('created' or 'updated').

    Returns:
        A dict summarising the outcome, surfaced in Celery's result store.
    """
    attempt = AlertAttempt.objects.create(
        financing_request_id=financing_request_id,
        channel=AlertAttempt.Channel.LOG,
        status=AlertAttempt.Status.QUEUED,
    )

    try:
        financing_request = FinancingRequest.objects.get(id=financing_request_id)
    except FinancingRequest.DoesNotExist:
        attempt.status = AlertAttempt.Status.FAILED
        attempt.error_message = f'FinancingRequest {financing_request_id} not found.'
        attempt.save(update_fields=['status', 'error_message'])
        logger.warning(
            'Alert task could not find financing request %s', financing_request_id
        )
        return {'status': 'failed', 'reason': 'not_found'}

    try:
        # MVP: log the alert. Production would send email / SMS / webhook here.
        logger.info(
            'ALERT [%s]: Financing request %s for %s %s by %s',
            event,
            financing_request.id,
            financing_request.amount,
            financing_request.currency,
            financing_request.merchant.business_name,
        )
        attempt.status = AlertAttempt.Status.SUCCEEDED
        attempt.save(update_fields=['status'])
        return {'status': 'succeeded', 'event': event, 'request_id': str(financing_request.id)}

    except Exception as exc:
        attempt.status = AlertAttempt.Status.FAILED
        attempt.error_message = str(exc)
        attempt.save(update_fields=['status', 'error_message'])
        logger.exception('Alert task failed for request %s', financing_request_id)
        # Retry with exponential backoff
        raise self.retry(exc=exc)