"""
Promotions (Gift Cards & Loyalty Program) Serializers.
"""

from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .models import (
    GiftCard,
    LoyaltyReward,
    LoyaltyTracker,
)


# =============================================================================
# Loyalty Program Serializers
# =============================================================================

class LoyaltyTrackerSerializer(serializers.ModelSerializer):
    """Serializer for LoyaltyTracker – shows progress per service per arrangement."""

    service_name = serializers.CharField(source="service.name", read_only=True)
    service_id = serializers.UUIDField(source="service.id", read_only=True)
    service_description = serializers.CharField(source="service.description", read_only=True)
    service_image = serializers.SerializerMethodField()
    service_arrangement_id = serializers.UUIDField(
        source="service_arrangement.id", read_only=True, default=None,
    )
    service_arrangement_label = serializers.CharField(
        source="service_arrangement.arrangement_label", read_only=True, default=None,
    )
    service_arrangement_type = serializers.CharField(
        source="service_arrangement.get_arrangement_type_display", read_only=True, default=None,
    )
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
            "service_arrangement_id",
            "service_arrangement_label",
            "service_arrangement_type",
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
    service_arrangement_id = serializers.UUIDField(
        source="service_arrangement.id", read_only=True, default=None,
    )
    service_arrangement_label = serializers.CharField(
        source="service_arrangement.arrangement_label", read_only=True, default=None,
    )
    service_arrangement_type = serializers.CharField(
        source="service_arrangement.get_arrangement_type_display", read_only=True, default=None,
    )
    is_available = serializers.BooleanField(read_only=True)

    class Meta:
        model = LoyaltyReward
        fields = [
            "id",
            "service_id",
            "service_name",
            "service_description",
            "service_image",
            "service_arrangement_id",
            "service_arrangement_label",
            "service_arrangement_type",
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


class LoyaltyRedeemBookingSerializer(serializers.Serializer):
    """
    Redeem a loyalty reward by creating a free booking.

    Creates a Booking + TimeSlot atomically, marks the reward as redeemed,
    and links the reward to the new booking. The service and arrangement
    are resolved from the reward itself.

    Input fields:
        - reward_id (UUID): The loyalty reward to redeem
        - date (date): Desired booking date
        - start_time (time): Desired start time
        - customer_message (str, optional): Special requests
    """

    reward_id = serializers.UUIDField()
    date = serializers.DateField()
    start_time = serializers.TimeField()
    customer_message = serializers.CharField(
        required=False, allow_blank=True, default=""
    )

    def validate_reward_id(self, value):
        """Ensure the reward exists, belongs to the current user, and is available."""
        request = self.context.get("request")
        try:
            reward = LoyaltyReward.objects.select_related(
                "service", "service_arrangement", "service__spa_center",
            ).get(id=value)
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

    def validate_date(self, value):
        """Validate that the date is not in the past."""
        from django.utils import timezone as tz
        today = tz.now().date()
        if value < today:
            raise serializers.ValidationError("Cannot book for a past date.")
        return value

    def validate(self, attrs):
        """
        Cross-field validation:
        - Resolve service, arrangement, spa_center from the reward
        - Calculate end time
        - Check time slot availability
        """
        from bookings.models import Booking, TimeSlot

        reward = LoyaltyReward.objects.select_related(
            "service", "service_arrangement",
            "service__spa_center", "service_arrangement__spa_center",
        ).get(id=attrs["reward_id"])

        service = reward.service
        arrangement = reward.service_arrangement
        spa_center = service.spa_center

        if not arrangement:
            raise serializers.ValidationError({
                "reward_id": "This reward has no service arrangement. Cannot create booking."
            })

        if not arrangement.is_active:
            raise serializers.ValidationError({
                "reward_id": "The service arrangement for this reward is no longer active."
            })

        date = attrs["date"]
        start_time = attrs["start_time"]

        # Check spa center operating hours
        opening_time = spa_center.default_opening_time
        closing_time = spa_center.default_closing_time

        if start_time < opening_time:
            raise serializers.ValidationError({
                "start_time": f"Spa center opens at {opening_time}."
            })

        # Calculate end time
        service_duration = service.duration_minutes
        cleanup_duration = arrangement.cleanup_duration
        end_time = Booking.calculate_end_time(
            start_time, service_duration, 0, cleanup_duration
        )

        if end_time > closing_time:
            raise serializers.ValidationError({
                "start_time": "Booking exceeds closing time."
            })

        # Check availability
        overlapping_count = TimeSlot.objects.filter(
            arrangement=arrangement,
            date=date,
            start_time__lt=end_time,
            end_time__gt=start_time,
        ).count()

        if overlapping_count >= arrangement.room_count:
            raise serializers.ValidationError({
                "start_time": "Selected arrangement has no available space for this time."
            })

        # Store resolved objects
        attrs["reward"] = reward
        attrs["service"] = service
        attrs["arrangement"] = arrangement
        attrs["spa_center"] = spa_center
        attrs["end_time"] = end_time
        attrs["service_duration"] = service_duration

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        """Create a free booking and redeem the reward atomically."""
        from bookings.models import Booking, TimeSlot
        from decimal import Decimal

        request = self.context.get("request")
        customer = request.user

        reward = validated_data["reward"]
        service = validated_data["service"]
        arrangement = validated_data["arrangement"]
        spa_center = validated_data["spa_center"]
        date = validated_data["date"]
        start_time = validated_data["start_time"]
        end_time = validated_data["end_time"]
        service_duration = validated_data["service_duration"]

        # 1. Create time slot
        time_slot = TimeSlot.objects.create(
            arrangement=arrangement,
            date=date,
            start_time=start_time,
            end_time=end_time,
        )

        # 2. Build meta_data snapshot
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
                "date": str(date),
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
                "extra_minutes": 0,
                "price_for_extra_minutes": "0.00",
                "total_price": "0.00",
            },
            "loyalty": {
                "reward_id": str(reward.id),
                "is_loyalty_reward": True,
            },
        }

        # 3. Create booking (free — total_price=0, status=CONFIRMED)
        booking = Booking.objects.create(
            customer=customer,
            spa_center=spa_center,
            service=service,
            service_arrangement=arrangement,
            time_slot=time_slot,
            subtotal=Decimal("0.00"),
            discount_amount=Decimal("0.00"),
            extra_minutes=0,
            price_for_extra_minutes=Decimal("0.00"),
            total_duration=service_duration,
            total_price=Decimal("0.00"),
            customer_message=validated_data.get("customer_message", ""),
            status=Booking.BookingStatus.CONFIRMED,
            is_loyalty_reward=True,
            loyalty_reward=reward,
            meta_data=meta_data,
        )

        # 4. Redeem the reward and link to the booking
        success, error = reward.redeem(booking=booking)
        if not success:
            raise serializers.ValidationError({"reward_id": str(error)})

        return booking

    def to_representation(self, instance):
        """Return full booking details after creation."""
        from bookings.serializers import BookingSerializer
        return BookingSerializer(instance).data


# =============================================================================
# Gift Card Serializers
# =============================================================================

class GiftCardCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a gift card.

    Authenticated user selects a service, spa center, and provides recipient phone number.
    """

    service_id = serializers.UUIDField(write_only=True)
    spa_center_id = serializers.UUIDField(
        write_only=True,
        help_text="Spa center ID where the service will be redeemed",
    )
    service_arrangement_id = serializers.UUIDField(
        write_only=True,
        help_text="Service arrangement (room/setup) ID",
    )
    extra_minutes = serializers.IntegerField(
        required=False,
        default=0,
        min_value=0,
        help_text="Extra minutes to add to the service duration",
    )
    total_duration = serializers.IntegerField(
        min_value=1,
        help_text="Total duration in minutes (service time + extra time)",
    )
    recipient_phone = serializers.CharField(
        help_text="Phone number of the gift recipient (E.164 format, e.g., +97450123456)"
    )
    recipient_name = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Optional name for the recipient",
    )
    gift_message = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Optional personal message to the recipient",
    )
    expires_at = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="Optional expiry date for redemption",
    )

    class Meta:
        model = GiftCard
        fields = [
            "service_id",
            "spa_center_id",
            "service_arrangement_id",
            "extra_minutes",
            "total_duration",
            "recipient_phone",
            "recipient_name",
            "gift_message",
            "expires_at",
        ]

    def validate_service_id(self, value):
        """Ensure the service exists and is active."""
        from spacenter.models import Service
        try:
            Service.objects.get(id=value, is_active=True)
        except Service.DoesNotExist:
            raise serializers.ValidationError("Service not found or is inactive.")
        return value

    def validate_spa_center_id(self, value):
        """Ensure the spa center exists and is active."""
        from spacenter.models import SpaCenter
        try:
            SpaCenter.objects.get(id=value, is_active=True)
        except SpaCenter.DoesNotExist:
            raise serializers.ValidationError("Spa center not found or is inactive.")
        return value

    def validate_service_arrangement_id(self, value):
        """Ensure the service arrangement exists and is active."""
        from spacenter.models import ServiceArrangement
        try:
            ServiceArrangement.objects.get(id=value, is_active=True)
        except ServiceArrangement.DoesNotExist:
            raise serializers.ValidationError("Service arrangement not found or is inactive.")
        return value

    def validate(self, attrs):
        """Ensure arrangement belongs to the selected service and spa center offers the service."""
        service_id = attrs.get("service_id")
        spa_center_id = attrs.get("spa_center_id")
        arrangement_id = attrs.get("service_arrangement_id")

        # Verify the service belongs to the spa center
        from spacenter.models import Service
        try:
            service = Service.objects.get(id=service_id)
            if str(service.spa_center_id) != str(spa_center_id):
                raise serializers.ValidationError({
                    "spa_center_id": "This spa center does not offer the selected service."
                })
        except Service.DoesNotExist:
            pass  # Already validated above

        # Verify arrangement belongs to the service
        from spacenter.models import ServiceArrangement
        try:
            arrangement = ServiceArrangement.objects.get(id=arrangement_id)
            if str(arrangement.service_id) != str(service_id):
                raise serializers.ValidationError({
                    "service_arrangement_id": "This arrangement does not belong to the selected service."
                })
        except ServiceArrangement.DoesNotExist:
            pass  # Already validated above

        return attrs

    def create(self, validated_data):
        """Create a gift card with provided fields."""
        from spacenter.models import Service, ServiceArrangement, SpaCenter

        service_id = validated_data.pop("service_id")
        spa_center_id = validated_data.pop("spa_center_id")
        arrangement_id = validated_data.pop("service_arrangement_id")
        extra_minutes = validated_data.pop("extra_minutes", 0)
        total_duration = validated_data.pop("total_duration")

        service = Service.objects.get(id=service_id)
        spa_center = SpaCenter.objects.get(id=spa_center_id)
        arrangement = ServiceArrangement.objects.get(id=arrangement_id)

        gift_card = GiftCard.objects.create(
            sender=self.context["request"].user,
            service=service,
            spa_center=spa_center,
            service_arrangement=arrangement,
            extra_minutes=extra_minutes,
            total_duration=total_duration,
            amount=service.current_price,
            currency=service.currency,
            recipient_phone=validated_data["recipient_phone"],
            recipient_name=validated_data.get("recipient_name", ""),
            gift_message=validated_data.get("gift_message", ""),
            expires_at=validated_data.get("expires_at"),
        )

        return gift_card


class GiftCardDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for gift cards – for authenticated sender."""

    sender_name = serializers.SerializerMethodField()
    service_name = serializers.CharField(source="service.name", read_only=True)
    service_description = serializers.CharField(source="service.description", read_only=True)
    service_duration = serializers.IntegerField(source="service.duration_minutes", read_only=True)
    service_image = serializers.SerializerMethodField()
    service_arrangement_label = serializers.CharField(
        source="service_arrangement.arrangement_label", read_only=True, default=None,
    )
    service_arrangement_type = serializers.CharField(
        source="service_arrangement.get_arrangement_type_display", read_only=True, default=None,
    )
    spa_center_name = serializers.CharField(source="spa_center.name", read_only=True)
    spa_center_address = serializers.CharField(source="spa_center.full_address", read_only=True)
    spa_center_phone = serializers.CharField(source="spa_center.phone", read_only=True)
    public_url = serializers.SerializerMethodField()
    is_redeemable = serializers.BooleanField(read_only=True)

    class Meta:
        model = GiftCard
        fields = [
            "id",
            "sender_name",
            "recipient_phone",
            "recipient_name",
            "gift_message",
            "service",
            "service_name",
            "service_description",
            "service_duration",
            "service_image",
            "service_arrangement",
            "service_arrangement_label",
            "service_arrangement_type",
            "extra_minutes",
            "total_duration",
            "spa_center",
            "spa_center_name",
            "spa_center_address",
            "spa_center_phone",
            "amount",
            "currency",
            "status",
            "is_redeemable",
            "public_url",
            "public_token",
            "sms_sent",
            "sms_sent_at",
            "redeemed_at",
            "expires_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_sender_name(self, obj):
        return obj.sender.get_full_name() or str(obj.sender)

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

    def get_public_url(self, obj):
        return obj.get_public_url()


class GiftCardPublicSerializer(serializers.ModelSerializer):
    """
    Public serializer for gift cards – shown on the public page.

    Does NOT expose the secret code, sender details, or internal IDs.
    Shows service details, location, and validity status.
    """

    service_name = serializers.CharField(source="service.name", read_only=True)
    service_description = serializers.CharField(source="service.description", read_only=True)
    service_duration = serializers.IntegerField(source="service.duration_minutes", read_only=True)
    service_image = serializers.SerializerMethodField()
    service_arrangement_label = serializers.CharField(
        source="service_arrangement.arrangement_label", read_only=True, default=None,
    )
    service_arrangement_type = serializers.CharField(
        source="service_arrangement.get_arrangement_type_display", read_only=True, default=None,
    )
    spa_center_name = serializers.CharField(
        source="spa_center.name", read_only=True, allow_blank=True, allow_null=True, default="",
    )
    spa_center_address = serializers.CharField(
        source="spa_center.full_address", read_only=True, allow_blank=True, allow_null=True, default="",
    )
    spa_center_city = serializers.CharField(
        source="spa_center.city.name", read_only=True, allow_blank=True, allow_null=True, default="",
    )
    spa_center_country = serializers.CharField(
        source="spa_center.country.name", read_only=True, allow_blank=True, allow_null=True, default="",
    )
    spa_center_phone = serializers.CharField(
        source="spa_center.phone", read_only=True, allow_blank=True, allow_null=True, default="",
    )
    spa_center_latitude = serializers.DecimalField(
        source="spa_center.latitude", max_digits=9, decimal_places=6, read_only=True,
    )
    spa_center_longitude = serializers.DecimalField(
        source="spa_center.longitude", max_digits=9, decimal_places=6, read_only=True,
    )
    sender_name = serializers.SerializerMethodField()
    is_valid = serializers.SerializerMethodField()
    is_redeemable = serializers.BooleanField(read_only=True)
    is_locked = serializers.BooleanField(read_only=True)
    spa_center_image = serializers.SerializerMethodField()
    spa_center_opening_time = serializers.TimeField(
        source="spa_center.default_opening_time", read_only=True,
    )
    spa_center_closing_time = serializers.TimeField(
        source="spa_center.default_closing_time", read_only=True,
    )
    redeemed_booking_date = serializers.SerializerMethodField()
    redeemed_booking_time = serializers.SerializerMethodField()
    fulfilled_by_name = serializers.SerializerMethodField()

    class Meta:
        model = GiftCard
        fields = [
            "public_token",
            "sender_name",
            "recipient_name",
            "gift_message",
            "service_name",
            "service_description",
            "service_duration",
            "service_image",
            "service_arrangement_label",
            "service_arrangement_type",
            "extra_minutes",
            "total_duration",
            "spa_center_name",
            "spa_center_address",
            "spa_center_city",
            "spa_center_country",
            "spa_center_phone",
            "spa_center_latitude",
            "spa_center_longitude",
            "spa_center_image",
            "spa_center_opening_time",
            "spa_center_closing_time",
            "amount",
            "currency",
            "status",
            "is_valid",
            "is_redeemable",
            "is_locked",
            "expires_at",
            "created_at",
            "redeemed_at",
            "redeemed_booking_date",
            "redeemed_booking_time",
            "fulfilled_at",
            "fulfilled_by_name",
        ]
        read_only_fields = fields

    def get_sender_name(self, obj):
        return obj.sender.get_full_name() or "A friend"

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

    def get_is_valid(self, obj):
        """Check if the gift card is currently valid and redeemable."""
        return obj.is_redeemable

    def get_redeemed_booking_date(self, obj):
        """Return the booking date from the redeemed booking's time slot."""
        if obj.redeemed_booking and obj.redeemed_booking.time_slot:
            return str(obj.redeemed_booking.time_slot.date)
        return None

    def get_redeemed_booking_time(self, obj):
        """Return the booking start time from the redeemed booking's time slot."""
        if obj.redeemed_booking and obj.redeemed_booking.time_slot:
            return str(obj.redeemed_booking.time_slot.start_time)
        return None

    def get_fulfilled_by_name(self, obj):
        """Return the name of the staff who marked the service as fulfilled."""
        if obj.fulfilled_by:
            return obj.fulfilled_by.get_full_name() or str(obj.fulfilled_by)
        return None

    def get_spa_center_image(self, obj):
        """Return the URL of the spa center's primary image."""
        if hasattr(obj.spa_center, 'images'):
            image = (
                obj.spa_center.images.filter(is_primary=True).first()
                or obj.spa_center.images.first()
            )
            if image and image.image:
                request = self.context.get("request")
                if request:
                    return request.build_absolute_uri(image.image.url)
                return image.image.url
        return None


class GiftCardValidityCheckSerializer(serializers.Serializer):
    """Serializer for checking gift card validity (public, no auth required)."""

    public_token = serializers.CharField()

    def validate_public_token(self, value):
        try:
            gift_card = GiftCard.objects.select_related(
                "service", "spa_center", "spa_center__city", "spa_center__country", "sender",
            ).get(public_token=value)
        except GiftCard.DoesNotExist:
            raise serializers.ValidationError("Gift card not found.")
        return value


class GiftCardRedeemSerializer(serializers.Serializer):
    """
    Serializer for redeeming a gift card (public, no auth required).

    Requires the public token and the 6-digit secret code.
    """

    public_token = serializers.CharField()
    secret_code = serializers.CharField(
        min_length=6,
        max_length=6,
        help_text="6-digit secret code received via SMS",
    )

    def validate_public_token(self, value):
        try:
            gift_card = GiftCard.objects.select_related(
                "service", "spa_center", "sender",
            ).get(public_token=value)
        except GiftCard.DoesNotExist:
            raise serializers.ValidationError("Gift card not found.")
        return value

    def validate_secret_code(self, value):
        if not value.isdigit() or len(value) != 6:
            raise serializers.ValidationError("Secret code must be exactly 6 digits.")
        return value
