"""Views for the financing app

Provides two separate API surfaces:

- FinancingRequestViewSet: merchant-facing CRUD on financing requests.
- LenderFinancingRequestListView: lender-facing read-only list of
  submitted requests.
"""

from django.shortcuts import render

from rest_framework import generics, viewsets

from .models import FinancingRequest
from .serializers import FinancingRequestSerializer


class FinancingRequestViewSet(viewsets.ModelViewSet):
    """Merchant-facing API for creating and managing financing requests"""

    queryset = FinancingRequest.objects.all()
    serializer_class = FinancingRequestSerializer
    lookup_field = 'id'


class LenderFinancingRequestListView(generics.ListAPIView):
    """Lender-facing read-only list of submitted financing requests"""

    serializer_class = FinancingRequestSerializer
    queryset = FinancingRequest.objects.filter(status='submitted')