"""
Booking URL Configuration.

API endpoints for bookings, service arrangements, and availability.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BookingViewSet,
    CustomerBookingsView,
    ServiceArrangementListView,
    ServiceAvailabilityView,
)

app_name = "bookings"

router = DefaultRouter()
router.register(r"", BookingViewSet, basename="booking")

urlpatterns = [
    # Service arrangements for a service
    path(
        "services/<uuid:service_id>/arrangements/",
        ServiceArrangementListView.as_view(),
        name="service-arrangements",
    ),
    # Availability for a service
    path(
        "services/<uuid:service_id>/availability/",
        ServiceAvailabilityView.as_view(),
        name="service-availability",
    ),
    # Customer's bookings
    path(
        "my-bookings/",
        CustomerBookingsView.as_view(),
        name="my-bookings",
    ),
    # Booking CRUD (router handles the rest)
    path("", include(router.urls)),
]
