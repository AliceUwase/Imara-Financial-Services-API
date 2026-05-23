"""Views for the merchants app
"""

from rest_framework import viewsets

from .models import Merchant
from .serializers import MerchantSerializer
from django.shortcuts import render

class MerchantViewSet(viewsets.ModelViewSet):
    """API endpoints for merchant registration and profile management."""

    queryset = Merchant.objects.all()
    serializer_class = MerchantSerializer
    lookup_field = 'id'
    
