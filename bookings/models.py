"""
Booking Models for Spa Center Management.

Efficient design for handling time slot availability and high-volume requests.
Includes time slots and booking management.
ServiceArrangement is now in spacenter app.
"""

import uuid
from datetime import datetime, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _



class TimeSlot(models.Model):
    """
    Records booked time slots for service arrangements.
    
    Each time slot represents a blocked period for a specific arrangement.
    The end_time is auto-calculated based on service duration + add-ons + cleanup.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)


    arrangement = models.ForeignKey(
        "spacenter.ServiceArrangement",
        on_delete=models.CASCADE,
        related_name="time_slots",
        verbose_name=_("service arrangement"),
    )

    # Time slot details
    date = models.DateField(_("date"), db_index=True)
    start_time = models.TimeField(_("start time"))
    end_time = models.TimeField(_("end time"))  # Auto-calculated on booking creation

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("time slot")
        verbose_name_plural = _("time slots")
        ordering = ["date", "start_time"]
        indexes = [
            models.Index(fields=["arrangement", "date", "start_time"]),
            models.Index(fields=["date", "start_time", "end_time"]),
        ]

    def __str__(self):
        return f"{self.arrangement.service.name} - {self.date} {self.start_time}-{self.end_time}"

    def get_blocked_hour_slots(self):
        """
        Returns a list of standard 1-hour slots that this time slot blocks.
        
        For example, if a booking is from 10:00 to 11:30, it blocks:
        - 10:00-11:00
        - 11:00-12:00 (partial overlap)
        """
        blocked_slots = []
        current_hour = self.start_time.hour
        end_hour = self.end_time.hour
        
        # If end_time has minutes, it extends into the next hour
        if self.end_time.minute > 0:
            end_hour += 1
        
        for hour in range(current_hour, end_hour):
            slot_start = f"{hour:02d}:00"
            slot_end = f"{hour + 1:02d}:00"
            blocked_slots.append(f"{slot_start} - {slot_end}")
        
        return blocked_slots


def generate_booking_number():
    """Generate a unique booking reference number."""
    import random
    import string
    from django.utils import timezone
    
    date_part = timezone.now().strftime("%Y%m%d")
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"BK-{date_part}-{random_part}"


class Booking(models.Model):
    """
    Booking model for spa services.

    Stores all booking information with status tracking.
    Optimized for high-volume concurrent requests.
    """

    class BookingStatus(models.TextChoices):
        REQUESTED = "requested", _("Requested")
        PAYMENT_PENDING = "payment_pending", _("Payment Pending")
        PAYMENT_SUCCESS = "payment_success", _("Payment Success")
        CONFIRMED = "confirmed", _("Confirmed")
        ON_HOLD = "on_hold", _("On Hold")
        CANCELED = "canceled", _("Canceled")
        COMPLETED = "completed", _("Completed")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Booking reference number (human-readable)
    booking_number = models.CharField(
        _("booking number"),
        max_length=25,
        unique=True,
        db_index=True,
        default=generate_booking_number,
    )

    # Customer information
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="bookings",
        verbose_name=_("customer"),
    )

    # Service and location details
    spa_center = models.ForeignKey(
        "spacenter.SpaCenter",
        on_delete=models.PROTECT,
        related_name="bookings",
        verbose_name=_("spa center"),
    )
    service_arrangement = models.ForeignKey(
        "spacenter.ServiceArrangement",
        on_delete=models.PROTECT,
        related_name="bookings",
        verbose_name=_("service arrangement"),
    )

    # Time slot - OneToOne since each booking has exactly one time slot
    time_slot = models.OneToOneField(
        TimeSlot,
        on_delete=models.PROTECT,
        related_name="booking",
        verbose_name=_("time slot"),
    )

    # Therapist assignment (optional)
    therapist = models.ForeignKey(
        "spacenter.TherapistProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bookings",
        verbose_name=_("therapist"),
    )

    # Add-on services - ManyToMany for multiple add-ons
    add_on_services = models.ManyToManyField(
        "spacenter.AddOnService",
        blank=True,
        related_name="bookings",
        verbose_name=_("add-on services"),
    )

    # Pricing
    subtotal = models.DecimalField(
        _("subtotal"),
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text=_("Sum of service prices before discounts"),
    )
    
    discount_amount = models.DecimalField(
        _("discount amount"),
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text=_("Total discount applied (vouchers + other)"),
    )
    
    total_price = models.DecimalField(
        _("total price"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_("Final payable amount after discounts"),
    )

    # Promotions
    vouchers = models.ManyToManyField(
        "promotions.Voucher",
        blank=True,
        related_name="bookings",
        verbose_name=_("vouchers"),
    )
    
    gift_cards = models.ManyToManyField(
        "promotions.GiftCard",
        blank=True,
        related_name="bookings",
        verbose_name=_("gift cards"),
    )

    # Customer message/notes
    customer_message = models.TextField(
        _("customer message"),
        blank=True,
        help_text=_("Special requests or notes from customer"),
    )

    # Internal notes (for staff)
    staff_notes = models.TextField(
        _("staff notes"),
        blank=True,
        help_text=_("Internal notes for staff"),
    )

    # Status tracking
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=BookingStatus.choices,
        default=BookingStatus.REQUESTED,
        db_index=True,
    )

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("booking")
        verbose_name_plural = _("bookings")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["customer", "status"]),
            models.Index(fields=["spa_center", "status"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.booking_number} - {self.service_arrangement.service.name}"

    @property
    def service(self):
        """Get the service from the arrangement."""
        return self.service_arrangement.service

    @property
    def booking_date(self):
        """Get the booking date from time slot."""
        return self.time_slot.date

    @property
    def booking_time(self):
        """Get the start time from time slot."""
        return self.time_slot.start_time

    @classmethod
    def calculate_end_time(cls, start_time, service_duration, addon_duration=0, cleanup_duration=15):
        """
        Calculate the end time for a booking.
        
        Args:
            start_time: datetime.time object
            service_duration: int, duration in minutes
            addon_duration: int, total add-on services duration in minutes
            cleanup_duration: int, cleanup buffer in minutes (default 15)
        
        Returns:
            datetime.time object representing the end time
        """
        # Convert start_time to datetime for calculation
        start_dt = datetime.combine(datetime.today(), start_time)
        try:
            total_duration = int(service_duration) + int(addon_duration) + int(cleanup_duration)
            end_dt = start_dt + timedelta(minutes=total_duration)
            return end_dt.time()
        except (ValueError, TypeError):
             return start_time 

# =============================================================================
# Product Order Models
# =============================================================================

def generate_order_number():
    """Generate a unique order reference number."""
    import random
    import string
    
    date_part = datetime.now().strftime("%Y%m%d")
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"ORD-{date_part}-{random_part}"


class ProductOrder(models.Model):
    """
    Product order for spa products.
    """
    
    class OrderStatus(models.TextChoices):
        PENDING = "pending", _("Pending")
        PROCESSING = "processing", _("Processing")
        SHIPPED = "shipped", _("Shipped")
        COMPLETED = "completed", _("Completed")
        CANCELED = "canceled", _("Canceled")
        REFUNDED = "refunded", _("Refunded")

    class PaymentStatus(models.TextChoices):
        PENDING = "pending", _("Pending")
        PAID = "paid", _("Paid")
        FAILED = "failed", _("Failed")
        REFUNDED = "refunded", _("Refunded")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="product_orders",
        verbose_name=_("user"),
    )

    order_number = models.CharField(
        _("order number"),
        max_length=25,
        unique=True,
        default=generate_order_number,
        editable=False,
    )

    status = models.CharField(
        _("status"),
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
    )

    payment_status = models.CharField(
        _("payment status"),
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )

    # Pricing
    total_amount = models.DecimalField(
        _("total amount"),
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text=_("Sum of item prices before discounts"),
    )
    
    discount_amount = models.DecimalField(
        _("discount amount"),
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text=_("Total discount applied (vouchers + other)"),
    )
    
    final_amount = models.DecimalField(
        _("final amount"),
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text=_("Final payable amount after discounts"),
    )
    
    currency = models.CharField(
        _("currency"),
        max_length=3,
        default="QAR",
    )

    # Promotions
    vouchers = models.ManyToManyField(
        "promotions.Voucher",
        blank=True,
        related_name="product_orders",
        verbose_name=_("vouchers"),
    )
    
    gift_cards = models.ManyToManyField(
        "promotions.GiftCard",
        blank=True,
        related_name="product_orders",
        verbose_name=_("gift cards"),
    )

    payment_method = models.CharField(
        _("payment method"),
        max_length=50,
        blank=True,
        help_text=_("Method used for payment (e.g., Credit Card, Cash)"),
    )

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("product order")
        verbose_name_plural = _("product orders")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.order_number} - {self.user.email}"


class OrderItem(models.Model):
    """
    Individual item in a product order.
    """
    order = models.ForeignKey(
        ProductOrder,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("order"),
    )
    
    product = models.ForeignKey(
        "spacenter.SpaProduct",
        on_delete=models.PROTECT,
        related_name="order_items",
        verbose_name=_("product"),
    )
    
    quantity = models.PositiveIntegerField(
        _("quantity"),
        default=1,
        validators=[MinValueValidator(1)],
    )
    
    unit_price = models.DecimalField(
        _("unit price"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Price at time of purchase"),
    )
    
    total_price = models.DecimalField(
        _("total price"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Quantity * Unit Price"),
    )

    def save(self, *args, **kwargs):
        if not self.total_price:
            self.total_price = self.unit_price * self.quantity
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("order item")
        verbose_name_plural = _("order items")

    def __str__(self):
        return f"{self.quantity} x {self.product.product.name} ({self.order.order_number})"
