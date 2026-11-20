"""Admin configuration for the merchants app
"""

from .models import Merchant
from django.contrib import admin

@admin.register(Merchant)
class MerchantAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'email', 'country', 'status', 'created_at')
    list_filter = ('status', 'country')
    search_fields = ('business_name', 'owner_name', 'email')
    readonly_fields = ('id', 'created_at', 'updated_at')
    