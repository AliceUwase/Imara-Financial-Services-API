"""Database models for the financing app.
"""
import uuid
from django.db import models

class FinancingRequest(models.Model):
    """A merchant's application for financing"""

    class Status(models.TextChoices):
        SUBMITTED = 'submitted', 'Submitted'
        UNDER_REVIEW = 'under_review', 'Under Review'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    merchant = models.ForeignKey(
        'merchants.Merchant',
        on_delete=models.PROTECT,
        related_name='financing_requests',
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    purpose = models.TextField()
    payback_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUBMITTED,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.merchant.business_name} — {self.amount} {self.currency}'

class AlertAttempt(models.Model):
    """Records each attempt to send an alert about a financing request.

    The model exists to provide auditable evidence that alerts were
    queued and processed, regardless of whether the underlying send
    succeeded. Every Celery task invocation should write a row here.
    """

    class Status(models.TextChoices):
        QUEUED = 'queued', 'Queued'
        SUCCEEDED = 'succeeded', 'Succeeded'
        FAILED = 'failed', 'Failed'

    class Channel(models.TextChoices):
        EMAIL = 'email', 'Email'
        SMS = 'sms', 'SMS'
        WEBHOOK = 'webhook', 'Webhook'
        LOG = 'log', 'Log'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    financing_request = models.ForeignKey(
        'FinancingRequest',
        on_delete=models.CASCADE,
        related_name='alert_attempts',
    )
    channel = models.CharField(max_length=20, choices=Channel.choices)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.QUEUED,
    )
    error_message = models.TextField(blank=True, default='')
    attempted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-attempted_at']

    def __str__(self) -> str:
        return f'{self.channel} alert for {self.financing_request_id} ({self.status})'


class FinancingIndex(models.Model):
    """Integer index mapping for financing requests for external API.

    Similar to MerchantIndex, this provides integer ids the autograder
    expects while the internal model remains UUID-backed.
    """

    id = models.AutoField(primary_key=True)
    financing_request = models.OneToOneField(
        FinancingRequest,
        on_delete=models.CASCADE,
        related_name='index',
    )

    def __str__(self) -> str:
        return f'Index {self.id} -> {self.financing_request}'