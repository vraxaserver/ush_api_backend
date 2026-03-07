"""
Gift Card Public URLs.

All URLs under /gift-cards/ — public pages and API endpoints
for gift card viewing, redemption, and booking.
"""

from django.urls import path

from .views import (
    GiftCardAvailabilityView,
    GiftCardPublicView,
    GiftCardRedeemBookingView,
    GiftCardRedeemPageView,
    GiftCardRedeemView,
    GiftCardValidityCheckView,
    GiftCardVerifyCodeView,
)

app_name = "gift_cards"

urlpatterns = [
    # HTML Pages
    path(
        "public/<str:public_token>/",
        GiftCardPublicView.as_view(),
        name="public",
    ),
    path(
        "redeem/<str:public_token>/",
        GiftCardRedeemPageView.as_view(),
        name="redeem-page",
    ),

    # API Endpoints (called by JS on the redeem page)
    path(
        "api/verify-code/",
        GiftCardVerifyCodeView.as_view(),
        name="verify-code",
    ),
    path(
        "api/availability/<str:public_token>/",
        GiftCardAvailabilityView.as_view(),
        name="availability",
    ),
    path(
        "api/redeem-booking/",
        GiftCardRedeemBookingView.as_view(),
        name="redeem-booking",
    ),
    path(
        "api/check-validity/",
        GiftCardValidityCheckView.as_view(),
        name="check-validity",
    ),
    path(
        "api/redeem/",
        GiftCardRedeemView.as_view(),
        name="redeem",
    ),
]
