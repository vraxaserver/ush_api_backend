"""
Booking URL Configuration.

API endpoints for bookings, service arrangements, and availability.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BookingViewSet,
    ProductOrderViewSet,
    UpcomingBookingsView,
    PastBookingsView,
    ServiceArrangementListView,
    ServiceAvailabilityView,
)

app_name = "bookings"

router = DefaultRouter()
router.register(r"orders", ProductOrderViewSet, basename="product-order")
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
    # Customer's upcoming bookings
    path(
        "upcoming-bookings/",
        UpcomingBookingsView.as_view(),
        name="upcoming-bookings",
    ),
    # Customer's past bookings
    path(
        "past-bookings/",
        PastBookingsView.as_view(),
        name="past-bookings",
    ),
    # Booking CRUD (router handles the rest)
    path("", include(router.urls)),
]
