"""
Promotions (Gift Cards & Loyalty Program) Views.
"""

from django.db.models import Sum
from django.shortcuts import get_object_or_404
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

        # Send SMS asynchronously
        from .tasks import send_gift_card_sms

        send_gift_card_sms.delay(str(gift_card.id))

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

    GET – Retrieve gift card details by public token.
    Shows service info, location, and validity status.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request, public_token):
        """
        Get public gift card details.

        Returns service details, spa center location, and validity status.
        Does NOT expose secret code or sensitive sender info.
        """
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
        )

        serializer = GiftCardPublicSerializer(gift_card, context={"request": request})

        return Response(serializer.data)


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

        success, error = gift_card.redeem(secret_code=secret_code)

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
