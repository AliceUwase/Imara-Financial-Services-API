"""Shared models for the common app.

UserProfile extends Django's built-in User with a role field that
distinguishes merchants from lenders. This drives permission checks
across the API.
"""
import uuid
from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    if created and not kwargs.get('raw', False):
        UserProfile.objects.get_or_create(user=instance)


class UserProfile(models.Model):
    """One-to-one extension of Django's User with role information."""

    class Role(models.TextChoices):
        MERCHANT = 'merchant', 'Merchant'
        LENDER = 'lender', 'Lender'
        COMPLIANCE = 'compliance', 'Compliance / Admin'
        SUPPORT = 'support', 'Support Staff'


    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.SUPPORT,
    )
    # Only set for merchant-role users: the merchant they may access.
    # Left null for lender/compliance/support, who aren't tied to one merchant.
    merchant = models.ForeignKey(
        'merchants.Merchant',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='user_profiles',
    )

class AccessLog(models.Model):

    class Action(models.TextChoices):
        LIST_FINANCING = 'list_financing', 'Listed financing requests'
        VIEW_FINANCING = 'view_financing', 'Viewed a financing request'
        EXPORT_FINANCING = 'export_financing', 'Exported financing data'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # The user who performed the access. SET_NULL so the log survives even if
    # the account is later deleted — audit records must outlive their subjects.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='access_logs',
    )

    # Snapshots taken at access time, so the entry stays readable and accurate
    # even if the user is later deleted or their role changes.
    username = models.CharField(max_length=150, blank=True, default='')
    role = models.CharField(max_length=20, blank=True, default='')

    action = models.CharField(max_length=30, choices=Action.choices)

    # The kind of record touched (e.g. 'financing_request').
    resource_type = models.CharField(max_length=50, blank=True, default='')

    # References to the records accessed  integer index ids only, never the record contents
    record_ids = models.JSONField(default=list, blank=True)

    # How many records were accessed 
    record_count = models.PositiveIntegerField(default=0)

    # Where the request came from.
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


    def __str__(self) -> str:
        return (
            f'{self.username or "unknown"} '
            f'{self.action} ({self.record_count}) '
            f'@ {self.created_at:%Y-%m-%d %H:%M}'
        )
    
    