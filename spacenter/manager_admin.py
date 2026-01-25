"""
Branch Manager Admin Site.

Separate admin site restricted to branch managers only.
Accessible at /manager URL.
"""

from django.contrib import admin
from django.contrib.admin import AdminSite
from django.db.models import Sum
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from modeltranslation.admin import TranslationAdmin

from .models import (
    Service,
    ServiceImage,
    SpaCenter,
    SpaCenterOperatingHours,
    SpaProduct,
    TherapistProfile,
)
from bookings.models import Booking, ServiceArrangement, TimeSlot


# =============================================================================
# Custom Admin Site for Branch Managers
# =============================================================================

class BranchManagerAdminSite(AdminSite):
    """Custom admin site for branch managers only."""
    
    site_header = _("Branch Manager Portal")
    site_title = _("Branch Manager Portal")
    index_title = _("Welcome to the Branch Manager Portal")
    
    def has_permission(self, request):
        """
        Only allow access to users who are branch managers.
        A branch manager is a user with a managed_spa_center.
        """
        user = request.user
        if not user.is_active:
            return False
        
        # Must be authenticated
        if not user.is_authenticated:
            return False
        
        # Check if user is a branch manager (has managed_spa_center)
        if hasattr(user, 'managed_spa_center') and user.managed_spa_center is not None:
            return True
        
        return False


# Create the branch manager admin site instance
manager_admin_site = BranchManagerAdminSite(name='manager_admin')


# =============================================================================
# Helper function
# =============================================================================

def get_branch_manager_spa_center(user):
    """
    Get the spa center managed by this user.
    Returns None if user has no assigned spa center.
    """
    if hasattr(user, 'managed_spa_center'):
        return getattr(user, 'managed_spa_center', None)
    return None


# =============================================================================
# SpaCenter Admin for Branch Manager Portal
# =============================================================================

class ManagerSpaCenterOperatingHoursInline(admin.TabularInline):
    """Inline for operating hours."""
    model = SpaCenterOperatingHours
    extra = 0
    max_num = 7


class ManagerSpaCenterAdmin(TranslationAdmin):
    """SpaCenter admin for branch manager portal - read-only view of their center."""
    
    list_display = [
        "name",
        "city",
        "country",
        "default_opening_time",
        "default_closing_time",
        "is_active",
        "on_service",
    ]
    list_filter = ["is_active", "on_service"]
    search_fields = ["name", "name_en", "name_ar", "address", "city__name"]
    filter_horizontal = ["services"]
    inlines = [ManagerSpaCenterOperatingHoursInline]
    
    fieldsets = (
        (None, {
            "fields": ("name", "slug", "description", "image")
        }),
        ("Location", {
            "fields": (
                "country",
                "city",
                "address",
                "postal_code",
                ("latitude", "longitude"),
            )
        }),
        ("Contact", {
            "fields": ("phone", "email", "website")
        }),
        ("Operating Hours", {
            "fields": ("default_opening_time", "default_closing_time")
        }),
        ("Status", {
            "fields": ("is_active", "on_service")
        }),
        ("Services", {
            "fields": ("services",)
        }),
    )

    def get_queryset(self, request):
        """Branch managers can only see their own spa center."""
        qs = super().get_queryset(request)
        spa_center = get_branch_manager_spa_center(request.user)
        if spa_center:
            return qs.filter(id=spa_center.id)
        return qs.none()

    def has_add_permission(self, request):
        """Branch managers cannot add new spa centers."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Branch managers cannot delete spa centers."""
        return False


# =============================================================================
# Service Admin for Branch Manager Portal
# =============================================================================

class ManagerServiceImageInline(admin.TabularInline):
    """Inline for service images."""
    model = ServiceImage
    extra = 1
    max_num = 3
    min_num = 1
    fields = ["image", "alt_text", "is_primary", "sort_order"]


class ManagerServiceAdmin(TranslationAdmin):
    """Service admin for branch manager portal."""
    
    list_display = [
        "name",
        "specialty",
        "duration_minutes",
        "currency",
        "base_price",
        "discount_price",
        "is_home_service",
        "is_active",
        "sort_order",
    ]
    list_filter = ["is_active", "is_home_service", "specialty"]
    search_fields = ["name", "name_en", "name_ar", "description"]
    ordering = ["sort_order", "name"]
    list_editable = ["sort_order", "is_active", "is_home_service"]
    filter_horizontal = ["add_on_services"]
    inlines = [ManagerServiceImageInline]
    
    fieldsets = (
        (None, {
            "fields": ("name", "description", "specialty")
        }),
        ("Location", {
            "fields": ("country", "city")
        }),
        ("Pricing & Duration", {
            "fields": ("duration_minutes", "currency", "base_price", "discount_price")
        }),
        ("Home Service", {
            "fields": ("is_home_service", "price_for_home_service")
        }),
        ("Add-on Services", {
            "fields": ("add_on_services",),
        }),
        ("Additional Info", {
            "fields": ("ideal_for", "benefits")
        }),
        ("Status", {
            "fields": ("is_active", "sort_order")
        }),
    )

    def get_queryset(self, request):
        """Filter services by branch manager's spa center location."""
        qs = super().get_queryset(request)
        spa_center = get_branch_manager_spa_center(request.user)
        if spa_center:
            return qs.filter(country=spa_center.country, city=spa_center.city)
        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Limit country/city choices for branch managers."""
        from .models import City, Country
        spa_center = get_branch_manager_spa_center(request.user)
        if spa_center:
            if db_field.name == "country":
                kwargs["queryset"] = Country.objects.filter(id=spa_center.country_id)
            elif db_field.name == "city":
                kwargs["queryset"] = City.objects.filter(id=spa_center.city_id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# =============================================================================
# TherapistProfile Admin for Branch Manager Portal
# =============================================================================

class ManagerTherapistProfileAdmin(TranslationAdmin):
    """TherapistProfile admin for branch manager portal."""
    
    list_display = [
        "therapist_name",
        "spa_center",
        "years_of_experience",
        "is_available",
        "specialty_list",
    ]
    list_filter = ["is_available", "specialties"]
    search_fields = [
        "employee_profile__user__first_name",
        "employee_profile__user__last_name",
        "employee_profile__user__email",
    ]
    filter_horizontal = ["specialties", "services"]
    raw_id_fields = ["employee_profile", "spa_center"]
    ordering = ["-created_at"]

    fieldsets = (
        (None, {
            "fields": ("employee_profile", "spa_center")
        }),
        ("Skills", {
            "fields": ("specialties", "services", "years_of_experience")
        }),
        ("Profile", {
            "fields": ("bio", "is_available")
        }),
    )

    def therapist_name(self, obj):
        return obj.employee_profile.user.get_full_name()
    therapist_name.short_description = "Name"

    def specialty_list(self, obj):
        specialties = obj.specialties.all()[:3]
        names = ", ".join([s.name for s in specialties])
        if obj.specialties.count() > 3:
            names += f" (+{obj.specialties.count() - 3} more)"
        return names or "-"
    specialty_list.short_description = "Specialties"

    def get_queryset(self, request):
        """Filter therapists by branch manager's spa center."""
        qs = super().get_queryset(request)
        spa_center = get_branch_manager_spa_center(request.user)
        if spa_center:
            return qs.filter(spa_center=spa_center)
        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Limit spa center choices for branch managers."""
        spa_center = get_branch_manager_spa_center(request.user)
        if spa_center:
            if db_field.name == "spa_center":
                kwargs["queryset"] = SpaCenter.objects.filter(id=spa_center.id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# =============================================================================
# ServiceArrangement Admin for Branch Manager Portal
# =============================================================================

class ManagerServiceArrangementAdmin(admin.ModelAdmin):
    """ServiceArrangement admin for branch manager portal."""

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

    def get_queryset(self, request):
        """Filter service arrangements by branch manager's spa center."""
        qs = super().get_queryset(request)
        spa_center = get_branch_manager_spa_center(request.user)
        if spa_center:
            return qs.filter(spa_center=spa_center)
        return qs.none()

    def has_add_permission(self, request):
        """Branch managers cannot add service arrangements."""
        return False

    def has_change_permission(self, request, obj=None):
        """Branch managers cannot change service arrangements."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Branch managers cannot delete service arrangements."""
        return False

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Limit spa center and service choices for branch managers."""
        spa_center = get_branch_manager_spa_center(request.user)
        if spa_center:
            if db_field.name == "spa_center":
                kwargs["queryset"] = SpaCenter.objects.filter(id=spa_center.id)
            elif db_field.name == "service":
                kwargs["queryset"] = spa_center.services.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# =============================================================================
# TimeSlot Admin for Branch Manager Portal
# =============================================================================

class ManagerTimeSlotAdmin(admin.ModelAdmin):
    """TimeSlot admin for branch manager portal."""

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
        return qs.none()

    def has_add_permission(self, request):
        """Branch managers cannot add time slots."""
        return False

    def has_change_permission(self, request, obj=None):
        """Branch managers cannot change time slots."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Branch managers cannot delete time slots."""
        return False

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Limit arrangement choices for branch managers."""
        spa_center = get_branch_manager_spa_center(request.user)
        if spa_center:
            if db_field.name == "arrangement":
                kwargs["queryset"] = ServiceArrangement.objects.filter(spa_center=spa_center)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# =============================================================================
# Booking Admin for Branch Manager Portal
# =============================================================================

class ManagerBookingAdmin(admin.ModelAdmin):
    """Booking admin for branch manager portal."""

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
        return qs.none()

    def has_add_permission(self, request):
        """Branch managers cannot add bookings."""
        return False

    def has_change_permission(self, request, obj=None):
        """Branch managers cannot change bookings."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Branch managers cannot delete bookings."""
        return False

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Limit choices for branch managers."""
        spa_center = get_branch_manager_spa_center(request.user)
        if spa_center:
            if db_field.name == "spa_center":
                kwargs["queryset"] = SpaCenter.objects.filter(id=spa_center.id)
            elif db_field.name == "service_arrangement":
                kwargs["queryset"] = ServiceArrangement.objects.filter(spa_center=spa_center)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# =============================================================================
# SpaProduct Admin for Branch Manager Portal
# =============================================================================

class ManagerSpaProductAdmin(admin.ModelAdmin):
    """SpaProduct admin for branch manager portal."""

    list_display = [
        "product",
        "country",
        "city",
        "currency",
        "price",
        "discounted_price",
        "current_price_display",
        "quantity",
        "reserved_quantity",
        "available_display",
        "stock_status_display",
    ]
    list_filter = [
        "product__category",
        "product__status",
    ]
    search_fields = [
        "product__name",
        "product__sku",
    ]
    ordering = ["-updated_at"]
    list_editable = ["quantity", "price", "discounted_price"]
    raw_id_fields = ["product", "country", "city"]

    fieldsets = (
        (None, {
            "fields": ("product",)
        }),
        ("Location", {
            "fields": ("country", "city")
        }),
        ("Pricing", {
            "fields": ("currency", "price", "discounted_price")
        }),
        ("Inventory", {
            "fields": ("quantity", "reserved_quantity", "low_stock_threshold")
        }),
    )

    def current_price_display(self, obj):
        """Display current price with discount indicator."""
        if obj.has_discount:
            return format_html(
                '<span style="text-decoration: line-through; color: #999;">{}</span> '
                '<span style="color: green; font-weight: bold;">{}</span> '
                '<span style="color: red;">(-{}%)</span>',
                obj.price,
                obj.current_price,
                obj.discount_percentage
            )
        return obj.price
    current_price_display.short_description = "Current Price"

    def available_display(self, obj):
        """Display available quantity."""
        available = obj.available_quantity
        if available == 0:
            return format_html('<span style="color: red;">0</span>')
        elif obj.is_low_stock:
            return format_html('<span style="color: orange;">{}</span>', available)
        return available
    available_display.short_description = "Available"

    def stock_status_display(self, obj):
        """Display stock status with color coding."""
        status = obj.stock_status
        if status == "out_of_stock":
            return format_html('<span style="color: red;">Out of Stock</span>')
        elif status == "low_stock":
            return format_html('<span style="color: orange;">Low Stock</span>')
        return format_html('<span style="color: green;">In Stock</span>')
    stock_status_display.short_description = "Status"

    def get_queryset(self, request):
        """Filter products by branch manager's location."""
        qs = super().get_queryset(request)
        spa_center = get_branch_manager_spa_center(request.user)
        if spa_center:
            return qs.filter(
                country=spa_center.country,
                city=spa_center.city
            )
        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Limit country/city choices for branch managers."""
        from .models import City, Country
        spa_center = get_branch_manager_spa_center(request.user)
        if spa_center:
            if db_field.name == "country":
                kwargs["queryset"] = Country.objects.filter(id=spa_center.country_id)
            elif db_field.name == "city":
                kwargs["queryset"] = City.objects.filter(id=spa_center.city_id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        """Auto-set country/city for branch managers on create."""
        spa_center = get_branch_manager_spa_center(request.user)
        if not change and spa_center:
            obj.country = spa_center.country
            obj.city = spa_center.city
        super().save_model(request, obj, form, change)


# =============================================================================
# Register models with the branch manager admin site
# =============================================================================

manager_admin_site.register(SpaCenter, ManagerSpaCenterAdmin)
manager_admin_site.register(Service, ManagerServiceAdmin)
manager_admin_site.register(TherapistProfile, ManagerTherapistProfileAdmin)
manager_admin_site.register(ServiceArrangement, ManagerServiceArrangementAdmin)
manager_admin_site.register(TimeSlot, ManagerTimeSlotAdmin)
manager_admin_site.register(Booking, ManagerBookingAdmin)
manager_admin_site.register(SpaProduct, ManagerSpaProductAdmin)
