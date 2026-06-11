"""Shared models for the common app.

UserProfile extends Django's built-in User with a role field that
distinguishes merchants from lenders. This drives permission checks
across the API.
"""
from django.conf import settings
from django.db import models

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

    def __str__(self) -> str:
        return f'{self.user.username} ({self.role})'
    
    