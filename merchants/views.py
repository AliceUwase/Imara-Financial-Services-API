"""Views for the merchants app.

Exposes merchant resources as a DRF ViewSet. R
"""

from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from common.permissions import IsMerchant

from .models import Merchant
from .serializers import MerchantSerializer


class MerchantViewSet(viewsets.ModelViewSet):
    """API endpoints for merchant registration and profile management."""

    queryset = Merchant.objects.all()
    serializer_class = MerchantSerializer
    lookup_field = 'id'

    def get_permissions(self):
        """Registration is open; everything else requires merchant auth."""
        if self.action == 'create':
            return [AllowAny()]
        return [IsMerchant()]