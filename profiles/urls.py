"""
URL Configuration for Profiles.

Profile management endpoints.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CustomerProfileView,
    SlideListView,
)

app_name = "profiles"

router = DefaultRouter()

urlpatterns = [
    # ViewSet routes
    path("", include(router.urls)),
    # Customer profile
    path("customer/me/", CustomerProfileView.as_view(), name="customer-profile"),
    # Public slideshow endpoint
    path("slides/", SlideListView.as_view(), name="slide-list"),
]
