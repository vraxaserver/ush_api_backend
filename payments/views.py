"""
Payment Views for Stripe Integration.

Views for creating PaymentSheet parameters and handling Stripe webhooks.
"""

import logging

import stripe
from django.conf import settings
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from bookings.models import Booking

from .models import Payment, StripeCustomer
from .serializers import (
    PaymentSheetRequestSerializer,
    PaymentSheetResponseSerializer,
)

logger = logging.getLogger(__name__)

# Initialize Stripe with secret key
stripe.api_key = settings.STRIPE_SECRET_KEY


class CreatePaymentSheetView(APIView):
    """
    Create PaymentSheet parameters for React Native client.
    
    POST /api/v1/payments/payment-sheet/
    
    Request body:
        {
            "amount": 1000,  // Amount in cents
            "currency": "usd",
            "booking_id": 123  // Optional
        }
    
    Response:
        {
            "paymentIntent": "pi_xxx_secret_xxx",
            "customerSessionClientSecret": "cuss_xxx",
            "customer": "cus_xxx",
            "publishableKey": "pk_test_xxx"
        }
    """
    
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PaymentSheetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        amount = serializer.validated_data["amount"]
        currency = serializer.validated_data.get("currency", "usd")
        booking_id = serializer.validated_data.get("booking_id")
        
        user = request.user
        booking = None
        
        # Validate booking if provided
        if booking_id:
            try:
                booking = Booking.objects.get(id=booking_id, customer=user)
            except Booking.DoesNotExist:
                return Response(
                    {"error": "Booking not found or does not belong to you."},
                    status=status.HTTP_404_NOT_FOUND,
                )
        
        try:
            # Get or create Stripe Customer
            stripe_customer = self._get_or_create_stripe_customer(user)
            
            # Create CustomerSession for secure client access
            customer_session = stripe.CustomerSession.create(
                customer=stripe_customer.stripe_customer_id,
                components={
                    "mobile_payment_element": {
                        "enabled": True,
                        "features": {
                            "payment_method_save": "enabled",
                            "payment_method_redisplay": "enabled",
                            "payment_method_remove": "enabled",
                        },
                    },
                },
            )
            
            # Create PaymentIntent
            payment_intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                customer=stripe_customer.stripe_customer_id,
                automatic_payment_methods={"enabled": True},
                metadata={
                    "user_id": str(user.id),
                    "booking_id": str(booking_id) if booking_id else "",
                },
            )
            
            # Store payment record
            Payment.objects.create(
                user=user,
                booking=booking,
                stripe_payment_intent_id=payment_intent.id,
                amount=amount / 100,  # Convert cents to dollars for storage
                currency=currency,
                status=Payment.PaymentStatus.PENDING,
            )
            
            # Build response
            response_data = {
                "paymentIntent": payment_intent.client_secret,
                "customerSessionClientSecret": customer_session.client_secret,
                "customer": stripe_customer.stripe_customer_id,
                "publishableKey": settings.STRIPE_PUBLISHABLE_KEY,
            }
            
            response_serializer = PaymentSheetResponseSerializer(data=response_data)
            response_serializer.is_valid(raise_exception=True)
            
            return Response(response_serializer.data, status=status.HTTP_200_OK)
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating payment sheet: {e}")
            return Response(
                {"error": f"Payment service error: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"Error creating payment sheet: {e}")
            return Response(
                {"error": "An unexpected error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _get_or_create_stripe_customer(self, user):
        """Get existing or create new Stripe customer for user."""
        try:
            return StripeCustomer.objects.get(user=user)
        except StripeCustomer.DoesNotExist:
            # Create new Stripe customer
            customer = stripe.Customer.create(
                email=user.email,
                name=getattr(user, "full_name", None) or user.email,
                metadata={"user_id": str(user.id)},
            )
            
            return StripeCustomer.objects.create(
                user=user,
                stripe_customer_id=customer.id,
            )


class StripeWebhookView(APIView):
    """
    Handle Stripe webhook events.
    
    POST /api/v1/payments/webhook/
    
    Handles events:
        - payment_intent.succeeded: Updates payment status to succeeded
        - payment_intent.payment_failed: Updates payment status to failed
    """
    
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
        
        if not sig_header:
            return Response(
                {"error": "Missing Stripe signature header"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        try:
            event = stripe.Webhook.construct_event(
                payload,
                sig_header,
                settings.STRIPE_WEBHOOK_SECRET,
            )
        except ValueError as e:
            logger.error(f"Invalid payload: {e}")
            return Response(
                {"error": "Invalid payload"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid signature: {e}")
            return Response(
                {"error": "Invalid signature"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        # Handle the event
        event_type = event["type"]
        data_object = event["data"]["object"]
        
        logger.info(f"Received Stripe webhook: {event_type}")
        
        if event_type == "payment_intent.succeeded":
            self._handle_payment_succeeded(data_object)
        elif event_type == "payment_intent.payment_failed":
            self._handle_payment_failed(data_object)
        else:
            logger.info(f"Unhandled event type: {event_type}")
        
        return Response({"status": "success"}, status=status.HTTP_200_OK)

    def _handle_payment_succeeded(self, payment_intent):
        """Handle successful payment."""
        payment_intent_id = payment_intent["id"]
        
        try:
            payment = Payment.objects.get(stripe_payment_intent_id=payment_intent_id)
            payment.status = Payment.PaymentStatus.SUCCEEDED
            payment.metadata = dict(payment_intent)
            payment.save()
            
            # Update related booking status if exists
            if payment.booking:
                payment.booking.status = "payment_success"
                payment.booking.save()
                logger.info(f"Updated booking {payment.booking.id} to payment_success")
            
            logger.info(f"Payment {payment_intent_id} marked as succeeded")
            
        except Payment.DoesNotExist:
            logger.warning(f"Payment not found for intent: {payment_intent_id}")

    def _handle_payment_failed(self, payment_intent):
        """Handle failed payment."""
        payment_intent_id = payment_intent["id"]
        
        try:
            payment = Payment.objects.get(stripe_payment_intent_id=payment_intent_id)
            payment.status = Payment.PaymentStatus.FAILED
            payment.metadata = dict(payment_intent)
            payment.save()
            
            # Update related booking status if exists
            if payment.booking:
                payment.booking.status = "payment_pending"
                payment.booking.save()
                logger.info(f"Updated booking {payment.booking.id} to payment_pending")
            
            logger.info(f"Payment {payment_intent_id} marked as failed")
            
        except Payment.DoesNotExist:
            logger.warning(f"Payment not found for intent: {payment_intent_id}")
