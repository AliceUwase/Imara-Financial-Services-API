"""URL routing for the financing app.

Hosts endpoints for financing request creation (merchant-facing) and
financing request listing (lender-facing). 
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    FinancingRequestViewSet,
    LenderFinancingRequestListView,
)

router = DefaultRouter()
router.register(
    r'financing-requests',
    FinancingRequestViewSet,
    basename='financing-request',
)

urlpatterns = router.urls + [
    path(
        'lender/financing-requests/',
        LenderFinancingRequestListView.as_view(),
        name='lender-financing-list',
    ),
]
