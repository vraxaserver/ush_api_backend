"""
Promotions (Gift Cards & Loyalty Program) URL Configuration.

Note: Public gift card pages and API endpoints are served under
/gift-cards/ via gift_card_urls.py (included in config/urls.py).
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    GiftCardViewSet,
    LoyaltyRewardViewSet,
    LoyaltyStatusView,
    LoyaltyTrackerViewSet,
    UserGiftCardViewSet,
)

app_name = "promotions"

router = DefaultRouter()
router.register(r"loyalty-trackers", LoyaltyTrackerViewSet, basename="loyalty-tracker")
router.register(r"loyalty-rewards", LoyaltyRewardViewSet, basename="loyalty-reward")
router.register(r"gift-cards", GiftCardViewSet, basename="gift-card")
router.register(r"my-gift-cards", UserGiftCardViewSet, basename="my-gift-card")

urlpatterns = [
    path("", include(router.urls)),
    path("loyalty/status/", LoyaltyStatusView.as_view(), name="loyalty-status"),
]
