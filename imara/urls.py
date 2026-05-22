"""Root URL configuration for the Imara project.

API endpoints are mounted under /api/v1/. Each domain app contributes
its own URL patterns through include(). The schema endpoints publish
the OpenAPI document and a Swagger UI for interactive exploration.
"""

from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # API v1 — domain endpoints
    path('api/v1/', include('merchants.urls')),
    path('api/v1/', include('financing.urls')),
    path('api/v1/', include('common.urls')),

    # API schema and interactive docs
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