"""
Booking Serializers for Spa Center Management.

Serializers for service arrangements, time slots, availability, and booking management.
"""

from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from spacenter.models import AddOnService, Service, SpaCenter
from spacenter.serializers import (
    AddOnServiceListSerializer,
    ServiceListSerializer,
    SpaCenterListSerializer,
)
from spacenter.models import ServiceArrangement

from .models import Booking, TimeSlot, ProductOrder, OrderItem


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
            "extra_minutes",
            "price_for_extra_minutes",
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
            "extra_minutes",
            "price_for_extra_minutes",
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
            "total_price",
            "status",
            "created_at",
        ]

    def get_service_image(self, obj):
        """Get the primary image URL for the service."""
        if obj.service_arrangement and obj.service_arrangement.service:
            service = obj.service_arrangement.service
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
    add_on_services_details = AddOnServiceListSerializer(
        source="add_on_services", many=True, read_only=True
    )
    time_slot_details = TimeSlotSerializer(source="time_slot", read_only=True)
    service_name = serializers.CharField(
        source="service_arrangement.service.name", read_only=True
    )
    voucher_usages_details = serializers.SerializerMethodField()
    gift_card_transactions_details = serializers.SerializerMethodField()

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
            "add_on_services",
            "add_on_services_details",
            "subtotal",
            "discount_amount",
            "total_price",
            "voucher_usages",
            "voucher_usages_details",
            "gift_card_transactions",
            "gift_card_transactions_details",
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

    def get_voucher_usages_details(self, obj):
        """Get detailed voucher usage information."""
        usages = obj.voucher_usages.all()
        return [
            {
                "id": str(usage.id),
                "voucher_code": usage.voucher.code,
                "voucher_name": usage.voucher.name,
                "discount_type": usage.voucher.discount_type,
                "original_amount": str(usage.original_amount),
                "discount_amount": str(usage.discount_amount),
                "final_amount": str(usage.final_amount),
                "used_at": usage.used_at.isoformat() if usage.used_at else None,
            }
            for usage in usages
        ]

    def get_gift_card_transactions_details(self, obj):
        """Get detailed gift card transaction information."""
        transactions = obj.gift_card_transactions.all()
        return [
            {
                "id": str(txn.id),
                "gift_card_code": txn.gift_card.code,
                "transaction_type": txn.transaction_type,
                "amount": str(txn.amount),
                "balance_after": str(txn.balance_after),
                "created_at": txn.created_at.isoformat() if txn.created_at else None,
            }
            for txn in transactions
        ]


class BookingCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a new booking.
    
    Handles:
    - Validation of arrangement availability
    - Explicit service_arrangement_id support
    - Voucher and Gift Card application
    - End time calculation (service + add-ons + cleanup)
    - Time slot creation
    - Booking creation with financial records
    """
    
    # Arrangement options
    service_arrangement_id = serializers.UUIDField(required=True)
    arrangement_type = serializers.ChoiceField(choices=ServiceArrangement.ArrangementType.choices, required=False)
    
    # Core details
    service = serializers.UUIDField()
    spa_center = serializers.UUIDField()
    date = serializers.DateField()
    start_time = serializers.TimeField()
    
    # Extras
    add_on_services = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
    )
    customer_message = serializers.CharField(required=False, allow_blank=True, default="")
    
    # Financials & Promotions
    voucher_ids = serializers.ListField(
        child=serializers.CharField(),
        required=False, 
        default=list
    )
    gift_card_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False, 
        default=list
    )
    subtotal = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        required=False, 
        allow_null=True,
        help_text="Sum of service prices before discounts"
    )
    discount = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        required=False, 
        allow_null=True,
        default=0,
        help_text="Total discount amount (vouchers + other)"
    )
    total_price = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        required=False, 
        allow_null=True,
        help_text="Final payable amount after discounts"    
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

    def validate(self, attrs):
        """
        Cross-field validation:
        - Resolve arrangement (id vs type search)
        - Calculate end time
        - Check availability
        - Validate Vouchers & Gift Cards
        """
        service = attrs["service"]
        spa_center = attrs["spa_center"]
        date = attrs["date"]
        start_time = attrs["start_time"]
        addons = attrs.get("add_on_services", [])
        
        request = self.context.get("request")
        user = request.user
        
        # 1. Resolve Arrangement
        selected_arrangement = None
        
        arr_id = attrs.get("service_arrangement_id")
        
        try:
            selected_arrangement = ServiceArrangement.objects.get(
                id=arr_id, 
                service=service, 
                spa_center=spa_center,
                is_active=True
            )
        except ServiceArrangement.DoesNotExist:
            raise serializers.ValidationError({
                "service_arrangement_id": "Arrangement not found or does not match service/spa center."
            })

        # Check spa center operating hours
        opening_time = spa_center.default_opening_time
        closing_time = spa_center.default_closing_time

        if start_time < opening_time:
            raise serializers.ValidationError({
                "start_time": f"Spa center opens at {opening_time}."
            })

        # Calculate durations
        addon_duration = sum(addon.duration_minutes for addon in addons)
        service_duration = service.duration_minutes
        
        # 2. Check Availability
        final_end_time = None
        
        cleanup_duration = selected_arrangement.cleanup_duration
        end_time = Booking.calculate_end_time(
            start_time, service_duration, addon_duration, cleanup_duration
        )
        
        if end_time > closing_time:
             raise serializers.ValidationError({"start_time": "Booking exceeds closing time."})

        overlapping = TimeSlot.objects.filter(
            arrangement=selected_arrangement,
            date=date,
            start_time__lt=end_time,
            end_time__gt=start_time,
        ).exists()
        
        if overlapping:
            raise serializers.ValidationError({"start_time": "Selected arrangement is booked for this time."})
        
        final_end_time = end_time

        # Store calculated values
        attrs["service_arrangement"] = selected_arrangement
        attrs["end_time"] = final_end_time
        attrs["addon_duration"] = addon_duration
        
        # 3. Calculate Financials (Pre-check)
        base_price = service.current_price
        addon_price = sum(addon.price for addon in addons)
        calculated_subtotal = base_price + addon_price
        
        # Validate vouchers
        voucher_ids = attrs.get("voucher_ids", [])
        valid_vouchers = []
        discount_amount = 0
        
        from promotions.models import Voucher, GiftCard
        
        # We process vouchers one by one (if multiple allowed in future, currently usually 1)
        # Assuming list input for future proofing but logic handles accumulated discount
        
        current_payable = calculated_subtotal
        
        if voucher_ids:
             # Fetch unique vouchers to avoid double usage in same request
             # Assuming codes or IDs? Serializer says CharField (implies code or ID). 
             # Let's assume ID if UUID, or Code if string. The model has UUID PK.
             # Client likely sends IDs if they picked from a list, or codes if typed.
             # ImplementationPlan said IDs. Let's try to fetch by ID.
             
             # Actually input says voucher_ids (List[str]).
             for v_input in voucher_ids:
                 # Try ID first, then code
                 voucher = None
                 try:
                     # Check if uuid
                     import uuid
                     uuid_obj = uuid.UUID(str(v_input))
                     voucher = Voucher.objects.get(id=uuid_obj)
                 except (ValueError, Voucher.DoesNotExist):
                     try:
                        voucher = Voucher.objects.get(code=v_input)
                     except Voucher.DoesNotExist:
                         raise serializers.ValidationError(f"Voucher '{v_input}' not found.")
                 
                 # Check validity
                 is_valid, msg = voucher.can_be_used_by(user, calculated_subtotal)
                 if not is_valid:
                     raise serializers.ValidationError(f"Voucher '{voucher.code}': {msg}")
                 
                 # Calculate discount
                 disc = voucher.calculate_discount(current_payable)
                 discount_amount += disc
                 current_payable = max(0, current_payable - disc)
                 valid_vouchers.append(voucher)
        
        attrs["valid_vouchers"] = valid_vouchers
        attrs["calculated_discount"] = discount_amount
        attrs["calculated_subtotal"] = calculated_subtotal
        
        # Validate Gift Cards
        gift_card_ids = attrs.get("gift_card_ids", [])
        valid_gift_cards = []
        gift_card_usage = {} # map id -> amount to use
        
        if gift_card_ids:
             remaining_to_pay = current_payable
             
             for gc_id in gift_card_ids:
                 if remaining_to_pay <= 0:
                     break # No need for more gift cards
                     
                 try:
                     gc = GiftCard.objects.get(id=gc_id)
                 except GiftCard.DoesNotExist:
                     raise serializers.ValidationError(f"Gift card {gc_id} not found.")
                 
                 # Check access - MUST be owner? Or just have code? 
                 # Usually owner needs to be the user for security in app,
                 # unless we just validate code (but here we have IDs).
                 if gc.owner != user and gc.purchased_by != user:
                      # If strict ownership is required. 
                      # Let's assume ownership required as per typical app flow
                      raise serializers.ValidationError(f"Gift card {gc_id} does not belong to you.")
                 
                 if not gc.is_valid:
                      raise serializers.ValidationError(f"Gift card {gc_id} is invalid or empty.")
                 
                 to_use = min(remaining_to_pay, gc.current_balance)
                 gift_card_usage[gc.id] = to_use
                 remaining_to_pay -= to_use
                 valid_gift_cards.append(gc)
                 
        attrs["valid_gift_cards"] = valid_gift_cards
        attrs["gift_card_usage"] = gift_card_usage       

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        """Create the booking with time slot and financials."""
        request = self.context.get("request")
        customer = request.user
        
        arrangement = validated_data["service_arrangement"]
        addons = validated_data.get("add_on_services", [])
        
        # Create time slot
        time_slot = TimeSlot.objects.create(
            arrangement=arrangement,
            date=validated_data["date"],
            start_time=validated_data["start_time"],
            end_time=validated_data["end_time"],
        )
        
        # Financials - use client-provided values if available, else calculated
        subtotal = validated_data.get("subtotal") or validated_data["calculated_subtotal"]
        discount_amount = validated_data.get("discount") if validated_data.get("discount") is not None else validated_data["calculated_discount"]
        
        # Apply Gift Cards
        valid_gift_cards = validated_data["valid_gift_cards"]
        gift_card_usage = validated_data["gift_card_usage"]
        gift_card_total_deducted = 0
        
        # We need the booking ID for transaction reference, but booking needs price.
        # We'll calculate final price first.
        
        price_after_discount = max(0, subtotal - discount_amount)
        # Gift cards are payment methods, so they don't reduce "total_price" (invoice amount),
        # but they pay for it. 
        # HOWEVER, the requirements often treat GC as discount/payment. 
        # In `ProductOrder` logic: `final_amount` was after GC. 
        # Let's follow the Booking model fields. 
        # `total_price` help text says "Final payable amount after discounts".
        # This usually means Price - Vouchers. 
        # Gift Cards are usually treated as payment (like cash).
        # But if total_price is what the user has to pay via Gateway, then GC reduces it.
        # Let's assume total_price is the *outstanding* amount to be paid.
        
        for gc in valid_gift_cards:
            amount_to_use = gift_card_usage.get(gc.id, 0)
            gift_card_total_deducted += amount_to_use
        
        # Use client-provided total_price if available, else calculate
        final_payable = validated_data.get("total_price")
        if final_payable is None:
            final_payable = max(0, price_after_discount - gift_card_total_deducted)
        
        status_val = Booking.BookingStatus.REQUESTED
        if final_payable == 0:
            status_val = Booking.BookingStatus.PAYMENT_SUCCESS

        # Create booking
        booking = Booking.objects.create(
            customer=customer,
            spa_center=validated_data["spa_center"],
            service_arrangement=arrangement,
            time_slot=time_slot,
            subtotal=subtotal,
            discount_amount=discount_amount,
            total_price=final_payable,
            customer_message=validated_data.get("customer_message", ""),
            status=status_val,
        )

        # Add relations
        if addons:
            booking.add_on_services.set(addons)
            
        # Record voucher usages and link to booking
        if validated_data["valid_vouchers"]:
            from promotions.models import VoucherUsage
            voucher_usage_records = []
            for v in validated_data["valid_vouchers"]:
                usage = VoucherUsage.objects.create(
                    voucher=v,
                    user=customer,
                    order_reference=str(booking.id),
                    order_type="service_booking",
                    original_amount=subtotal,
                    discount_amount=discount_amount,
                    final_amount=price_after_discount
                )
                voucher_usage_records.append(usage)
            booking.voucher_usages.set(voucher_usage_records)

        # Redeem gift cards and link transactions to booking
        if valid_gift_cards:
            gc_transaction_records = []
            for gc in valid_gift_cards:
                amount = gift_card_usage.get(gc.id, 0)
                success, redeemed_amount, error = gc.redeem(
                    amount=amount,
                    user=customer,
                    order_reference=str(booking.id),
                    order_type="service_booking"
                )
                if success:
                    # Get the most recent transaction for this gift card (the one just created)
                    transaction = gc.transactions.order_by('-created_at').first()
                    if transaction:
                        gc_transaction_records.append(transaction)
            booking.gift_card_transactions.set(gc_transaction_records)

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
    - voucher_ids: optional list of voucher IDs (UUIDs)
    - gift_card_ids: optional list of gift card IDs (UUIDs)
    - subtotal: optional (sum of item prices before discounts)
    - discount: optional (total discount amount)
    - total_amount: optional (final amount to be paid)
    """
    
    items = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField()),
        allow_empty=False
    )
    voucher_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
        help_text="List of voucher IDs (UUIDs) to apply"
    )
    gift_card_ids = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text="List of gift card IDs to use for payment"
    )
    payment_method = serializers.CharField(required=True)
    subtotal = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        required=False, 
        allow_null=True,
        help_text="Sum of item prices before discounts (optional, for client-side cross-check)"
    )
    discount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
        default=0,
        help_text="Total discount amount (optional)"
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
