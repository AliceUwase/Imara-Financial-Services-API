"""Admin configuration for the financing app.
"""

from django.contrib import admin
from .models import FinancingRequest


@admin.register(FinancingRequest)
class FinancingRequestAdmin(admin.ModelAdmin):
    list_display = ('merchant', 'amount', 'currency', 'payback_date', 'status', 'created_at')
    list_filter = ('status', 'currency')
    search_fields = ('merchant__business_name', 'merchant__email')
    readonly_fields = ('id', 'created_at', 'updated_at')
    autocomplete_fields = ('merchant',)