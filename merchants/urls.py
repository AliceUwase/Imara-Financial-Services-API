"""URL routing for the merchants app.

Endpoints defined here will be mounted under /api/v1/ by the project's
root URL configuration. 
"""
from rest_framework.routers import DefaultRouter

from .views import MerchantViewSet

router = DefaultRouter()
router.register(r'merchants', MerchantViewSet, basename='merchant')

urlpatterns = router.urls
