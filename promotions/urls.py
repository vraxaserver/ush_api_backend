"""
Promotions (Vouchers & Gift Cards) URL Configuration.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ApplyDiscountsView,
    GiftCardTemplateViewSet,
    GiftCardTransactionViewSet,
    GiftCardViewSet,
    VoucherUsageViewSet,
    VoucherViewSet,
)

app_name = "promotions"

router = DefaultRouter()
router.register(r"vouchers", VoucherViewSet, basename="voucher")
router.register(r"voucher-usage", VoucherUsageViewSet, basename="voucher-usage")
router.register(r"gift-card-templates", GiftCardTemplateViewSet, basename="gift-card-template")
router.register(r"gift-cards", GiftCardViewSet, basename="gift-card")
router.register(r"gift-card-transactions", GiftCardTransactionViewSet, basename="gift-card-transaction")

urlpatterns = [
    path("", include(router.urls)),
    path("apply-discounts/", ApplyDiscountsView.as_view(), name="apply-discounts"),
]
