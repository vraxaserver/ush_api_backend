"""
Spa Center Admin Configuration.

Admin interface for managing spa centers, services, specialties, and therapists.
Supports multi-language (English, Arabic) via django-modeltranslation.
"""

from django.contrib import admin
from django.db.models import Sum
from django.utils.html import format_html
from modeltranslation.admin import TranslationAdmin

from .models import (
    AddOnService,
    BaseProduct,
    City,
    Country,
    ProductCategory,
    Service,
    ServiceImage,
    SpaCenter,
    SpaCenterOperatingHours,
    SpaProduct,
    Specialty,
    TherapistProfile,
)


@admin.register(Country)
class CountryAdmin(TranslationAdmin):
    """Admin for Country model with translation support."""

    list_display = ["name", "code", "phone_code", "is_active", "sort_order", "city_count"]
    list_filter = ["is_active"]
    search_fields = ["name", "name_en", "name_ar", "code"]
    ordering = ["sort_order", "name"]
    list_editable = ["sort_order", "is_active"]

    fieldsets = (
        (None, {
            "fields": ("name", "code", "phone_code")
        }),
        ("Media", {
            "fields": ("flag",)
        }),
        ("Status", {
            "fields": ("is_active", "sort_order")
        }),
    )

    def city_count(self, obj):
        return obj.cities.count()
    city_count.short_description = "Cities"


@admin.register(City)
class CityAdmin(TranslationAdmin):
    """Admin for City model with translation support."""

    list_display = ["name", "country", "state", "is_active", "sort_order"]
    list_filter = ["is_active", "country"]
    search_fields = ["name", "name_en", "name_ar", "state", "country__name"]
    ordering = ["country", "sort_order", "name"]
    list_editable = ["sort_order", "is_active"]
    autocomplete_fields = ["country"]

    fieldsets = (
        (None, {
            "fields": ("country", "name", "state")
        }),
        ("Status", {
            "fields": ("is_active", "sort_order")
        }),
    )


@admin.register(Specialty)
class SpecialtyAdmin(TranslationAdmin):
    """Admin for Specialty model with translation support."""

    list_display = ["name", "is_active", "sort_order", "therapist_count", "service_count"]
    list_filter = ["is_active"]
    search_fields = ["name", "name_en", "name_ar", "description"]
    ordering = ["sort_order", "name"]
    list_editable = ["sort_order", "is_active"]

    fieldsets = (
        (None, {
            "fields": ("name", "description")
        }),
        ("Media", {
            "fields": ("icon",)
        }),
        ("Status", {
            "fields": ("is_active", "sort_order")
        }),
    )

    def therapist_count(self, obj):
        return obj.therapists.count()
    therapist_count.short_description = "Therapists"

    def service_count(self, obj):
        return obj.services.count()
    service_count.short_description = "Services"


@admin.register(AddOnService)
class AddOnServiceAdmin(TranslationAdmin):
    """Admin for AddOnService model."""

    list_display = [
        "name",
        "duration_minutes",
        "currency",
        "price",
        "is_active",
        "sort_order",
        "service_count",
        "image_preview",
    ]
    list_filter = ["is_active", "currency"]
    search_fields = ["name", "name_en", "name_ar", "description"]
    ordering = ["sort_order", "name"]
    list_editable = ["sort_order", "is_active", "price", "duration_minutes"]

    fieldsets = (
        ("English", {
            "fields": ("name_en", "description_en")
        }),
        ("Arabic", {
            "fields": ("name_ar", "description_ar"),
            "classes": ("collapse",)
        }),
        ("Pricing & Duration", {
            "fields": ("duration_minutes", "currency", "price")
        }),
        ("Media", {
            "fields": ("image",)
        }),
        ("Status", {
            "fields": ("is_active", "sort_order")
        }),
    )

    def service_count(self, obj):
        """Count of services using this add-on."""
        return obj.services.count()
    service_count.short_description = "Used In"

    def image_preview(self, obj):
        """Display image thumbnail."""
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 40px; max-width: 60px;" />',
                obj.image.url
            )
        return "-"
    image_preview.short_description = "Image"


class ServiceImageInline(admin.TabularInline):
    """Inline for service images."""

    model = ServiceImage
    extra = 1
    max_num = 3
    min_num = 1
    fields = ["image", "alt_text", "is_primary", "sort_order"]


@admin.register(Service)
class ServiceAdmin(TranslationAdmin):
    """Admin for Service model with translation support."""

    list_display = [
        "name",
        "specialty",
        "country",
        "city",
        "duration_minutes",
        "currency",
        "base_price",
        "discount_price",
        "current_price_display",
        "is_home_service",
        "is_active",
        "sort_order",
        "addon_count",
        "image_count",
    ]
    list_filter = ["is_active", "is_home_service", "specialty", "currency", "country", "city"]
    search_fields = ["name", "name_en", "name_ar", "description", "ideal_for"]
    ordering = ["sort_order", "name"]
    list_editable = ["sort_order", "is_active", "is_home_service"]
    autocomplete_fields = ["specialty", "country", "city"]
    filter_horizontal = ["add_on_services"]
    inlines = [ServiceImageInline]

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
            "description": "Select additional services that can be added to this service."
        }),
        ("Additional Info", {
            "fields": ("ideal_for", "benefits")
        }),
        ("Status", {
            "fields": ("is_active", "sort_order", "created_by")
        }),
    )
    readonly_fields = ["created_by"]

    def addon_count(self, obj):
        """Count of add-on services attached."""
        count = obj.add_on_services.count()
        if count > 0:
            return format_html('<span style="color: green;">{}</span>', count)
        return "-"
    addon_count.short_description = "Add-ons"

    def current_price_display(self, obj):
        if obj.has_discount:
            return format_html(
                '<span style="text-decoration: line-through; color: #999;">{}</span> '
                '<span style="color: green; font-weight: bold;">{}</span> '
                '<span style="color: red;">(-{}%)</span>',
                obj.base_price,
                obj.current_price,
                obj.discount_percentage
            )
        return obj.base_price
    current_price_display.short_description = "Current Price"

    def image_count(self, obj):
        count = obj.images.count()
        if count < 1:
            return format_html('<span style="color: red;">0 (Required!)</span>')
        return count
    image_count.short_description = "Images"

    def save_model(self, request, obj, form, change):
        if not change:  # Only on create
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ServiceImage)
class ServiceImageAdmin(admin.ModelAdmin):
    """Admin for ServiceImage model."""

    list_display = ["service", "image_preview", "is_primary", "sort_order"]
    list_filter = ["is_primary", "service"]
    ordering = ["service", "sort_order"]

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 100px;" />',
                obj.image.url
            )
        return "-"
    image_preview.short_description = "Preview"


class SpaCenterOperatingHoursInline(admin.TabularInline):
    """Inline for operating hours."""

    model = SpaCenterOperatingHours
    extra = 0
    max_num = 7


@admin.register(SpaCenter)
class SpaCenterAdmin(TranslationAdmin):
    """Admin for SpaCenter model with translation support."""

    list_display = [
        "name",
        "city",
        "country",
        "branch_manager_display",
        "default_opening_time",
        "default_closing_time",
        "is_active",
        "on_service",
        "sort_order",
    ]
    list_filter = ["is_active", "on_service", "country", "city"]
    search_fields = ["name", "name_en", "name_ar", "address", "city__name"]
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ["services"]
    raw_id_fields = ["branch_manager"]
    autocomplete_fields = ["country", "city"]
    inlines = [SpaCenterOperatingHoursInline]
    ordering = ["sort_order", "country", "name"]
    list_editable = ["sort_order", "is_active", "on_service"]

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
            "fields": ("is_active", "on_service", "sort_order")
        }),
        ("Management", {
            "fields": ("branch_manager", "services")
        }),
    )

    def branch_manager_display(self, obj):
        if obj.branch_manager:
            return obj.branch_manager.get_full_name()
        return "-"
    branch_manager_display.short_description = "Branch Manager"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter city choices based on selected country."""
        if db_field.name == "city":
            # Get country from request if available
            if request.resolver_match.kwargs.get("object_id"):
                try:
                    obj = self.get_object(request, request.resolver_match.kwargs["object_id"])
                    if obj and obj.country:
                        kwargs["queryset"] = City.objects.filter(country=obj.country)
                except Exception:
                    pass
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(SpaCenterOperatingHours)
class SpaCenterOperatingHoursAdmin(admin.ModelAdmin):
    """Admin for operating hours."""

    list_display = [
        "spa_center",
        "day_of_week",
        "opening_time",
        "closing_time",
        "is_closed",
    ]
    list_filter = ["spa_center", "day_of_week", "is_closed"]
    ordering = ["spa_center", "day_of_week"]


@admin.register(TherapistProfile)
class TherapistProfileAdmin(TranslationAdmin):
    """Admin for TherapistProfile model with translation support."""

    list_display = [
        "therapist_name",
        "spa_center",
        "country_display",
        "city_display",
        "years_of_experience",
        "is_available",
        "specialty_list",
    ]
    list_filter = [
        "is_available",
        "spa_center__country",
        "spa_center__city",
        "spa_center",
        "specialties",
    ]
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

    def country_display(self, obj):
        if obj.spa_center and obj.spa_center.country:
            return obj.spa_center.country.name
        return "-"
    country_display.short_description = "Country"

    def city_display(self, obj):
        if obj.spa_center and obj.spa_center.city:
            return obj.spa_center.city.name
        return "-"
    city_display.short_description = "City"

    def specialty_list(self, obj):
        specialties = obj.specialties.all()[:3]
        names = ", ".join([s.name for s in specialties])
        if obj.specialties.count() > 3:
            names += f" (+{obj.specialties.count() - 3} more)"
        return names or "-"
    specialty_list.short_description = "Specialties"


# =============================================================================
# Product Admin (Only Admin can add/update/delete ProductCategory and BaseProduct)
# =============================================================================

@admin.register(ProductCategory)
class ProductCategoryAdmin(TranslationAdmin):
    """
    Admin for ProductCategory model.
    Only Admin can add/update/delete.
    """

    list_display = [
        "name",
        "is_active",
        "sort_order",
        "created_at",
    ]
    list_filter = ["is_active"]
    search_fields = ["name", "name_en", "name_ar", "description"]
    ordering = ["sort_order", "name"]
    list_editable = ["sort_order", "is_active"]

    fieldsets = (
        (None, {
            "fields": ("name", "description")
        }),
        ("Status", {
            "fields": ("is_active", "sort_order")
        }),
    )


@admin.register(BaseProduct)
class BaseProductAdmin(TranslationAdmin):
    """
    Admin for BaseProduct model.
    Only Admin can add/update/delete.
    """

    list_display = [
        "name",
        "sku",
        "category",
        "brand",
        "product_type",
        "status",
        "is_featured",
        "is_visible",
        "total_stock_display",
        "locations_count_display",
        "image_preview",
    ]
    list_filter = [
        "status",
        "product_type",
        "category",
        "is_featured",
        "is_visible",
        "is_organic",
        "is_aromatherapy",
        "suitable_for_sensitive_skin",
    ]
    search_fields = [
        "name",
        "name_en",
        "name_ar",
        "sku",
        "brand",
        "short_description",
        "category",
    ]
    ordering = ["-created_at"]
    list_editable = ["status", "is_featured", "is_visible"]

    fieldsets = (
        (None, {
            "fields": ("name", "sku", "short_description")
        }),
        ("Classification", {
            "fields": ("product_type", "category", "brand")
        }),
        ("Media", {
            "fields": ("image",)
        }),
        ("Product Attributes", {
            "fields": (
                "is_organic",
                "is_aromatherapy",
                "suitable_for_sensitive_skin",
            )
        }),
        ("Display Settings", {
            "fields": ("status", "is_featured", "is_visible")
        }),
    )

    def total_stock_display(self, obj):
        """Display total stock across all locations."""
        total = obj.stocks.aggregate(total=Sum("quantity"))["total"] or 0
        if total == 0:
            return format_html('<span style="color: red;">0</span>')
        return total
    total_stock_display.short_description = "Total Stock"

    def locations_count_display(self, obj):
        """Display number of locations with stock."""
        count = obj.stocks.filter(quantity__gt=0).count()
        return count
    locations_count_display.short_description = "Locations"

    def image_preview(self, obj):
        """Display image preview."""
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 40px; max-width: 60px;" />',
                obj.image.url
            )
        return "-"
    image_preview.short_description = "Image"


@admin.register(SpaProduct)
class SpaProductAdmin(admin.ModelAdmin):
    """
    Admin for SpaProduct model.
    Admin and Branch Manager can add/update.
    Branch Manager can only manage products in their branch's location.
    """

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
        "country",
        "city",
        "currency",
        "product__category",
        "product__status",
    ]
    search_fields = [
        "product__name",
        "product__sku",
        "country__name",
        "city__name",
    ]
    ordering = ["-updated_at"]
    list_editable = ["quantity", "price", "discounted_price"]
    autocomplete_fields = ["product", "country", "city"]

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
        """
        Filter queryset based on user role.
        Branch managers can only see products in their branch's location.
        """
        qs = super().get_queryset(request)
        
        # Check if user is a branch manager (not superuser/admin)
        if not request.user.is_superuser:
            if hasattr(request.user, 'managed_spa_center'):
                spa_center = request.user.managed_spa_center
                if spa_center:
                    return qs.filter(
                        country=spa_center.country,
                        city=spa_center.city
                    )
        
        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Limit country/city choices for branch managers.
        """
        if not request.user.is_superuser:
            if hasattr(request.user, 'managed_spa_center'):
                spa_center = request.user.managed_spa_center
                if spa_center:
                    if db_field.name == "country":
                        kwargs["queryset"] = Country.objects.filter(id=spa_center.country_id)
                    elif db_field.name == "city":
                        kwargs["queryset"] = City.objects.filter(id=spa_center.city_id)
        
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        """Auto-set country/city for branch managers on create."""
        if not change and not request.user.is_superuser:
            if hasattr(request.user, 'managed_spa_center'):
                spa_center = request.user.managed_spa_center
                if spa_center:
                    obj.country = spa_center.country
                    obj.city = spa_center.city
        super().save_model(request, obj, form, change)

