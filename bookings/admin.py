import json
from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import path, reverse
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
        "status",
        "status_actions",
        "created_at",
    ]
    list_editable = ["status"]
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
        return None

    @admin.display(description=_("Date"))
    def get_booking_date(self, obj):
        return obj.time_slot.date

    @admin.display(description=_("Time"))
    def get_booking_time(self, obj):
        return f"{obj.time_slot.start_time} - {obj.time_slot.end_time}"

    @admin.display(description=_("Status Actions"))
    def status_actions(self, obj):
        """Render quick action buttons for status changes."""
        buttons = []
        
        # Define button styles
        btn_base = 'display: inline-block; padding: 4px 8px; border-radius: 4px; color: white; text-decoration: none; font-weight: bold; font-size: 11px; margin-right: 5px;'
        confirm_style = f'{btn_base} background-color: #28a745;'
        cancel_style = f'{btn_base} background-color: #dc3545;'
        complete_style = f'{btn_base} background-color: #17a2b8;'

        if obj.status == Booking.BookingStatus.REQUESTED:
            buttons.append(format_html(
                '<a href="{}" style="{}">{}</a>',
                reverse('admin:booking-set-status', args=[obj.pk, 'confirmed']),
                confirm_style,
                _("Confirm")
            ))
            buttons.append(format_html(
                '<a href="{}" style="{}">{}</a>',
                reverse('admin:booking-set-status', args=[obj.pk, 'canceled']),
                cancel_style,
                _("Cancel")
            ))
        
        elif obj.status == Booking.BookingStatus.CONFIRMED:
            buttons.append(format_html(
                '<a href="{}" style="{}">{}</a>',
                reverse('admin:booking-set-status', args=[obj.pk, 'completed']),
                complete_style,
                _("Complete")
            ))
            buttons.append(format_html(
                '<a href="{}" style="{}">{}</a>',
                reverse('admin:booking-set-status', args=[obj.pk, 'canceled']),
                cancel_style,
                _("Cancel")
            ))

        if not buttons:
            return "-"
        
        return format_html(''.join(buttons))

    def get_urls(self):
        """Add custom URLs for status actions."""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<uuid:object_id>/set-status/<str:status>/',
                self.admin_site.admin_view(self.set_status),
                name='booking-set-status',
            ),
        ]
        return custom_urls + urls

    def set_status(self, request, object_id, status):
        """Custom view to update booking status."""
        obj = self.get_object(request, object_id)
        if obj:
            old_status = obj.get_status_display()
            obj.status = status
            obj.save()
            new_status = obj.get_status_display()
            messages.success(request, _(f"Status for booking {obj.booking_number} updated from {old_status} to {new_status}."))
        
        # Redirect back to the changelist
        return redirect(reverse('admin:bookings_booking_changelist'))

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
                "service_arrangement",
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
    list_editable = ["status", "payment_status"]
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
        "status",
        "status_actions",
        "created_at",
    ]
    list_editable = ["status"]
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

    @admin.display(description=_("Status Actions"))
    def status_actions(self, obj):
        """Render quick action buttons for status changes."""
        buttons = []
        
        # Define button styles
        btn_base = 'display: inline-block; padding: 4px 8px; border-radius: 4px; color: white; text-decoration: none; font-weight: bold; font-size: 11px; margin-right: 5px;'
        confirm_style = f'{btn_base} background-color: #28a745;'
        cancel_style = f'{btn_base} background-color: #dc3545;'
        complete_style = f'{btn_base} background-color: #17a2b8;'

        if obj.status == HomeServiceBooking.BookingStatus.REQUESTED:
            buttons.append(format_html(
                '<a href="{}" style="{}">{}</a>',
                reverse('admin:home-booking-set-status', args=[obj.pk, 'confirmed']),
                confirm_style,
                _("Confirm")
            ))
            buttons.append(format_html(
                '<a href="{}" style="{}">{}</a>',
                reverse('admin:home-booking-set-status', args=[obj.pk, 'canceled']),
                cancel_style,
                _("Cancel")
            ))
        
        elif obj.status == HomeServiceBooking.BookingStatus.CONFIRMED:
            buttons.append(format_html(
                '<a href="{}" style="{}">{}</a>',
                reverse('admin:home-booking-set-status', args=[obj.pk, 'completed']),
                complete_style,
                _("Complete")
            ))
            buttons.append(format_html(
                '<a href="{}" style="{}">{}</a>',
                reverse('admin:home-booking-set-status', args=[obj.pk, 'canceled']),
                cancel_style,
                _("Cancel")
            ))

        if not buttons:
            return "-"
        
        return format_html(''.join(buttons))

    def get_urls(self):
        """Add custom URLs for status actions."""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<uuid:object_id>/set-status/<str:status>/',
                self.admin_site.admin_view(self.set_status),
                name='home-booking-set-status',
            ),
        ]
        return custom_urls + urls

    def set_status(self, request, object_id, status):
        """Custom view to update booking status."""
        obj = self.get_object(request, object_id)
        if obj:
            old_status = obj.get_status_display()
            obj.status = status
            obj.save()
            new_status = obj.get_status_display()
            messages.success(request, _(f"Status for booking {obj.booking_number} updated from {old_status} to {new_status}."))
        
        # Redirect back to the changelist
        return redirect(reverse('admin:bookings_homeservicebooking_changelist'))

    def get_queryset(self, request):
        """Optimise queryset with select_related."""
        return (
            super()
            .get_queryset(request)
            .select_related("customer", "home_service")
        )
