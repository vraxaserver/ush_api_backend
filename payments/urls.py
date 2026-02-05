"""
Payment URL Configuration.

API endpoints for Stripe payment integration.
"""

from django.urls import path

from .views import CreatePaymentSheetView, StripeWebhookView

urlpatterns = [
    path("payment-sheet/", CreatePaymentSheetView.as_view(), name="payment-sheet"),
    path("webhook/", StripeWebhookView.as_view(), name="stripe-webhook"),
]
