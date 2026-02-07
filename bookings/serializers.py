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

from .models import Booking, ServiceArrangement, TimeSlot, ProductOrder, OrderItem


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

    arrangement_type = serializers.ChoiceField(choices=ServiceArrangement.ArrangementType.choices)
    service = serializers.UUIDField()
    spa_center = serializers.UUIDField()
    date = serializers.DateField()
    start_time = serializers.TimeField()
    add_on_services = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
    )
    therapist = serializers.UUIDField(required=False, allow_null=True)
    customer_message = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_service(self, value):
        """Validate that the service exists and is active."""
        try:
            service = Service.objects.get(id=value, is_active=True)
            return service
        except Service.DoesNotExist:
            raise serializers.ValidationError("Service not found or not active.")

    def validate_spa_center(self, value):
        """Validate that the spa center exists and is active."""
        try:
            spa_center = SpaCenter.objects.get(id=value, is_active=True)
            return spa_center
        except SpaCenter.DoesNotExist:
            raise serializers.ValidationError("Spa center not found or not active.")

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
        - Find available arrangement
        - Calculate end time
        - Check spa center operating hours
        """
        service = attrs["service"]
        spa_center = attrs["spa_center"]
        arrangement_type = attrs["arrangement_type"]
        date = attrs["date"]
        start_time = attrs["start_time"]
        addons = attrs.get("add_on_services", [])

        # Calculate total add-on duration
        addon_duration = sum(addon.duration_minutes for addon in addons)

        # Calculate end time based on service duration and potential additions
        service_duration = service.duration_minutes
        
        # We need a potential end_time to check availability
        # We'll use a default cleanup of 15 if we can't get it from arrangement yet
        # but actually each arrangement has its own cleanup_duration.
        # Let's find arrangements first, then check availability for each.
        
        arrangements = ServiceArrangement.objects.filter(
            service=service,
            spa_center=spa_center,
            arrangement_type=arrangement_type,
            is_active=True
        )

        if not arrangements.exists():
            raise serializers.ValidationError({
                "arrangement_type": "No arrangements of this type available for the selected service at this spa center."
            })

        # Check spa center operating hours
        opening_time = spa_center.default_opening_time
        closing_time = spa_center.default_closing_time

        if start_time < opening_time:
            raise serializers.ValidationError({
                "start_time": f"Spa center opens at {opening_time}."
            })

        selected_arrangement = None
        final_end_time = None

        for arrangement in arrangements:
            cleanup_duration = arrangement.cleanup_duration
            end_time = Booking.calculate_end_time(
                start_time, service_duration, addon_duration, cleanup_duration
            )

            if end_time > closing_time:
                continue # This arrangement's cleanup might push it past closing, though unlikely if others don't

            # Check for overlapping time slots for THIS arrangement
            overlapping = TimeSlot.objects.filter(
                arrangement=arrangement,
                date=date,
                start_time__lt=end_time,
                end_time__gt=start_time,
            ).exists()

            if not overlapping:
                selected_arrangement = arrangement
                final_end_time = end_time
                break

        if not selected_arrangement:
            raise serializers.ValidationError({
                "start_time": "No available arrangements found for this time slot."
            })

        # Store calculated values
        attrs["service_arrangement"] = selected_arrangement
        attrs["end_time"] = final_end_time
        attrs["addon_duration"] = addon_duration

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

# =============================================================================
# Product Order Serializers
# =============================================================================

class OrderItemSerializer(serializers.ModelSerializer):
    """
    Serializer for Order Items.
    """
    product_name = serializers.CharField(source="product.product.name", read_only=True)
    product_image = serializers.ImageField(source="product.product.image", read_only=True)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "product_name",
            "product_image",
            "quantity",
            "unit_price",
            "total_price",
        ]


class ProductOrderSerializer(serializers.ModelSerializer):
    """
    Serializer for Product Order details.
    """
    items = OrderItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    payment_status_display = serializers.CharField(source="get_payment_status_display", read_only=True)
    voucher_codes = serializers.SerializerMethodField()
    gift_card_codes = serializers.SerializerMethodField()

    class Meta:
        model = ProductOrder
        fields = [
            "id",
            "order_number",
            "user",
            "status",
            "status_display",
            "payment_status",
            "payment_status_display",
            "total_amount",
            "discount_amount",
            "final_amount",
            "currency",
            "payment_method",
            "items",
            "voucher_codes",
            "gift_card_codes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_voucher_codes(self, obj):
        return [v.code for v in obj.vouchers.all()]

    def get_gift_card_codes(self, obj):
        return [g.code for g in obj.gift_cards.all()]


class CreateProductOrderSerializer(serializers.Serializer):
    """
    Serializer for creating a new product order.
    Accepts:
    - items: list of {product_id, quantity}
    - voucher_id: optional
    - gift_card_id: optional (single for now as per requirements)
    - subtotal: optional (sum of item prices before discounts)
    - total_amount: optional (final amount to be paid)
    """
    
    items = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField()),
        allow_empty=False
    )
    voucher_id = serializers.IntegerField(required=False, allow_null=True)
    gift_card_id = serializers.IntegerField(required=False, allow_null=True)
    payment_method = serializers.CharField(required=True)
    subtotal = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        required=False, 
        allow_null=True,
        help_text="Sum of item prices before discounts (optional, for client-side cross-check)"
    )
    total_amount = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        required=False, 
        allow_null=True,
        help_text="Final payable amount (optional, for client-side cross-check)"
    )
    
    # Note: user is taken from request.user
    # Status is set to default (PENDING)
    
    def validate_items(self, value):
        from spacenter.models import SpaProduct
        validated_items = []
        for item in value:
            product_id = item.get("product_id")
            quantity = item.get("quantity")
            
            if not product_id or not quantity:
                raise serializers.ValidationError("Each item must have 'product_id' and 'quantity'.")
            
            try:
                quantity = int(quantity)
                if quantity < 1:
                    raise serializers.ValidationError("Quantity must be at least 1.")
            except ValueError:
                raise serializers.ValidationError("Quantity must be an integer.")

            try:
                product = SpaProduct.objects.get(id=product_id)
                if product.available_quantity < quantity:
                    raise serializers.ValidationError(
                        f"Not enough stock for {product.product.name}. Available: {product.available_quantity}"
                    )
                validated_items.append({"product": product, "quantity": quantity})
            except SpaProduct.DoesNotExist:
                raise serializers.ValidationError(f"Product with ID {product_id} not found.")
        
        return validated_items

    def validate(self, attrs):
        # Additional validations if needed
        return attrs
