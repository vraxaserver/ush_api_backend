"""
Promotions (Gift Cards & Loyalty Program) URL Configuration.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    GiftCardPublicView,
    GiftCardRedeemView,
    GiftCardValidityCheckView,
    GiftCardViewSet,
    LoyaltyRewardViewSet,
    LoyaltyStatusView,
    LoyaltyTrackerViewSet,
)

app_name = "promotions"

router = DefaultRouter()
router.register(r"loyalty-trackers", LoyaltyTrackerViewSet, basename="loyalty-tracker")
router.register(r"loyalty-rewards", LoyaltyRewardViewSet, basename="loyalty-reward")
router.register(r"gift-cards", GiftCardViewSet, basename="gift-card")

urlpatterns = [
    path("", include(router.urls)),
    path("loyalty/status/", LoyaltyStatusView.as_view(), name="loyalty-status"),

    # Public gift card endpoints (no authentication required)
    path(
        "gift-cards/public/<str:public_token>/",
        GiftCardPublicView.as_view(),
        name="gift-card-public",
    ),
    path(
        "gift-cards/check-validity/",
        GiftCardValidityCheckView.as_view(),
        name="gift-card-check-validity",
    ),
    path(
        "gift-cards/redeem/",
        GiftCardRedeemView.as_view(),
        name="gift-card-redeem",
    ),
]
