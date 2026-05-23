"""Serializers for the financing app

Translates FinancingRequest instances to and from JSON.
"""

from datetime import date

from rest_framework import serializers

from .models import FinancingRequest


class FinancingRequestSerializer(serializers.ModelSerializer):
    """Serializer for FinancingRequest create, read, and update operations"""

    class Meta:
        model = FinancingRequest
        fields = [
            'id',
            'merchant',
            'amount',
            'currency',
            'purpose',
            'payback_date',
            'status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']

    def validate_amount(self, value):
        """Reject non-positive amounts and amounts above the MVP ceiling."""
        if value <= 0:
            raise serializers.ValidationError('Amount must be greater than zero.')
        if value > 1_000_000:
            raise serializers.ValidationError(
                'Amount exceeds the maximum permitted for this MVP (1,000,000).'
            )
        return value

    def validate_currency(self, value: str) -> str:
        """Restrict currency to a known set for the MVP."""
        allowed = {'USD', 'EUR', 'RWF', 'KES', 'UGX'}
        if value.upper() not in allowed:
            raise serializers.ValidationError(
                f'Currency must be one of: {", ".join(sorted(allowed))}.'
            )
        return value.upper()

    def validate_purpose(self, value: str) -> str:
        """Require a meaningful purpose, not just a few characters."""
        cleaned = value.strip()
        if len(cleaned) < 10:
            raise serializers.ValidationError(
                'Purpose must be at least 10 characters.'
            )
        return cleaned

    def validate_payback_date(self, value):
        """If a payback date is provided, it must be in the future."""
        if value is not None and value <= date.today():
            raise serializers.ValidationError(
                'Payback date must be in the future.'
            )
        return value