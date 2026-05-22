"""URL routing for the financing app.

Hosts endpoints for financing request creation (merchant-facing) and
financing request listing (lender-facing). Both are mounted under
/api/v1/ by the project's root URL configuration.
"""

from rest_framework.routers import DefaultRouter

router = DefaultRouter()
# router.register(r'financing-requests', FinancingRequestViewSet, basename='financing-request')

urlpatterns = router.urls
