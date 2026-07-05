"""
Booking Serializers for Spa Center Management.

Serializers for service arrangements, time slots, availability, and booking management.
"""

from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from spacenter.models import Service, SpaCenter
from spacenter.serializers import (
    ServiceListSerializer,
    SpaCenterListSerializer,
)
from spacenter.models import ServiceArrangement

from .models import Booking, TimeSlot, ProductOrder, OrderItem, HomeServiceBooking


# =============================================================================
# Service Arrangement Serializers
# =============================================================================


class ServiceArrangementSerializer(serializers.ModelSerializer):
    """Full serializer for ServiceArrangement model."""

    spa_center_name = serializers.CharField(source="spa_center.name", read_only=True)
    service = serializers.SerializerMethodField()
    service_name = serializers.SerializerMethodField()
    service_duration = serializers.SerializerMethodField()
    room_count = serializers.SerializerMethodField()
    total_duration = serializers.SerializerMethodField()
    # Room extension (additive — no frontend breakage)
    room_info = serializers.SerializerMethodField()
    allows_all_services = serializers.SerializerMethodField()
    allows_all_add_ons = serializers.SerializerMethodField()

    class Meta:
        model = ServiceArrangement
        fields = [
            "id",
            "spa_center",
            "spa_center_name",
            "service",
            "service_name",
            "service_duration",
            "room_count",
            "arrangement_type",
            "arrangement_label",
            "cleanup_duration",
            "total_duration",
            "extra_minutes",
            "price_for_extra_minutes",
            "is_active",
            "created_at",
            "updated_at",
            # Extensions
            "room_info",
            "allows_all_services",
            "allows_all_add_ons",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_service(self, obj):
        """Legacy service field (no longer exists, return None)."""
        return None

    def get_service_name(self, obj):
        """Return legacy service name, or None for multi-service arrangements."""
        return None

    def get_service_duration(self, obj):
        """Return legacy service duration, or None for multi-service arrangements."""
        return None

    def get_room_count(self, obj):
        """Return arrangement capacity (always 1 for room-based arrangements)."""
        return obj.capacity

    def get_total_duration(self, obj):
        """Get total duration including service (if set) + cleanup."""
        return obj.cleanup_duration

    def get_allows_all_services(self, obj):
        return True

    def get_allows_all_add_ons(self, obj):
        return True

    def get_room_info(self, obj):
        """Return Room summary if a Room FK is set."""
        if obj.room:
            return {
                "id": str(obj.room.id),
                "room_id": obj.room.room_id,
                "name": obj.room.name,
            }
        return None


class ServiceArrangementListSerializer(serializers.ModelSerializer):
    """Minimal serializer for arrangement lists."""

    room_count = serializers.SerializerMethodField()
    service_name = serializers.SerializerMethodField()
    service_duration = serializers.SerializerMethodField()
    room_info = serializers.SerializerMethodField()
    allows_all_services = serializers.SerializerMethodField()
    allows_all_add_ons = serializers.SerializerMethodField()

    class Meta:
        model = ServiceArrangement
        fields = [
            "id",
            "room_count",
            "arrangement_type",
            "arrangement_label",
            "service_name",
            "service_duration",
            "cleanup_duration",
            "extra_minutes",
            "price_for_extra_minutes",
            # Extensions
            "room_info",
            "allows_all_services",
            "allows_all_add_ons",
        ]

    def get_room_count(self, obj):
        """Return arrangement capacity (always 1 for room-based arrangements)."""
        return obj.capacity

    def get_service_name(self, obj):
        return None

    def get_service_duration(self, obj):
        return None

    def get_allows_all_services(self, obj):
        return True

    def get_allows_all_add_ons(self, obj):
        return True

    def get_room_info(self, obj):
        if obj.room:
            return {
                "id": str(obj.room.id),
                "room_id": obj.room.room_id,
                "name": obj.room.name,
            }
        return None


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
        source="service.name", read_only=True
    )
    service_image = serializers.SerializerMethodField()
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
            "service_image",
            "spa_center_name",
            "booking_date",
            "booking_time",
            "end_time",
            "total_duration",
            "total_price",
            "is_loyalty_reward",
            "is_gift_card",
            "status",
            "created_at",
        ]

    def get_service_image(self, obj):
        """Get the primary image URL for the service."""
        service = obj.service
        if service:
            # Try to get primary image first
            primary_image = service.images.filter(is_primary=True).first()
            if primary_image and primary_image.image:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(primary_image.image.url)
                return primary_image.image.url
            # Fallback to first image if no primary
            first_image = service.images.first()
            if first_image and first_image.image:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(first_image.image.url)
                return first_image.image.url
        return None


class BookingSerializer(serializers.ModelSerializer):
    """Full serializer for Booking model."""

    service_arrangement_details = ServiceArrangementListSerializer(
        source="service_arrangement", read_only=True
    )
    spa_center_details = SpaCenterListSerializer(source="spa_center", read_only=True)
    time_slot_details = TimeSlotSerializer(source="time_slot", read_only=True)
    service_name = serializers.CharField(
        source="service.name", read_only=True
    )

    class Meta:
        model = Booking
        fields = [
            "id",
            "booking_number",
            "customer",
            "spa_center",
            "spa_center_details",
            "service",
            "service_name",
            "service_arrangement",
            "service_arrangement_details",
            "time_slot",
            "time_slot_details",
            "subtotal",
            "discount_amount",
            "extra_minutes",
            "price_for_extra_minutes",
            "total_duration",
            "total_price",
            "is_loyalty_reward",
            "loyalty_reward",
            "is_gift_card",
            "gift_card",
            "meta_data",
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


class BookingCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a new booking.
    
    Handles:
    - Validation of arrangement availability
    - Explicit service_arrangement_id support
    - End time calculation (service + add-ons + cleanup)
    - Time slot creation
    - Booking creation with pricing
    """
    
    # Arrangement options
    service_arrangement_id = serializers.UUIDField(required=True)
    arrangement_type = serializers.ChoiceField(choices=ServiceArrangement.ArrangementType.choices, required=False)
    
    # Core details
    service = serializers.UUIDField()
    spa_center = serializers.UUIDField()
    date = serializers.DateField()
    start_time = serializers.TimeField()
    
    customer_message = serializers.CharField(required=False, allow_blank=True, default="")
    
    # Extra time
    extra_minutes = serializers.IntegerField(
        required=False,
        default=0,
        help_text="Extra minutes to add to the service duration"
    )
    price_for_extra_minutes = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        default=0,
        help_text="Price for the extra minutes"
    )

    # Financials
    discount_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        default=0,
        help_text="Total discount amount to apply"
    )
    subtotal = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        required=False, 
        allow_null=True,
        help_text="Sum of service prices before discounts"
    )
    total_price = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        required=False, 
        allow_null=True,
        help_text="Final payable amount"
    )


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


    def validate(self, attrs):
        """
        Cross-field validation:
        - Resolve arrangement by ID (whitelist-aware, no service FK filter)
        - Validate service is allowed in arrangement
        - Validate add-ons (if any) are allowed in arrangement
        - Calculate end time
        - Check timeslot availability
        """
        service = attrs["service"]
        spa_center = attrs["spa_center"]
        date = attrs["date"]
        start_time = attrs["start_time"]

        # ------------------------------------------------------------------
        # 1. Resolve Arrangement (no service FK filter — use whitelist check)
        # ------------------------------------------------------------------
        arr_id = attrs.get("service_arrangement_id")

        try:
            selected_arrangement = (
                ServiceArrangement.objects
                .select_related("room", "spa_center")
                .get(id=arr_id, spa_center=spa_center, is_active=True)
            )
        except ServiceArrangement.DoesNotExist:
            raise serializers.ValidationError({
                "service_arrangement_id": (
                    "Arrangement not found or does not belong to the selected spa center."
                )
            })

        # ------------------------------------------------------------------
        # 2. Service whitelist check
        # ------------------------------------------------------------------
        if not selected_arrangement.is_service_allowed(service):
            raise serializers.ValidationError({
                "service_arrangement_id": (
                    "This arrangement does not support the selected service."
                )
            })

        # ------------------------------------------------------------------
        # 3. Operating hours check
        # ------------------------------------------------------------------
        opening_time = spa_center.default_opening_time
        closing_time = spa_center.default_closing_time

        if start_time < opening_time:
            raise serializers.ValidationError({
                "start_time": f"Spa center opens at {opening_time}."
            })

        service_duration = service.duration_minutes
        extra_minutes = int(attrs.get("extra_minutes", 0))
        total_duration = service_duration + extra_minutes

        # ------------------------------------------------------------------
        # 4. Calculate end time & closing-time check
        # ------------------------------------------------------------------
        cleanup_duration = selected_arrangement.cleanup_duration
        end_time = Booking.calculate_end_time(
            start_time, total_duration, 0, cleanup_duration
        )

        if end_time > closing_time:
            raise serializers.ValidationError({
                "start_time": "Booking exceeds closing time."
            })

        # ------------------------------------------------------------------
        # 5. Availability check — use arr.capacity (supports both Room & legacy)
        # ------------------------------------------------------------------
        overlapping_count = TimeSlot.objects.filter(
            arrangement=selected_arrangement,
            date=date,
            start_time__lt=end_time,
            end_time__gt=start_time,
        ).count()

        if overlapping_count >= selected_arrangement.capacity:
            raise serializers.ValidationError({
                "start_time": "Selected arrangement has no available space for this time."
            })

        # Store calculated values for create()
        attrs["service_arrangement"] = selected_arrangement
        attrs["end_time"] = end_time

        # ------------------------------------------------------------------
        # 6. Calculate Financials
        # ------------------------------------------------------------------
        from decimal import Decimal
        from spacenter.models import ServiceArrangementPrice
        arr_price_obj = ServiceArrangementPrice.objects.filter(
            service=service,
            service_arrangement=selected_arrangement
        ).first()
        base_price = arr_price_obj.price if arr_price_obj else service.base_price
        price_for_extra = Decimal(str(attrs.get("price_for_extra_minutes", 0)))
        attrs["calculated_subtotal"] = base_price + price_for_extra

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        """Create the booking with time slot and pricing."""
        request = self.context.get("request")
        customer = request.user
        
        arrangement = validated_data["service_arrangement"]
        
        # Create time slot
        time_slot = TimeSlot.objects.create(
            arrangement=arrangement,
            date=validated_data["date"],
            start_time=validated_data["start_time"],
            end_time=validated_data["end_time"],
        )
        
        # Financials
        from decimal import Decimal
        extra_minutes = int(validated_data.get("extra_minutes", 0))
        price_for_extra = Decimal(str(validated_data.get("price_for_extra_minutes", 0)))
        discount_amount = Decimal(str(validated_data.get("discount_amount", 0)))
        
        # Total duration = service duration + extra minutes
        service = validated_data["service"]
        total_duration = service.duration_minutes + extra_minutes
        
        subtotal = validated_data.get("subtotal") or validated_data["calculated_subtotal"]
        
        # Use client-provided total_price if available, else calculate: subtotal - discount
        final_payable = validated_data.get("total_price")
        if final_payable is None:
            from spacenter.models import ServiceArrangementPrice
            arr_price_obj = ServiceArrangementPrice.objects.filter(
                service=service,
                service_arrangement=arrangement
            ).first()
            if arr_price_obj and arr_price_obj.discounted_price:
                discount_amount = arr_price_obj.price - arr_price_obj.discounted_price
                final_payable = arr_price_obj.discounted_price + price_for_extra
            else:
                final_payable = subtotal - discount_amount
            if final_payable < 0:
                final_payable = Decimal("0.00")
        
        status_val = Booking.BookingStatus.REQUESTED

        # Build comprehensive meta_data snapshot
        service = validated_data["service"]
        spa_center_obj = validated_data["spa_center"]
        
        meta_data = {
            "service": {
                "id": str(service.id),
                "name": service.name,
                "duration_minutes": service.duration_minutes,
                "currency": service.currency,
            },
            "spa_center": {
                "id": str(spa_center_obj.id),
                "name": spa_center_obj.name,
                "city": spa_center_obj.city.name if spa_center_obj.city else None,
                "country": spa_center_obj.country.name if spa_center_obj.country else None,
                "address": spa_center_obj.address or None,
            },
            "schedule": {
                "date": str(validated_data["date"]),
                "start_time": str(validated_data["start_time"]),
                "end_time": str(validated_data["end_time"]),
            },
            "arrangement": {
                "id": str(arrangement.id),
                "type": arrangement.arrangement_type,
                "capacity": arrangement.capacity,
                "label": arrangement.arrangement_label,
                "cleanup_duration": arrangement.cleanup_duration,
                # Room info if linked
                "room": (
                    {
                        "id": str(arrangement.room.id),
                        "room_id": arrangement.room.room_id,
                        "name": arrangement.room.name,
                    }
                    if arrangement.room else None
                ),
            },
            "pricing": {
                "subtotal": str(subtotal),
                "discount_amount": str(discount_amount),
                "extra_minutes": extra_minutes,
                "price_for_extra_minutes": str(price_for_extra),
                "total_price": str(final_payable),
            },
        }

        # Create booking
        booking = Booking.objects.create(
            customer=customer,
            spa_center=spa_center_obj,
            service=service,
            service_arrangement=arrangement,
            time_slot=time_slot,
            subtotal=subtotal,
            discount_amount=discount_amount,
            extra_minutes=extra_minutes,
            price_for_extra_minutes=price_for_extra,
            total_duration=total_duration,
            total_price=final_payable,
            customer_message=validated_data.get("customer_message", ""),
            status=status_val,
            meta_data=meta_data,
        )

        return booking

    def to_representation(self, instance):
        """Return full booking details after creation."""
        return BookingSerializer(instance).data

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
            "delivery_charge",
            "final_amount",
            "currency",
            "shipping_address",
            "contact_number",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class CreateProductOrderSerializer(serializers.Serializer):
    """
    Serializer for creating a new product order.
    Accepts:
    - items: list of {product_id, quantity}
    - shipping_address: delivery address
    - contact_number: phone number of the delivery recipient
    - delivery_charge: optional delivery fee
    - subtotal: optional (sum of item prices)
    - total_amount: optional (final amount to be paid)
    """
    
    items = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField()),
        allow_empty=False
    )
    shipping_address = serializers.CharField(
        required=True,
        help_text="Delivery address for the order"
    )
    contact_number = serializers.CharField(
        required=True,
        max_length=20,
        help_text="Phone number of the person receiving the delivery"
    )
    delivery_charge = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        default=0,
        help_text="Delivery fee to add to the order"
    )
    subtotal = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        required=False, 
        allow_null=True,
        help_text="Sum of item prices (optional, for client-side cross-check)"
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


# =============================================================================
# Home Service Booking Serializers
# =============================================================================


class HomeServiceBookingListSerializer(serializers.ModelSerializer):
    """Minimal serializer for home service booking lists."""

    home_service_name = serializers.CharField(source="home_service.name", read_only=True)
    home_service_image = serializers.SerializerMethodField()

    class Meta:
        model = HomeServiceBooking
        fields = [
            "id",
            "booking_number",
            "home_service",
            "home_service_name",
            "home_service_image",
            "date",
            "time",
            "total_duration",
            "total_price",
            "home_location",
            "contact_number",
            "status",
            "created_at",
        ]

    def get_home_service_image(self, obj):
        """Get the image URL for the home service."""
        if obj.home_service and obj.home_service.image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.home_service.image.url)
            return obj.home_service.image.url
        return None


class HomeServiceBookingSerializer(serializers.ModelSerializer):
    """Full serializer for HomeServiceBooking model."""

    home_service_name = serializers.CharField(source="home_service.name", read_only=True)
    home_service_image = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = HomeServiceBooking
        fields = [
            "id",
            "booking_number",
            "customer",
            "home_service",
            "home_service_name",
            "home_service_image",
            "date",
            "time",
            "subtotal",
            "discount_amount",
            "extra_minutes",
            "price_for_extra_minutes",
            "total_duration",
            "total_price",
            "home_location",
            "contact_number",
            "customer_message",
            "staff_notes",
            "status",
            "status_display",
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

    def get_home_service_image(self, obj):
        """Get the image URL for the home service."""
        if obj.home_service and obj.home_service.image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.home_service.image.url)
            return obj.home_service.image.url
        return None


class HomeServiceBookingCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a new home service booking.

    Handles:
    - Validation of home service existence and active status
    - Date validation (not in the past)
    - Booking creation with pricing
    """

    from spacenter.models import HomeService as _HomeService  # type: ignore

    home_service = serializers.UUIDField()
    date = serializers.DateField()
    time = serializers.TimeField()

    # Pricing
    subtotal = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Sum of service prices before discounts",
    )
    discount_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        default=0,
        help_text="Total discount amount to apply",
    )
    extra_minutes = serializers.IntegerField(
        required=False,
        default=0,
        help_text="Extra minutes to add to the service duration",
    )
    price_for_extra_minutes = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        default=0,
        help_text="Price for the extra minutes",
    )
    total_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Final payable amount",
    )

    # Home-specific
    home_location = serializers.CharField(help_text="Full address / location for the service")
    contact_number = serializers.CharField(max_length=20, help_text="Phone number for the booking")

    customer_message = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_home_service(self, value):
        """Validate that the home service exists and is active."""
        from spacenter.models import HomeService
        try:
            service = HomeService.objects.get(id=value, is_active=True)
            return service
        except HomeService.DoesNotExist:
            raise serializers.ValidationError("Home service not found or not active.")

    def validate_date(self, value):
        """Validate that the date is not in the past."""
        from django.utils import timezone
        today = timezone.now().date()
        if value < today:
            raise serializers.ValidationError("Cannot book for a past date.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        """Create the home service booking."""
        from decimal import Decimal

        request = self.context.get("request")
        customer = request.user

        home_service = validated_data["home_service"]
        extra_minutes = int(validated_data.get("extra_minutes", 0))
        price_for_extra = Decimal(str(validated_data.get("price_for_extra_minutes", 0)))
        discount_amount = Decimal(str(validated_data.get("discount_amount", 0)))

        # Total duration = service duration + extra minutes
        total_duration = home_service.duration_minutes + extra_minutes

        # Subtotal = service current price + price for extra minutes
        calculated_subtotal = home_service.current_price + price_for_extra
        subtotal = validated_data.get("subtotal") or calculated_subtotal

        # Final price: use client-provided or calculate
        final_price = validated_data.get("total_price")
        if final_price is None:
            final_price = subtotal - discount_amount
            if final_price < Decimal("0.00"):
                final_price = Decimal("0.00")

        booking = HomeServiceBooking.objects.create(
            customer=customer,
            home_service=home_service,
            date=validated_data["date"],
            time=validated_data["time"],
            subtotal=subtotal,
            discount_amount=discount_amount,
            extra_minutes=extra_minutes,
            price_for_extra_minutes=price_for_extra,
            total_duration=total_duration,
            total_price=final_price,
            home_location=validated_data["home_location"],
            contact_number=validated_data["contact_number"],
            customer_message=validated_data.get("customer_message", ""),
            status=HomeServiceBooking.BookingStatus.REQUESTED,
        )

        return booking

    def to_representation(self, instance):
        """Return full booking details after creation."""
        return HomeServiceBookingSerializer(instance, context=self.context).data
