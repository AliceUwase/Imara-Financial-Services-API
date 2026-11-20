"""Contract-facing merchant URLs.

This module exists so the root URL config can mount the merchant API
under /api/merchants/ without disturbing the existing app URLs.
"""

from django.urls import path

from .views import MerchantViewSet


merchant_view = MerchantViewSet.as_view({
    'get': 'list',
    'post': 'create',
})
merchant_detail_view = MerchantViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy',
})

urlpatterns = [
    path('', merchant_view, name='merchant-list-create'),
    path('<uuid:id>/', merchant_detail_view, name='merchant-detail'),
]