"""
Booking Admin Configuration.

Admin interface for managing service arrangements, time slots, and bookings.
Uses Django Unfold for modern admin styling.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from unfold.admin import ModelAdmin
from unfold.decorators import display

from .models import Booking, ServiceArrangement, TimeSlot


@admin.register(ServiceArrangement)
class ServiceArrangementAdmin(ModelAdmin):
    """Admin for ServiceArrangement model."""

    list_display = [
        "arrangement_label",
        "spa_center",
        "service",
        "room_no",
        "arrangement_type",
        "cleanup_duration",
        "is_active",
        "created_at",
    ]
    list_filter = [
        "is_active",
        "arrangement_type",
        "spa_center",
        "service",
    ]
    search_fields = [
        "arrangement_label",
        "room_no",
        "spa_center__name",
        "service__name",
    ]
    ordering = ["spa_center", "service", "room_no"]
    readonly_fields = ["id", "created_at", "updated_at"]

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "spa_center",
                    "service",
                    "room_no",
                    "arrangement_label",
                    "arrangement_type",
                )
            },
        ),
        (
            _("Settings"),
            {
                "fields": (
                    "cleanup_duration",
                    "is_active",
                )
            },
        ),
        (
            _("Metadata"),
            {
                "fields": (
                    "id",
                    "created_at",
                    "updated_at",
                ),
                "classes": ["collapse"],
            },
        ),
    )


@admin.register(TimeSlot)
class TimeSlotAdmin(ModelAdmin):
    """Admin for TimeSlot model."""

    list_display = [
        "id",
        "arrangement",
        "date",
        "start_time",
        "end_time",
        "created_at",
    ]
    list_filter = [
        "date",
        "arrangement__spa_center",
        "arrangement__service",
    ]
    search_fields = [
        "arrangement__arrangement_label",
        "arrangement__service__name",
    ]
    ordering = ["-date", "-start_time"]
    readonly_fields = ["id", "created_at"]
    date_hierarchy = "date"

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "arrangement",
                    "date",
                    "start_time",
                    "end_time",
                )
            },
        ),
        (
            _("Metadata"),
            {
                "fields": (
                    "id",
                    "created_at",
                ),
                "classes": ["collapse"],
            },
        ),
    )


@admin.register(Booking)
class BookingAdmin(ModelAdmin):
    """Admin for Booking model."""

    list_display = [
        "booking_number",
        "customer",
        "spa_center",
        "get_service_name",
        "get_booking_date",
        "get_booking_time",
        "total_price",
        "display_status",
        "created_at",
    ]
    list_filter = [
        "status",
        "spa_center",
        "service_arrangement__service",
        "created_at",
    ]
    search_fields = [
        "booking_number",
        "customer__email",
        "customer__first_name",
        "customer__last_name",
        "spa_center__name",
    ]
    ordering = ["-created_at"]
    readonly_fields = [
        "id",
        "booking_number",
        "created_at",
        "updated_at",
    ]
    date_hierarchy = "created_at"
    filter_horizontal = ["add_on_services"]
    raw_id_fields = ["customer", "time_slot"]

    fieldsets = (
        (
            _("Booking Information"),
            {
                "fields": (
                    "booking_number",
                    "status",
                    "customer",
                )
            },
        ),
        (
            _("Service Details"),
            {
                "fields": (
                    "spa_center",
                    "service_arrangement",
                    "time_slot",
                    "therapist",
                    "add_on_services",
                )
            },
        ),
        (
            _("Pricing"),
            {
                "fields": ("total_price",)
            },
        ),
        (
            _("Notes"),
            {
                "fields": (
                    "customer_message",
                    "staff_notes",
                )
            },
        ),
        (
            _("Metadata"),
            {
                "fields": (
                    "id",
                    "created_at",
                    "updated_at",
                ),
                "classes": ["collapse"],
            },
        ),
    )

    @admin.display(description=_("Service"))
    def get_service_name(self, obj):
        return obj.service_arrangement.service.name

    @admin.display(description=_("Date"))
    def get_booking_date(self, obj):
        return obj.time_slot.date

    @admin.display(description=_("Time"))
    def get_booking_time(self, obj):
        return f"{obj.time_slot.start_time} - {obj.time_slot.end_time}"

    @display(
        description=_("Status"),
        label={
            Booking.BookingStatus.REQUESTED: "info",
            Booking.BookingStatus.PAYMENT_PENDING: "warning",
            Booking.BookingStatus.PAYMENT_SUCCESS: "success",
            Booking.BookingStatus.CONFIRMED: "success",
            Booking.BookingStatus.ON_HOLD: "warning",
            Booking.BookingStatus.CANCELED: "danger",
            Booking.BookingStatus.COMPLETED: "success",
        },
    )
    def display_status(self, obj):
        return obj.get_status_display()

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "customer",
                "spa_center",
                "service_arrangement__service",
                "time_slot",
                "therapist",
            )
            .prefetch_related("add_on_services")
        )
