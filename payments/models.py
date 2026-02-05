"""
Payment Models for Stripe Integration.

Models for tracking Stripe customers and payment transactions.
"""

from django.conf import settings
from django.db import models


class StripeCustomer(models.Model):
    """
    Links Django user to Stripe Customer ID.
    
    Allows reusing the same Stripe customer for returning users,
    enabling saved payment methods and better customer management.
    """
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="stripe_customer",
    )
    stripe_customer_id = models.CharField(
        max_length=255,
        unique=True,
        help_text="Stripe Customer ID (cus_xxx)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Stripe Customer"
        verbose_name_plural = "Stripe Customers"

    def __str__(self):
        return f"{self.user.email} - {self.stripe_customer_id}"


class Payment(models.Model):
    """
    Tracks payment transactions via Stripe.
    
    Stores payment intent information and status for audit trails
    and linking payments to bookings.
    """
    
    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        CANCELED = "canceled", "Canceled"
        REQUIRES_ACTION = "requires_action", "Requires Action"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    booking = models.ForeignKey(
        "bookings.Booking",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
        help_text="Optional booking this payment is for",
    )
    stripe_payment_intent_id = models.CharField(
        max_length=255,
        unique=True,
        help_text="Stripe PaymentIntent ID (pi_xxx)",
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Payment amount in the smallest currency unit",
    )
    currency = models.CharField(
        max_length=3,
        default="usd",
        help_text="Three-letter ISO currency code",
    )
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional payment metadata from Stripe",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment {self.stripe_payment_intent_id} - {self.status}"
