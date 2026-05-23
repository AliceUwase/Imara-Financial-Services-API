"""Serializers for the merchants app

Translates Merchant instances to and from JSON, and enforces field-level 
and cross-field validation on incoming payloads. This includes checks for required fields, field formats (like email and phone),
"""

from rest_framework import serializers

from .models import Merchant


class MerchantSerializer(serializers.ModelSerializer):
    """Serializer for Merchant create, read, and update operations"""

    class Meta:
        model = Merchant
        fields = [
            'id',
            'business_name',
            'owner_name',
            'email',
            'phone',
            'country',
            'status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']

    def validate_business_name(self, value: str) -> str:
        """Reject empty or whitespace-only business names."""
        if not value.strip():
            raise serializers.ValidationError('Business name cannot be empty.')
        return value.strip()

    def validate_phone(self, value: str) -> str:
        """Basic phone-format check: digits, plus sign, spaces, dashes only."""
        allowed = set('+0123456789 -()')
        if not all(char in allowed for char in value):
            raise serializers.ValidationError(
                'Phone number contains invalid characters.'
            )
        if len(value.strip()) < 7:
            raise serializers.ValidationError(
                'Phone number is too short.'
            )
        return value.strip()