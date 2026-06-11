"""URL routing for the merchants app.

"""

from django.urls import path
from merchants.views import ApiTokenLoginView
    
from .views import MerchantCreateView, MerchantDetailView

urlpatterns = [
    path('', MerchantCreateView.as_view(), name='merchant-create'),
    path('<int:pk>/', MerchantDetailView.as_view(), name='merchant-detail'),
    path('api/auth/token/', ApiTokenLoginView.as_view(), name='api_token_login'),
]
