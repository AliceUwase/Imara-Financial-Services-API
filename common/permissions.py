"""Permission classes for the Imara API.

Provides role-based gates that views attach to. Both classes require
the user to be authenticated and to have an associated UserProfile.
Anonymous users and users without profiles are rejected.
"""

from rest_framework.permissions import BasePermission

from .models import UserProfile


class IsMerchant(BasePermission):
    """Permits access only to authenticated users with the merchant role."""

    message = 'This endpoint is restricted to merchant accounts.'

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user.is_authenticated:
            return False
        try:
            return user.profile.role == UserProfile.Role.MERCHANT
        except UserProfile.DoesNotExist:
            return False


class IsLender(BasePermission):
    """Permits access only to authenticated users with the lender role."""

    message = 'This endpoint is restricted to lender accounts.'

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user.is_authenticated:
            return False
        try:
            return user.profile.role == UserProfile.Role.LENDER
        except UserProfile.DoesNotExist:
            return False

class IsCompliance(BasePermission):
    """Permits access only to authenticated users with the compliance role."""

    message = 'This endpoint is restricted to compliance accounts.'

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user.is_authenticated:
            return False
        try:
            return user.profile.role == UserProfile.Role.COMPLIANCE
        except UserProfile.DoesNotExist:
            return False


class IsSupport(BasePermission):
    """Permits access only to authenticated users with the support role."""

    message = 'This endpoint is restricted to support accounts.'

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user.is_authenticated:
            return False
        try:
            return user.profile.role == UserProfile.Role.SUPPORT
        except UserProfile.DoesNotExist:
            return False