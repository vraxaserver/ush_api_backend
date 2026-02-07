"""
Payment URL Configuration.

API endpoints for Stripe payment integration.
"""

from django.urls import path

from .views import StripePaymentViewSet, StripeWebhookView

urlpatterns = [
    path("payment-sheet/", StripePaymentViewSet.as_view({'post': 'payment_sheet'}), name="payment-sheet"),
    path("webhook/", StripeWebhookView.as_view(), name="stripe-webhook"),
]
