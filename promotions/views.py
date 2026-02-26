"""
Promotions (Gift Cards & Loyalty Program) Views.
"""

from django.db.models import Sum
from django_filters import rest_framework as django_filters
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    LoyaltyReward,
    LoyaltyTracker,
)

from .serializers import (
    LoyaltyRedeemSerializer,
    LoyaltyRewardSerializer,
    LoyaltyTrackerSerializer,
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
        ).select_related("service")


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
        ).select_related("service")

    @action(detail=False, methods=["post"])
    def redeem(self, request):
        """
        Redeem a loyalty reward for a free booking.

        Request body:
        - reward_id: UUID of the loyalty reward
        - booking_id: (optional) UUID of the free booking to link

        Returns the updated reward details.
        """
        serializer = LoyaltyRedeemSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        reward = serializer.save()

        return Response({
            "success": True,
            "message": f"Loyalty reward redeemed successfully for service: {reward.service.name}.",
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

        trackers = LoyaltyTracker.objects.filter(
            customer=user,
        ).select_related("service")

        available_rewards = LoyaltyReward.objects.filter(
            customer=user,
            status=LoyaltyReward.RewardStatus.AVAILABLE,
        ).select_related("service")

        all_rewards = LoyaltyReward.objects.filter(customer=user)
        total_earned = all_rewards.count()
        total_redeemed = all_rewards.filter(
            status=LoyaltyReward.RewardStatus.REDEEMED,
        ).count()

        context = {"request": request}

        return Response({
            "trackers": LoyaltyTrackerSerializer(trackers, many=True, context=context).data,
            "available_rewards": LoyaltyRewardSerializer(available_rewards, many=True, context=context).data,
            "total_rewards_earned": total_earned,
            "total_rewards_redeemed": total_redeemed,
        })

