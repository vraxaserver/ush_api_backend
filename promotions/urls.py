"""
Promotions (Gift Cards & Loyalty Program) URL Configuration.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ApplyDiscountsView,
    GiftCardTemplateViewSet,
    GiftCardTransactionViewSet,
    GiftCardViewSet,
    LoyaltyRewardViewSet,
    LoyaltyStatusView,
    LoyaltyTrackerViewSet,
)

app_name = "promotions"

router = DefaultRouter()
router.register(r"gift-card-templates", GiftCardTemplateViewSet, basename="gift-card-template")
router.register(r"gift-cards", GiftCardViewSet, basename="gift-card")
router.register(r"gift-card-transactions", GiftCardTransactionViewSet, basename="gift-card-transaction")
router.register(r"loyalty-trackers", LoyaltyTrackerViewSet, basename="loyalty-tracker")
router.register(r"loyalty-rewards", LoyaltyRewardViewSet, basename="loyalty-reward")

urlpatterns = [
    path("", include(router.urls)),
    path("apply-discounts/", ApplyDiscountsView.as_view(), name="apply-discounts"),
    path("loyalty/status/", LoyaltyStatusView.as_view(), name="loyalty-status"),
]
