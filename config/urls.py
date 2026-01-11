"""
URL Configuration for Auth Microservice.

API Endpoints:
- /api/v1/auth/ - Authentication endpoints
- /api/v1/accounts/ - User account management
- /api/v1/profiles/ - Profile management
- /api/v1/spa/ - Spa centers, services, and therapists
- /api/docs/ - API documentation
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)


# Dummy view for email confirmation (handled via our custom verification flow)
def email_confirm_redirect(request, key):
    """
    Placeholder for allauth email confirmation.
    Our app uses custom verification codes instead of email links.
    """
    return JsonResponse({
        "message": "Email verification is handled via verification codes.",
        "instruction": "Please use the /api/v1/auth/verify/confirm/ endpoint with your verification code."
    })


urlpatterns = [
    # Django Admin
    path("admin/", admin.site.urls),
    
    # Allauth URLs (required for dj-rest-auth compatibility)
    # This provides the account_confirm_email URL that allauth/dj-rest-auth expects
    path("accounts/", include("allauth.urls")),
    
    # API v1 Routes
    path("api/v1/auth/", include("accounts.urls.auth_urls")),
    path("api/v1/accounts/", include("accounts.urls.account_urls")),
    path("api/v1/profiles/", include("profiles.urls")),
    path("api/v1/spa/", include("spacenter.urls")),
    
    # API Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
