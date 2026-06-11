"""Admin configuration for the common app."""


from django.contrib import admin
from .models import UserProfile
from .models import AccessLog   


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__email')
    autocomplete_fields = ('user',)

@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    # List columns — references only, no sensitive contents on display.
    list_display = (
        'created_at', 'username', 'role',
        'action', 'record_count', 'ip_address',
    )

    # Let compliance slice the trail quickly by action, role, or date
    list_filter = ('action', 'role', 'created_at')
    search_fields = ('username', 'ip_address')
    ordering = ('-created_at',)

    # Every field is view-only. an audit record is a statement of fact and
    # must not be rewritten after it is created.
    readonly_fields = (
        'id', 'user', 'username', 'role', 'action',
        'resource_type', 'record_ids', 'record_count',
        'ip_address', 'created_at',
    )

    # Entries are written only by the application not manually modified
    def has_add_permission(self, request):
        return False

    # No editing — the record is immutable after creation.
    def has_change_permission(self, request, obj=None):
        return False

    # No deleting — the trail is append-only. If deletion was allowed, a user could cover their tracks by deleting entries.
    def has_delete_permission(self, request, obj=None):
        return False

# Register your models here.
