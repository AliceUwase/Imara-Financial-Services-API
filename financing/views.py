"""Views for the financing app.

Merchant-facing CRUD on financing requests is gated by IsMerchant.
Lender-facing listing is gated by IsLender.Creation and updates dispatch an async alert via Celery so the API
response is not blocked by alert delivery.

The lender-facing list view uses cursor pagination tuned for
low-bandwidth contexts: small page size, opaque cursor.
"""

from django.db import transaction
from rest_framework import generics, viewsets

from common.pagination import FinancingRequestCursorPagination
from common.permissions import IsLender, IsMerchant

from .models import FinancingRequest
from .serializers import FinancingRequestSerializer
from .tasks import send_financing_alert


class FinancingRequestViewSet(viewsets.ModelViewSet):
    """Merchant-facing API for creating and managing financing requests."""

    queryset = FinancingRequest.objects.all()
    serializer_class = FinancingRequestSerializer
    lookup_field = 'id'
    permission_classes = [IsMerchant]

    def perform_create(self, serializer):
        """Save the request, then queue an alert after the transaction commits."""
        instance = serializer.save()
        transaction.on_commit(
            lambda: send_financing_alert.delay(str(instance.id), event='created')
        )

    def perform_update(self, serializer):
        """Save the update, then queue an alert after the transaction commits."""
        instance = serializer.save()
        transaction.on_commit(
            lambda: send_financing_alert.delay(str(instance.id), event='updated')
        )


class LenderFinancingRequestListView(generics.ListAPIView):
    """Lender-facing read-only list of submitted financing requests.

    Uses cursor pagination so lenders on unstable mobile data fetch
    small, predictable pages. 
    """

    serializer_class = FinancingRequestSerializer
    queryset = FinancingRequest.objects.filter(status='submitted')
    permission_classes = [IsLender]
    pagination_class = FinancingRequestCursorPagination