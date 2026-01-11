"""
URL Configuration for Profiles.

Profile management endpoints.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CustomerProfileView,
    EmployeeProfileAdminViewSet,
    EmployeeProfileView,
    EmployeeScheduleViewSet,
    TherapistDetailView,
    TherapistListView,
)

app_name = "profiles"

# Router for ViewSets
router = DefaultRouter()
router.register(
    r"admin/employees",
    EmployeeProfileAdminViewSet,
    basename="admin-employee-profile",
)
router.register(
    r"employee/me/schedules",
    EmployeeScheduleViewSet,
    basename="employee-schedule",
)

urlpatterns = [
    # ViewSet routes
    path("", include(router.urls)),
    # Customer profile
    path("customer/me/", CustomerProfileView.as_view(), name="customer-profile"),
    # Employee profile
    path("employee/me/", EmployeeProfileView.as_view(), name="employee-profile"),
    # Public therapist endpoints
    path("therapists/", TherapistListView.as_view(), name="therapist-list"),
    path(
        "therapists/<uuid:id>/",
        TherapistDetailView.as_view(),
        name="therapist-detail",
    ),
]
