"""
Promotions (Gift Cards & Loyalty Program) Views.
"""

from collections import defaultdict
from datetime import datetime, timedelta

from django.db.models import Sum
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django_filters import rest_framework as django_filters
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    GiftCard,
    LoyaltyReward,
    LoyaltyTracker
)
from django.db import models

from .serializers import (
    GiftCardCreateSerializer,
    GiftCardDetailSerializer,
    GiftCardPublicSerializer,
    GiftCardRedeemSerializer,
    GiftCardValidityCheckSerializer,
    LoyaltyRedeemBookingSerializer,
    LoyaltyRewardSerializer,
    LoyaltyTrackerSerializer
)

# =============================================================================
# Loyalty Program Views
# =============================================================================

class LoyaltyTrackerViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for LoyaltyTracker (Read Only).

    Shows the authenticated user's loyalty progress across all eligible services.
    """

    serializer_class = LoyaltyTrackerSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.OrderingFilter,
    ]
    filterset_fields = ["service"]
    ordering_fields = ["booking_count", "updated_at"]
    ordering = ["-updated_at"]

    def get_queryset(self):
        return LoyaltyTracker.objects.filter(
            customer=self.request.user,
        ).select_related("service", "service_arrangement")


class LoyaltyRewardViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for LoyaltyReward (Read Only + Redeem action).

    Lists the authenticated user's loyalty rewards and allows redemption.
    """

    serializer_class = LoyaltyRewardSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.OrderingFilter,
    ]
    filterset_fields = ["status", "service"]
    ordering_fields = ["created_at", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return LoyaltyReward.objects.filter(
            customer=self.request.user,
        ).select_related("service", "service_arrangement")

    @action(detail=False, methods=["post"])
    def redeem(self, request):
        """
        Redeem a loyalty reward by creating a free booking.

        Request body:
        - reward_id: UUID of the loyalty reward
        - date: Booking date (YYYY-MM-DD)
        - start_time: Booking start time (HH:MM)
        - customer_message: (optional) Special requests

        Returns the created booking and updated reward details.
        """
        serializer = LoyaltyRedeemBookingSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()

        # Reload the reward for fresh status
        from .models import LoyaltyReward
        reward = booking.loyalty_reward
        reward.refresh_from_db()

        return Response({
            "success": True,
            "message": f"Loyalty reward redeemed. Free booking created for {booking.service.name}.",
            "booking": serializer.to_representation(booking),
            "reward": LoyaltyRewardSerializer(reward).data,
        })


class LoyaltyStatusView(APIView):
    """
    Loyalty Program Dashboard / Status View.

    Returns a summary of the authenticated user's loyalty progress and rewards.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """
        Get loyalty status summary.

        Returns:
        - trackers: List of loyalty progress per service
        - available_rewards: List of currently redeemable rewards
        - total_rewards_earned: Lifetime total
        - total_rewards_redeemed: Lifetime total
        """
        user = request.user

        all_trackers = LoyaltyTracker.objects.filter(
            customer=user,
        ).select_related("service", "service_arrangement")

        # Split trackers: active progress vs. recently rewarded (counter reset to 0)
        trackers = all_trackers.filter(booking_count__gt=0)
        most_recent_rewards = all_trackers.filter(booking_count=0)

        available_rewards = LoyaltyReward.objects.filter(
            customer=user,
            status=LoyaltyReward.RewardStatus.AVAILABLE,
        ).select_related("service", "service_arrangement")

        all_rewards = LoyaltyReward.objects.filter(customer=user)
        total_earned = all_rewards.count()
        total_redeemed = all_rewards.filter(
            status=LoyaltyReward.RewardStatus.REDEEMED,
        ).count()

        context = {"request": request}

        return Response({
            "trackers": LoyaltyTrackerSerializer(trackers, many=True, context=context).data,
            "most_recent_rewards": LoyaltyTrackerSerializer(most_recent_rewards, many=True, context=context).data,
            "available_rewards": LoyaltyRewardSerializer(available_rewards, many=True, context=context).data,
            "total_rewards_earned": total_earned,
            "total_rewards_redeemed": total_redeemed,
        })


# =============================================================================
# Gift Card Views
# =============================================================================

class GiftCardViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Gift Cards (authenticated user – sender).

    - POST /gift-cards/ – Create a new gift card (send a service as gift)
    - GET /gift-cards/ – List all gift cards sent by the authenticated user
    - GET /gift-cards/{id}/ – Get details of a specific gift card
    """

    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.OrderingFilter,
    ]
    filterset_fields = ["status"]
    ordering_fields = ["created_at", "status"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "create":
            return GiftCardCreateSerializer
        return GiftCardDetailSerializer

    def get_queryset(self):
        return GiftCard.objects.filter(
            sender=self.request.user,
        ).select_related(
            "service", "spa_center", "spa_center__city", "spa_center__country",
            "service_arrangement",
        )

    def create(self, request, *args, **kwargs):
        """
        Create a new gift card.

        Flow:
        1. User sends service_id, recipient_phone, optional recipient_name, gift_message.
        2. A gift card is created with status 'pending_payment'.
        3. Response includes the gift card details – client should initiate payment.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        gift_card = serializer.save()

        detail_serializer = GiftCardDetailSerializer(
            gift_card, context={"request": request},
        )

        return Response(
            {
                "success": True,
                "message": "Gift card created successfully. Please complete payment.",
                "gift_card": detail_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="simulate-payment")
    def simulate_payment(self, request, pk=None):
        """
        Simulate a successful payment for development/testing.

        In production, payment success would be triggered by a Stripe webhook.
        This endpoint activates the gift card and sends the SMS.
        """
        gift_card = self.get_object()

        if gift_card.status != GiftCard.GiftCardStatus.PENDING_PAYMENT:
            return Response(
                {"error": "Gift card is not pending payment."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Activate the gift card
        gift_card.activate()

        # Enqueue gift card SMS to SQS (ush_gift_sms_queue)
        from .tasks import send_gift_card_sms

        send_gift_card_sms(str(gift_card.id))

        detail_serializer = GiftCardDetailSerializer(
            gift_card, context={"request": request},
        )

        return Response({
            "success": True,
            "message": "Payment simulated. Gift card activated and SMS queued.",
            "gift_card": detail_serializer.data,
        })

    def update(self, request, *args, **kwargs):
        """Disable updates – gift cards are immutable after creation."""
        return Response(
            {"error": "Gift cards cannot be updated."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def partial_update(self, request, *args, **kwargs):
        """Disable partial updates."""
        return Response(
            {"error": "Gift cards cannot be updated."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def destroy(self, request, *args, **kwargs):
        """Disable deletion – only cancellation is allowed."""
        return Response(
            {"error": "Gift cards cannot be deleted. Use cancel action instead."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel a pending or active gift card."""
        gift_card = self.get_object()

        if gift_card.status not in [
            GiftCard.GiftCardStatus.PENDING_PAYMENT,
            GiftCard.GiftCardStatus.ACTIVE,
        ]:
            return Response(
                {"error": "Only pending or active gift cards can be cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        gift_card.status = GiftCard.GiftCardStatus.CANCELLED
        gift_card.save(update_fields=["status", "updated_at"])

        return Response({
            "success": True,
            "message": "Gift card cancelled successfully.",
            "gift_card": GiftCardDetailSerializer(gift_card, context={"request": request}).data,
        })


class GiftCardPublicView(APIView):
    """
    Public Gift Card Page (no authentication required).

    Renders an HTML template with gift card details.
    Only visible when payment is complete (status != pending_payment).
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request, public_token):
        gift_card = get_object_or_404(
            GiftCard.objects.select_related(
                "service",
                "spa_center",
                "spa_center__city",
                "spa_center__country",
                "sender",
                "service_arrangement",
                "redeemed_booking",
                "redeemed_booking__time_slot",
            ),
            public_token=public_token,
        )

        serializer = GiftCardPublicSerializer(gift_card, context={"request": request})

        return render(request, "gift_cards/public.html", {
            "gift_card": serializer.data,
        })


class GiftCardRedeemPageView(APIView):
    """
    Gift Card Redeem Page (no authentication required).

    Renders the HTML template for the redeem booking flow.
    Only accessible when the gift card is active and redeemable.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request, public_token):
        gift_card = get_object_or_404(
            GiftCard.objects.select_related(
                "service",
                "spa_center",
                "spa_center__city",
                "spa_center__country",
                "sender",
                "service_arrangement",
            ),
            public_token=public_token,
            status=GiftCard.GiftCardStatus.ACTIVE,
        )

        serializer = GiftCardPublicSerializer(gift_card, context={"request": request})

        return render(request, "gift_cards/redeem.html", {
            "gift_card": serializer.data,
        })


class GiftCardVerifyCodeView(APIView):
    """
    Verify a gift card secret code (no authentication required).

    POST with public_token + secret_code.
    Returns whether the code is valid without actually redeeming.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        public_token = request.data.get("public_token")
        secret_code = request.data.get("secret_code")

        if not public_token or not secret_code:
            return Response(
                {"valid": False, "message": "Both public_token and secret_code are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            gift_card = GiftCard.objects.get(public_token=public_token)
        except GiftCard.DoesNotExist:
            return Response(
                {"valid": False, "message": "Gift card not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not gift_card.is_redeemable:
            return Response(
                {"valid": False, "message": "This gift card is not available for redemption."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if gift_card.secret_code != secret_code:
            gift_card.record_failed_attempt()
            remaining = gift_card.max_attempts - gift_card.failed_attempts
            if remaining <= 0:
                msg = "Invalid code. Gift card is now locked due to too many failed attempts."
            else:
                msg = f"Invalid code. {remaining} attempt(s) remaining."
            return Response(
                {"valid": False, "message": msg, "is_locked": gift_card.is_locked},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"valid": True, "message": "Code verified successfully."})


class GiftCardAvailabilityView(APIView):
    """
    Get available time slots for a gift card's service arrangement.

    GET /gift-cards/api/availability/{public_token}/
    Returns available dates and time slots for the next 30 days.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request, public_token):
        from bookings.models import TimeSlot
        from spacenter.models import ServiceArrangement

        gift_card = get_object_or_404(
            GiftCard.objects.select_related(
                "service",
                "spa_center",
                "service_arrangement",
                "service_arrangement__spa_center",
            ),
            public_token=public_token,
            status=GiftCard.GiftCardStatus.ACTIVE,
        )

        arrangement = gift_card.service_arrangement
        spa_center = gift_card.spa_center
        service = gift_card.service

        today = timezone.now().date()
        date_from = today
        date_to = today + timedelta(days=30)

        # Get booked time slots for this arrangement
        booked_slots = TimeSlot.objects.filter(
            arrangement=arrangement,
            date__gte=date_from,
            date__lte=date_to,
        )

        # Build booked map
        booked_map = defaultdict(set)
        for slot in booked_slots:
            date_str = slot.date.isoformat()
            for hour_slot in slot.get_blocked_hour_slots():
                booked_map[date_str].add(hour_slot)

        # Generate available slots
        opening_hour = spa_center.default_opening_time.hour
        closing_hour = spa_center.default_closing_time.hour
        all_hours = [
            f"{h:02d}:00"
            for h in range(opening_hour, closing_hour)
        ]

        available_slots = {}
        current_date = date_from
        while current_date <= date_to:
            date_str = current_date.isoformat()
            day_slots = {}
            for hour in all_hours:
                hour_range = f"{hour} - {int(hour[:2])+1:02d}:00"
                if hour_range in booked_map.get(date_str, set()):
                    day_slots[hour] = "booked"
                else:
                    day_slots[hour] = "available"
            available_slots[date_str] = day_slots
            current_date += timedelta(days=1)

        return Response({
            "service_name": service.name,
            "spa_center_name": spa_center.name,
            "opening_time": spa_center.default_opening_time.strftime("%H:%M"),
            "closing_time": spa_center.default_closing_time.strftime("%H:%M"),
            "available_slots": available_slots,
        })


class GiftCardRedeemBookingView(APIView):
    """
    Create a booking from a gift card redemption.

    POST with public_token, secret_code, date, start_time.
    No authentication required — anyone with the code can book.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def _get_or_create_recipient_user(self, gift_card):
        """
        Get or create a user for the gift card recipient.
        If created, set a random password and send an SMS.
        """
        from accounts.models import User, UserType
        from config.utils.sms_service import send_sms_async
        
        phone_number = gift_card.recipient_phone
        user = User.objects.filter(phone_number=phone_number).first()
        
        if not user:
            # Create user
            from django.utils.crypto import get_random_string
            password = get_random_string(6)
            user = User.objects.create_user(
                phone_number=phone_number,
                password=password,
                first_name=gift_card.recipient_name or "Recipient",
                last_name="GiftUser",
                user_type=UserType.CUSTOMER,
                is_phone_verified=True
            )
            
            # Send SMS with password
            message = (
                f"Welcome to USH Spa! An account has been created for you. "
                f"Your temporary password is: {password}. "
                f"You can now login and manage your gift cards."
            )
            send_sms_async(str(phone_number), message)
            
        return user

    def post(self, request):
        from bookings.models import Booking, TimeSlot
        from django.db import transaction
        from decimal import Decimal

        public_token = request.data.get("public_token")
        secret_code = request.data.get("secret_code")
        date_str = request.data.get("date")
        start_time_str = request.data.get("start_time")

        # Validate required fields
        if not all([public_token, secret_code, date_str, start_time_str]):
            return Response(
                {"success": False, "message": "All fields are required: public_token, secret_code, date, start_time."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get the gift card
        try:
            gift_card = GiftCard.objects.select_related(
                "service", "spa_center", "sender", "service_arrangement",
            ).get(public_token=public_token)
        except GiftCard.DoesNotExist:
            return Response(
                {"success": False, "message": "Gift card not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Verify the code
        if not gift_card.is_redeemable:
            return Response(
                {"success": False, "message": "This gift card is not available for redemption."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if gift_card.secret_code != secret_code:
            gift_card.record_failed_attempt()
            return Response(
                {"success": False, "message": "Invalid secret code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Parse date and time
        try:
            booking_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"success": False, "message": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            start_time = datetime.strptime(start_time_str, "%H:%M").time()
        except ValueError:
            return Response(
                {"success": False, "message": "Invalid time format. Use HH:MM."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate date is not in the past
        if booking_date < timezone.now().date():
            return Response(
                {"success": False, "message": "Cannot book for a past date."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        arrangement = gift_card.service_arrangement
        service = gift_card.service
        spa_center = gift_card.spa_center

        # Check operating hours
        opening_time = spa_center.default_opening_time
        closing_time = spa_center.default_closing_time

        if start_time < opening_time:
            return Response(
                {"success": False, "message": f"Spa center opens at {opening_time}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Calculate end time
        service_duration = gift_card.total_duration or service.duration_minutes
        cleanup_duration = arrangement.cleanup_duration
        end_time = Booking.calculate_end_time(
            start_time, service_duration, 0, cleanup_duration
        )

        if end_time > closing_time:
            return Response(
                {"success": False, "message": "Booking exceeds closing time."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check availability
        overlapping = TimeSlot.objects.filter(
            arrangement=arrangement,
            date=booking_date,
            start_time__lt=end_time,
            end_time__gt=start_time,
        ).exists()

        if overlapping:
            return Response(
                {"success": False, "message": "This time slot is already booked."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create booking atomically
        try:
            with transaction.atomic():
                # Create time slot
                time_slot = TimeSlot.objects.create(
                    arrangement=arrangement,
                    date=booking_date,
                    start_time=start_time,
                    end_time=end_time,
                )

                # Build meta_data
                meta_data = {
                    "service": {
                        "id": str(service.id),
                        "name": service.name,
                        "duration_minutes": service.duration_minutes,
                        "currency": service.currency,
                    },
                    "spa_center": {
                        "id": str(spa_center.id),
                        "name": spa_center.name,
                        "city": spa_center.city.name if spa_center.city else None,
                        "country": spa_center.country.name if spa_center.country else None,
                        "address": spa_center.address or None,
                    },
                    "schedule": {
                        "date": str(booking_date),
                        "start_time": str(start_time),
                        "end_time": str(end_time),
                    },
                    "arrangement": {
                        "id": str(arrangement.id),
                        "type": arrangement.arrangement_type,
                        "room_count": arrangement.room_count,
                        "label": arrangement.arrangement_label,
                        "cleanup_duration": arrangement.cleanup_duration,
                    },
                    "pricing": {
                        "subtotal": "0.00",
                        "discount_amount": "0.00",
                        "extra_minutes": gift_card.extra_minutes,
                        "price_for_extra_minutes": "0.00",
                        "total_price": "0.00",
                    },
                    "gift_card": {
                        "gift_card_id": str(gift_card.id),
                        "is_gift_card": True,
                        "original_amount": str(gift_card.amount),
                        "sender_name": gift_card.sender.get_full_name() or str(gift_card.sender),
                    },
                }

                # Get or create recipient user
                recipient_user = self._get_or_create_recipient_user(gift_card)

                # Create booking
                booking = Booking.objects.create(
                    customer=recipient_user,
                    spa_center=spa_center,
                    service=service,
                    service_arrangement=arrangement,
                    time_slot=time_slot,
                    subtotal=Decimal("0.00"),
                    discount_amount=Decimal("0.00"),
                    extra_minutes=gift_card.extra_minutes,
                    price_for_extra_minutes=Decimal("0.00"),
                    total_duration=service_duration,
                    total_price=Decimal("0.00"),
                    status=Booking.BookingStatus.CONFIRMED,
                    is_gift_card=True,
                    gift_card=gift_card,
                    meta_data=meta_data,
                )

                # Redeem the gift card
                gift_card.status = GiftCard.GiftCardStatus.REDEEMED
                gift_card.redeemed_at = timezone.now()
                gift_card.redeemed_by = recipient_user
                gift_card.redeemed_booking = booking
                gift_card.save(update_fields=[
                    "status", "redeemed_at", "redeemed_by", "redeemed_booking", "updated_at",
                ])

            return Response({
                "success": True,
                "message": f"Booking confirmed for {service.name} on {booking_date}.",
                "booking_number": booking.booking_number,
                "booking_id": str(booking.id),
            })

        except Exception as e:
            return Response(
                {"success": False, "message": f"Failed to create booking: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class GiftCardValidityCheckView(APIView):
    """
    Public endpoint to check if a gift card is still valid.

    POST with public_token – returns validity status.
    No authentication required.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        """
        Check gift card validity.

        Request body: { "public_token": "..." }
        Returns: validity status and remaining details.
        """
        serializer = GiftCardValidityCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        gift_card = GiftCard.objects.select_related(
            "service", "spa_center", "spa_center__city", "spa_center__country",
            "sender", "service_arrangement",
        ).get(public_token=serializer.validated_data["public_token"])

        return Response({
            "is_valid": gift_card.is_redeemable,
            "status": gift_card.get_status_display(),
            "is_expired": gift_card.is_expired,
            "is_locked": gift_card.is_locked,
            "service_name": gift_card.service.name,
            "spa_center_name": gift_card.spa_center.name,
            "expires_at": gift_card.expires_at,
        })


class GiftCardRedeemView(APIView):
    """
    Public endpoint to redeem a gift card.

    POST with public_token + secret_code.
    No authentication required – anyone with the code can redeem.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        """
        Redeem a gift card.

        Request body:
        {
            "public_token": "...",
            "secret_code": "123456"
        }

        Returns success/failure with appropriate message.
        """
        serializer = GiftCardRedeemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        public_token = serializer.validated_data["public_token"]
        secret_code = serializer.validated_data["secret_code"]

        gift_card = GiftCard.objects.select_related(
            "service", "spa_center", "sender", "service_arrangement",
        ).get(public_token=public_token)

        # Get or create recipient user
        # Note: We use the same helper logic here. Since it's on another class, 
        # we can either duplicate or move it to a shared place. 
        # For simplicity in this file, I'll re-implement or call it if I moved it.
        # I'll move it to a mixin or just repeat for now as it's small.
        from accounts.models import User, UserType
        from config.utils.sms_service import send_sms_async
        
        phone_number = gift_card.recipient_phone
        recipient_user = User.objects.filter(phone_number=phone_number).first()
        
        if not recipient_user:
            from django.utils.crypto import get_random_string
            password = get_random_string(6)
            recipient_user = User.objects.create_user(
                phone_number=phone_number,
                password=password,
                first_name=gift_card.recipient_name or "Recipient",
                last_name="GiftUser",
                user_type=UserType.CUSTOMER,
                is_phone_verified=True
            )
            message = (
                f"Welcome to USH Spa! An account has been created for you. "
                f"Your temporary password is: {password}. "
                f"You can now login and manage your gift cards."
            )
            send_sms_async(str(phone_number), message)

        success, error = gift_card.redeem(secret_code=secret_code, redeemed_by_user=recipient_user)

        if not success:
            return Response(
                {
                    "success": False,
                    "message": str(error),
                    "is_locked": gift_card.is_locked,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({
            "success": True,
            "message": "Gift card redeemed successfully! You can now book this service.",
            "service_name": gift_card.service.name,
            "spa_center_name": gift_card.spa_center.name,
            "redeemed_at": gift_card.redeemed_at,
        })


class UserGiftCardViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Gift Cards received or redeemed by the authenticated user.
    """

    serializer_class = GiftCardDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.OrderingFilter,
    ]
    filterset_fields = ["status"]
    ordering_fields = ["created_at", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        user = self.request.user
        return GiftCard.objects.filter(
            models.Q(redeemed_by=user) | models.Q(recipient_phone=user.phone_number)
        ).select_related(
            "service", "spa_center", "spa_center__city", "spa_center__country",
            "sender", "service_arrangement",
        )


class GiftCardFulfillView(APIView):
    """
    Mark a redeemed gift card as Service Fulfilled.

    Called by spa staff once the recipient has visited the spa and enjoyed
    the service. Transitions the gift card from REDEEMED → FULFILLED.

    POST /api/v1/promotions/gift-cards/{public_token}/fulfill/
    Requires authentication (staff or admin).

    Request body (optional):
        {} — no body required, authenticated user is recorded as the fulfiller.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, public_token):
        try:
            gift_card = GiftCard.objects.select_related(
                "service", "spa_center",
            ).get(public_token=public_token)
        except GiftCard.DoesNotExist:
            return Response(
                {"success": False, "message": "Gift card not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        success, error = gift_card.fulfill(fulfilled_by_user=request.user)

        if not success:
            return Response(
                {"success": False, "message": str(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({
            "success": True,
            "message": "🎉 Service marked as fulfilled. Thank you for providing an amazing experience!",
            "public_token": str(gift_card.public_token),
            "status": gift_card.status,
            "status_display": gift_card.get_status_display(),
            "fulfilled_at": gift_card.fulfilled_at,
            "service_name": gift_card.service.name,
            "spa_center_name": gift_card.spa_center.name,
        })
