from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import Booking, TimeSlot
from spacenter.models import SpaCenter, Service, ServiceArrangement


def get_branch_manager_spa_center(user):
    """
    Get the spa center managed by this user if they are a branch manager.
    Returns None if user is a superuser or has no assigned spa center.
    """
    if user.is_superuser:
        return None
    if hasattr(user, 'managed_spa_center'):
        return getattr(user, 'managed_spa_center', None)
    return None


class BranchManagerPermissionMixin:
    """
    Mixin that grants branch managers permission to view/add/change models.
    Branch managers are identified by having a managed_spa_center.
    """

    def has_module_permission(self, request):
        """Allow branch managers to see the app in admin."""
        if get_branch_manager_spa_center(request.user):
            return True
        return super().has_module_permission(request)

    def has_view_permission(self, request, obj=None):
        """Allow branch managers to view objects."""
        if get_branch_manager_spa_center(request.user):
            return True
        return super().has_view_permission(request, obj)

    def has_add_permission(self, request):
        """Allow branch managers to add objects."""
        if get_branch_manager_spa_center(request.user):
            return True
        return super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        """Allow branch managers to change objects."""
        if get_branch_manager_spa_center(request.user):
            return True
        return super().has_change_permission(request, obj)





@admin.register(TimeSlot)
class TimeSlotAdmin(BranchManagerPermissionMixin, admin.ModelAdmin):
    """Admin for TimeSlot model."""

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
        """Filter time slots by branch manager's spa center."""
        qs = super().get_queryset(request)
        spa_center = get_branch_manager_spa_center(request.user)
        if spa_center:
            return qs.filter(arrangement__spa_center=spa_center)
        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Limit arrangement choices for branch managers."""
        spa_center = get_branch_manager_spa_center(request.user)
        if spa_center:
            if db_field.name == "arrangement":
                kwargs["queryset"] = ServiceArrangement.objects.filter(spa_center=spa_center)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Booking)
class BookingAdmin(BranchManagerPermissionMixin, admin.ModelAdmin):
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

    @admin.display(description=_("Status"))
    def display_status(self, obj):
        return obj.get_status_display()

    def get_queryset(self, request):
        """Filter bookings by branch manager's spa center."""
        qs = (
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
        spa_center = get_branch_manager_spa_center(request.user)
        if spa_center:
            return qs.filter(spa_center=spa_center)
        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Limit choices for branch managers."""
        spa_center = get_branch_manager_spa_center(request.user)
        if spa_center:
            if db_field.name == "spa_center":
                kwargs["queryset"] = SpaCenter.objects.filter(id=spa_center.id)
            elif db_field.name == "service_arrangement":
                kwargs["queryset"] = ServiceArrangement.objects.filter(spa_center=spa_center)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
