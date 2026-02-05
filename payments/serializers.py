"""
Payment Serializers for Stripe Integration.

Serializers for payment sheet request and response handling.
"""

from rest_framework import serializers

from .models import Payment


class PaymentSheetRequestSerializer(serializers.Serializer):
    """
    Request serializer for creating a payment sheet.
    
    Validates the payment amount, currency, and optional booking reference.
    """
    
    amount = serializers.IntegerField(
        min_value=1,
        help_text="Amount in smallest currency unit (e.g., cents for USD)",
    )
    currency = serializers.CharField(
        max_length=3,
        default="usd",
        help_text="Three-letter ISO currency code (e.g., usd, eur)",
    )
    booking_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Optional booking ID to associate with this payment",
    )


class PaymentSheetResponseSerializer(serializers.Serializer):
    """
    Response serializer with PaymentSheet initialization parameters.
    
    Returns all necessary secrets and IDs for the React Native client
    to initialize and present the PaymentSheet.
    """
    
    paymentIntent = serializers.CharField(
        help_text="PaymentIntent client secret",
    )
    customerSessionClientSecret = serializers.CharField(
        help_text="CustomerSession client secret for secure client access",
    )
    customer = serializers.CharField(
        help_text="Stripe Customer ID",
    )
    publishableKey = serializers.CharField(
        help_text="Stripe publishable key for client initialization",
    )


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for Payment model."""
    
    class Meta:
        model = Payment
        fields = [
            "id",
            "stripe_payment_intent_id",
            "amount",
            "currency",
            "status",
            "booking",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
