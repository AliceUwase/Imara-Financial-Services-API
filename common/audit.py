"""Helpers for writing privacy-safe access-log entries."""

from .models import AccessLog, UserProfile


# Pull the client's IP from the request, preferring the forwarded header
# (set by proxies/load balancers) and falling back to the direct address.
def get_client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        # The first entry is the original client; the rest are proxies.
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


# Read the requesting user's role, or '' if they have none.
# Kept local so this module doesn't depend on the permissions module.
def get_role(user):
    if not user.is_authenticated:
        return ''
    try:
        return user.profile.role
    except UserProfile.DoesNotExist:
        return ''



def log_access(request, action, record_ids, resource_type=''):
    user = request.user
    AccessLog.objects.create(
        user=user if user.is_authenticated else None, # preserve audit trail for anonymous requests
        username=getattr(user, 'username', ''),
        role=get_role(user),
        action=action,
        resource_type=resource_type,
        record_ids=list(record_ids),     # references only — never contents
        record_count=len(record_ids),
        ip_address=get_client_ip(request),
    )