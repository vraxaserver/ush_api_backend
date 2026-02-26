"""
Promotions (Gift Cards & Loyalty Program) Serializers.
"""

from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from .models import (
    LoyaltyReward,
    LoyaltyTracker,
)


# =============================================================================
# Loyalty Program Serializers
# =============================================================================

class LoyaltyTrackerSerializer(serializers.ModelSerializer):
    """Serializer for LoyaltyTracker – shows progress per service."""

    service_name = serializers.CharField(source="service.name", read_only=True)
    service_id = serializers.UUIDField(source="service.id", read_only=True)
    service_description = serializers.CharField(source="service.description", read_only=True)
    service_image = serializers.SerializerMethodField()
    progress_percentage = serializers.FloatField(read_only=True)
    bookings_remaining = serializers.IntegerField(read_only=True)

    class Meta:
        model = LoyaltyTracker
        fields = [
            "id",
            "service_id",
            "service_name",
            "service_description",
            "service_image",
            "booking_count",
            "bookings_required",
            "bookings_remaining",
            "progress_percentage",
            "total_bookings",
            "total_rewards_earned",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_service_image(self, obj):
        """Return the URL of the primary service image (or first available)."""
        image = (
            obj.service.images.filter(is_primary=True).first()
            or obj.service.images.first()
        )
        if image and image.image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(image.image.url)
            return image.image.url
        return None


class LoyaltyRewardSerializer(serializers.ModelSerializer):
    """Serializer for LoyaltyReward – shows earned free-booking rewards."""

    service_name = serializers.CharField(source="service.name", read_only=True)
    service_id = serializers.UUIDField(source="service.id", read_only=True)
    service_description = serializers.CharField(source="service.description", read_only=True)
    service_image = serializers.SerializerMethodField()
    is_available = serializers.BooleanField(read_only=True)

    class Meta:
        model = LoyaltyReward
        fields = [
            "id",
            "service_id",
            "service_name",
            "service_description",
            "service_image",
            "status",
            "is_available",
            "earned_from_booking",
            "redeemed_in_booking",
            "redeemed_at",
            "expires_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_service_image(self, obj):
        """Return the URL of the primary service image (or first available)."""
        image = (
            obj.service.images.filter(is_primary=True).first()
            or obj.service.images.first()
        )
        if image and image.image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(image.image.url)
            return image.image.url
        return None


class LoyaltyRedeemSerializer(serializers.Serializer):
    """Serializer for redeeming a loyalty reward."""

    reward_id = serializers.UUIDField()
    booking_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="Optional: Link this reward to a specific free booking.",
    )

    def validate_reward_id(self, value):
        """Ensure the reward exists and belongs to the current user."""
        request = self.context.get("request")
        try:
            reward = LoyaltyReward.objects.select_related("service").get(id=value)
        except LoyaltyReward.DoesNotExist:
            raise serializers.ValidationError("Loyalty reward not found.")

        if request and request.user.is_authenticated:
            if reward.customer != request.user:
                raise serializers.ValidationError("This reward does not belong to you.")

        if not reward.is_available:
            if reward.status == LoyaltyReward.RewardStatus.REDEEMED:
                raise serializers.ValidationError("This reward has already been redeemed.")
            elif reward.status == LoyaltyReward.RewardStatus.EXPIRED:
                raise serializers.ValidationError("This reward has expired.")
            elif reward.status == LoyaltyReward.RewardStatus.CANCELLED:
                raise serializers.ValidationError("This reward has been cancelled.")
            else:
                raise serializers.ValidationError("This reward is no longer available.")

        return value

    def validate(self, attrs):
        reward = LoyaltyReward.objects.select_related("service").get(id=attrs["reward_id"])
        attrs["reward"] = reward

        booking_id = attrs.get("booking_id")
        if booking_id:
            from bookings.models import Booking
            try:
                booking = Booking.objects.get(id=booking_id)
                attrs["booking"] = booking
            except Booking.DoesNotExist:
                raise serializers.ValidationError({"booking_id": "Booking not found."})
        else:
            attrs["booking"] = None

        return attrs

    def create(self, validated_data):
        """Redeem the loyalty reward."""
        reward = validated_data["reward"]
        booking = validated_data.get("booking")

        success, error = reward.redeem(booking=booking)
        if not success:
            raise serializers.ValidationError({"reward_id": str(error)})

        return reward

