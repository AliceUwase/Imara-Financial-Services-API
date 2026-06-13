"""Root URL configuration for the Imara project.


"""

from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from common.views import health
from merchants.views import ApiTokenLoginView, SessionLoginView



urlpatterns = [
    path('admin/', admin.site.urls),

    # API endpoints
    path('api/health/', health, name='health'),
    path('api/merchants/', include('merchants.urls')),
    path('api/financing/requests/', include('financing.urls')),
    path("api/auth/token/", ApiTokenLoginView.as_view(), name="api_token_login"),
    path("api-auth/login/", SessionLoginView.as_view(), name="api_session_login"),
    path("api-auth/", include("rest_framework.urls")),

    # API schema 
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path(
        'api/schema/swagger-ui/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='swagger-ui',
    ),
    path(
        'api/schema/redoc/',
        SpectacularRedocView.as_view(url_name='schema'),
        name='redoc',
    ),
]