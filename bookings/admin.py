import json
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from config.admin_mixins import SpaCenterRestrictedAdminMixin
from simple_history.admin import SimpleHistoryAdmin
from .models import Booking, TimeSlot, ProductOrder, OrderItem, HomeServiceBooking
from spacenter.models import SpaCenter, Service, ServiceArrangement
from spacenter.filters import SpaCenterFilter





@admin.register(TimeSlot)
class TimeSlotAdmin(SpaCenterRestrictedAdminMixin, admin.ModelAdmin):
    """Admin for TimeSlot model."""
    
    spa_center_field = "arrangement__spa_center"

    list_display = [
        "arrangement",
        "date",
        "start_time",
        "end_time",
        "created_at",
    ]
    list_filter = [
        "date",
        
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

    def get_queryset(self, request):
        """Standard queryset."""
        return super().get_queryset(request)


@admin.register(Booking)
class BookingAdmin(SpaCenterRestrictedAdminMixin, SimpleHistoryAdmin):
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
        SpaCenterFilter,
        "status",
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
        "get_formatted_meta_data",
        "created_at",
        "updated_at",
    ]
    date_hierarchy = "created_at"
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
                    "service",
                    "service_arrangement",
                    "time_slot",
                )
            },
        ),
        (
            _("Pricing"),
            {
                "fields": ("subtotal", "discount_amount", "extra_minutes", "price_for_extra_minutes", "total_duration", "total_price")
            },
        ),
        (
            _("Booking Snapshot (Meta Data)"),
            {
                "fields": ("get_formatted_meta_data",),
                "classes": ["collapse"],
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
        if obj.service:
            return obj.service.name
        return obj.service_arrangement.service.name

    @admin.display(description=_("Date"))
    def get_booking_date(self, obj):
        return obj.time_slot.date

    @admin.display(description=_("Time"))
    def get_booking_time(self, obj):
        return f"{obj.time_slot.start_time} - {obj.time_slot.end_time}"

    @admin.display(description=_("Status"))
    def display_status(self, obj):
        return obj.get_status_display()

    @admin.display(description=_("Formatted Meta Data"))
    def get_formatted_meta_data(self, obj):
        """Display JSON data in a pretty-printed format."""
        if not obj.meta_data:
            return "-"
        formatted_json = json.dumps(obj.meta_data, indent=4, ensure_ascii=False)
        return format_html('<pre style="background-color: #828387; padding: 10px; border-radius: 4px; border: 1px solid #dee2e6;">{}</pre>', formatted_json)

    def get_queryset(self, request):
        """Optimise queryset with select_related."""
        return (
            super()
            .get_queryset(request)
            .select_related(
                "customer",
                "spa_center",
                "service",
                "service_arrangement__service",
                "time_slot",
            )
        )


class OrderItemInline(admin.TabularInline):
    """Inline for order items inside ProductOrder admin."""
    model = OrderItem
    extra = 0
    readonly_fields = ["product", "quantity", "unit_price", "total_price"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ProductOrder)
class ProductOrderAdmin(admin.ModelAdmin):
    """Admin for ProductOrder model."""

    list_display = [
        "order_number",
        "user",
        "status",
        "payment_status",
        "total_amount",
        "delivery_charge",
        "final_amount",
        "created_at",
    ]
    list_filter = [
        "status",
        "payment_status",
        "created_at",
    ]
    search_fields = [
        "order_number",
        "user__email",
        "user__first_name",
        "user__last_name",
        "contact_number",
    ]
    ordering = ["-created_at"]
    readonly_fields = [
        "id",
        "order_number",
        "created_at",
        "updated_at",
    ]
    date_hierarchy = "created_at"
    raw_id_fields = ["user"]
    inlines = [OrderItemInline]

    fieldsets = (
        (
            _("Order Information"),
            {
                "fields": (
                    "order_number",
                    "user",
                    "status",
                    "payment_status",
                )
            },
        ),
        (
            _("Delivery Details"),
            {
                "fields": (
                    "shipping_address",
                    "contact_number",
                )
            },
        ),
        (
            _("Pricing"),
            {
                "fields": (
                    "total_amount",
                    "delivery_charge",
                    "final_amount",
                    "currency",
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


@admin.register(HomeServiceBooking)
class HomeServiceBookingAdmin(admin.ModelAdmin):
    """Admin for HomeServiceBooking model."""

    list_display = [
        "booking_number",
        "customer",
        "home_service",
        "date",
        "time",
        "total_price",
        "display_status",
        "created_at",
    ]
    list_filter = [
        "status",
        "date",
        "created_at",
    ]
    search_fields = [
        "booking_number",
        "customer__email",
        "customer__first_name",
        "customer__last_name",
        "home_service__name",
        "contact_number",
    ]
    ordering = ["-created_at"]
    readonly_fields = [
        "id",
        "booking_number",
        "created_at",
        "updated_at",
    ]
    date_hierarchy = "created_at"
    raw_id_fields = ["customer"]

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
                    "home_service",
                    "date",
                    "time",
                )
            },
        ),
        (
            _("Pricing"),
            {
                "fields": (
                    "subtotal",
                    "discount_amount",
                    "extra_minutes",
                    "price_for_extra_minutes",
                    "total_duration",
                    "total_price",
                )
            },
        ),
        (
            _("Home Details"),
            {
                "fields": (
                    "home_location",
                    "contact_number",
                )
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

    @admin.display(description=_("Status"))
    def display_status(self, obj):
        return obj.get_status_display()

    def get_queryset(self, request):
        """Optimise queryset with select_related."""
        return (
            super()
            .get_queryset(request)
            .select_related("customer", "home_service")
        )
