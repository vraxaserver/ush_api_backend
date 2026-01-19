"""
Booking Serializers for Spa Center Management.

Serializers for service arrangements, time slots, availability, and booking management.
"""

from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from spacenter.models import AddOnService, Service, SpaCenter, TherapistProfile
from spacenter.serializers import (
    AddOnServiceListSerializer,
    ServiceListSerializer,
    SpaCenterListSerializer,
)

from .models import Booking, ServiceArrangement, TimeSlot


# =============================================================================
# Service Arrangement Serializers
# =============================================================================


class ServiceArrangementSerializer(serializers.ModelSerializer):
    """Full serializer for ServiceArrangement model."""

    spa_center_name = serializers.CharField(source="spa_center.name", read_only=True)
    service_name = serializers.CharField(source="service.name", read_only=True)
    service_duration = serializers.IntegerField(
        source="service.duration_minutes", read_only=True
    )
    total_duration = serializers.SerializerMethodField()

    class Meta:
        model = ServiceArrangement
        fields = [
            "id",
            "spa_center",
            "spa_center_name",
            "service",
            "service_name",
            "service_duration",
            "room_no",
            "arrangement_type",
            "arrangement_label",
            "cleanup_duration",
            "total_duration",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_total_duration(self, obj):
        """Get total duration including service + cleanup."""
        return obj.total_service_duration


class ServiceArrangementListSerializer(serializers.ModelSerializer):
    """Minimal serializer for arrangement lists."""

    service_name = serializers.CharField(source="service.name", read_only=True)
    service_duration = serializers.IntegerField(
        source="service.duration_minutes", read_only=True
    )

    class Meta:
        model = ServiceArrangement
        fields = [
            "id",
            "room_no",
            "arrangement_type",
            "arrangement_label",
            "service_name",
            "service_duration",
            "cleanup_duration",
        ]


# =============================================================================
# Time Slot Serializers
# =============================================================================


class TimeSlotSerializer(serializers.ModelSerializer):
    """Serializer for TimeSlot model."""

    arrangement_label = serializers.CharField(
        source="arrangement.arrangement_label", read_only=True
    )
    blocked_slots = serializers.SerializerMethodField()

    class Meta:
        model = TimeSlot
        fields = [
            "id",
            "arrangement",
            "arrangement_label",
            "date",
            "start_time",
            "end_time",
            "blocked_slots",
            "created_at",
        ]
        read_only_fields = ["id", "end_time", "created_at"]

    def get_blocked_slots(self, obj):
        """Get list of 1-hour slots this booking blocks."""
        return obj.get_blocked_hour_slots()


# =============================================================================
# Availability Serializers
# =============================================================================


class BookedSlotsResponseSerializer(serializers.Serializer):
    """
    Serializer for the booked slots availability response.
    
    Response format:
    {
        "arrangement_id": {
            "2026-01-19": {
                "8:00 - 9:00": "booked",
                "10:00 - 11:00": "booked"
            }
        }
    }
    """

    # This is a dynamic serializer, the actual structure is built in the view
    pass


# =============================================================================
# Booking Serializers
# =============================================================================


class BookingListSerializer(serializers.ModelSerializer):
    """Minimal serializer for booking lists."""

    service_name = serializers.CharField(
        source="service_arrangement.service.name", read_only=True
    )
    spa_center_name = serializers.CharField(source="spa_center.name", read_only=True)
    booking_date = serializers.DateField(source="time_slot.date", read_only=True)
    booking_time = serializers.TimeField(source="time_slot.start_time", read_only=True)
    end_time = serializers.TimeField(source="time_slot.end_time", read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id",
            "booking_number",
            "service_name",
            "spa_center_name",
            "booking_date",
            "booking_time",
            "end_time",
            "total_price",
            "status",
            "created_at",
        ]


class BookingSerializer(serializers.ModelSerializer):
    """Full serializer for Booking model."""

    service_arrangement_details = ServiceArrangementListSerializer(
        source="service_arrangement", read_only=True
    )
    spa_center_details = SpaCenterListSerializer(source="spa_center", read_only=True)
    add_on_services_details = AddOnServiceListSerializer(
        source="add_on_services", many=True, read_only=True
    )
    time_slot_details = TimeSlotSerializer(source="time_slot", read_only=True)
    therapist_name = serializers.SerializerMethodField()
    service_name = serializers.CharField(
        source="service_arrangement.service.name", read_only=True
    )

    class Meta:
        model = Booking
        fields = [
            "id",
            "booking_number",
            "customer",
            "spa_center",
            "spa_center_details",
            "service_arrangement",
            "service_arrangement_details",
            "service_name",
            "time_slot",
            "time_slot_details",
            "therapist",
            "therapist_name",
            "add_on_services",
            "add_on_services_details",
            "total_price",
            "customer_message",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "booking_number",
            "customer",
            "created_at",
            "updated_at",
        ]

    def get_therapist_name(self, obj):
        """Get therapist full name if assigned."""
        if obj.therapist:
            return obj.therapist.user.get_full_name()
        return None


class BookingCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a new booking.
    
    Handles:
    - Validation of arrangement availability
    - End time calculation (service + add-ons + cleanup)
    - Time slot creation
    - Booking creation
    """

    service_arrangement = serializers.UUIDField()
    date = serializers.DateField()
    start_time = serializers.TimeField()
    add_on_services = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
    )
    therapist = serializers.UUIDField(required=False, allow_null=True)
    customer_message = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_service_arrangement(self, value):
        """Validate that the arrangement exists and is active."""
        try:
            arrangement = ServiceArrangement.objects.select_related(
                "service", "spa_center"
            ).get(id=value, is_active=True)
            return arrangement
        except ServiceArrangement.DoesNotExist:
            raise serializers.ValidationError(
                "Service arrangement not found or not active."
            )

    def validate_date(self, value):
        """Validate that the date is not in the past."""
        today = timezone.now().date()
        if value < today:
            raise serializers.ValidationError("Cannot book for a past date.")
        return value

    def validate_add_on_services(self, value):
        """Validate that all add-on services exist and are active."""
        if not value:
            return []
        
        addons = AddOnService.objects.filter(id__in=value, is_active=True)
        if len(addons) != len(value):
            raise serializers.ValidationError(
                "One or more add-on services not found or not active."
            )
        return list(addons)

    def validate_therapist(self, value):
        """Validate that the therapist exists and is available."""
        if not value:
            return None
        
        try:
            therapist = TherapistProfile.objects.get(id=value, is_available=True)
            return therapist
        except TherapistProfile.DoesNotExist:
            raise serializers.ValidationError(
                "Therapist not found or not available."
            )

    def validate(self, attrs):
        """
        Cross-field validation:
        - Check if the time slot is available
        - Calculate end time
        - Check for overlapping bookings
        """
        arrangement = attrs["service_arrangement"]
        date = attrs["date"]
        start_time = attrs["start_time"]
        addons = attrs.get("add_on_services", [])

        # Calculate total add-on duration
        addon_duration = sum(addon.duration_minutes for addon in addons)

        # Calculate end time
        service_duration = arrangement.service.duration_minutes
        cleanup_duration = arrangement.cleanup_duration
        end_time = Booking.calculate_end_time(
            start_time, service_duration, addon_duration, cleanup_duration
        )

        # Check spa center operating hours
        spa_center = arrangement.spa_center
        opening_time = spa_center.default_opening_time
        closing_time = spa_center.default_closing_time

        if start_time < opening_time:
            raise serializers.ValidationError({
                "start_time": f"Spa center opens at {opening_time}."
            })

        if end_time > closing_time:
            raise serializers.ValidationError({
                "start_time": f"Booking would extend past closing time ({closing_time})."
            })

        # Check for overlapping time slots
        overlapping = TimeSlot.objects.filter(
            arrangement=arrangement,
            date=date,
        ).filter(
            # Check for any overlap
            start_time__lt=end_time,
            end_time__gt=start_time,
        ).exists()

        if overlapping:
            raise serializers.ValidationError({
                "start_time": "This time slot is not available. Please choose another time."
            })

        # Store calculated values
        attrs["end_time"] = end_time
        attrs["addon_duration"] = addon_duration
        attrs["spa_center"] = spa_center

        return attrs

    def calculate_total_price(self, arrangement, addons):
        """Calculate total price for the booking."""
        service_price = arrangement.service.current_price
        addon_price = sum(addon.price for addon in addons)
        return service_price + addon_price

    @transaction.atomic
    def create(self, validated_data):
        """Create the booking with time slot."""
        customer = self.context["request"].user
        arrangement = validated_data["service_arrangement"]
        addons = validated_data.get("add_on_services", [])

        # Create time slot
        time_slot = TimeSlot.objects.create(
            arrangement=arrangement,
            date=validated_data["date"],
            start_time=validated_data["start_time"],
            end_time=validated_data["end_time"],
        )

        # Calculate total price
        total_price = self.calculate_total_price(arrangement, addons)

        # Create booking
        booking = Booking.objects.create(
            customer=customer,
            spa_center=validated_data["spa_center"],
            service_arrangement=arrangement,
            time_slot=time_slot,
            therapist=validated_data.get("therapist"),
            total_price=total_price,
            customer_message=validated_data.get("customer_message", ""),
            status=Booking.BookingStatus.REQUESTED,
        )

        # Add add-on services
        if addons:
            booking.add_on_services.set(addons)

        return booking

    def to_representation(self, instance):
        """Return full booking details after creation."""
        return BookingSerializer(instance).data
