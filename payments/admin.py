"""
Payment Admin Configuration.

Admin interface for managing Stripe customers and payments.
"""

from django.contrib import admin

from .models import Payment, StripeCustomer


@admin.register(StripeCustomer)
class StripeCustomerAdmin(admin.ModelAdmin):
    list_display = ["user", "stripe_customer_id", "created_at"]
    search_fields = ["user__email", "stripe_customer_id"]
    readonly_fields = ["stripe_customer_id", "created_at", "updated_at"]
    list_filter = ["created_at"]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        "stripe_payment_intent_id",
        "user",
        "amount",
        "currency",
        "status",
        "booking",
        "created_at",
    ]
    list_filter = ["status", "currency", "created_at"]
    search_fields = [
        "stripe_payment_intent_id",
        "user__email",
        "booking__id",
    ]
    readonly_fields = [
        "stripe_payment_intent_id",
        "amount",
        "currency",
        "metadata",
        "created_at",
        "updated_at",
    ]
    raw_id_fields = ["user", "booking"]
