"""Views for the financing app.

Merchant-facing CRUD on financing requests is gated by IsMerchant.
Lender-facing listing is gated by IsLender. The audience split keeps
each role on its own URL surface with its own permission contract.
"""

from rest_framework import generics, viewsets

from common.permissions import IsLender, IsMerchant

from .models import FinancingRequest
from .serializers import FinancingRequestSerializer


class FinancingRequestViewSet(viewsets.ModelViewSet):
    """Merchant-facing API for creating and managing financing requests."""

    queryset = FinancingRequest.objects.all()
    serializer_class = FinancingRequestSerializer
    lookup_field = 'id'
    permission_classes = [IsMerchant]


class LenderFinancingRequestListView(generics.ListAPIView):
    """Lender-facing read-only list of submitted financing requests."""

    serializer_class = FinancingRequestSerializer
    queryset = FinancingRequest.objects.filter(status='submitted')
    permission_classes = [IsLender]