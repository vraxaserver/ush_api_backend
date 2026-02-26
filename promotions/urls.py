"""
Promotions (Gift Cards & Loyalty Program) URL Configuration.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    LoyaltyRewardViewSet,
    LoyaltyStatusView,
    LoyaltyTrackerViewSet,
)

app_name = "promotions"

router = DefaultRouter()
router.register(r"loyalty-trackers", LoyaltyTrackerViewSet, basename="loyalty-tracker")
router.register(r"loyalty-rewards", LoyaltyRewardViewSet, basename="loyalty-reward")

urlpatterns = [
    path("", include(router.urls)),
    path("loyalty/status/", LoyaltyStatusView.as_view(), name="loyalty-status"),
]
