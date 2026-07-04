"""
Spa Center Models.

Models for managing spa centers/branches, services, specialties.
Supports multi-language (English, Arabic) via django-modeltranslation.
"""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords


class Country(models.Model):
    """
    Country model for organizing spa centers by location.
    
    Translatable fields: name
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("country name"), max_length=100, unique=True)
    code = models.CharField(
        _("country code"),
        max_length=3,
        unique=True,
        help_text=_("ISO 3166-1 alpha-3 code"),
    )
    phone_code = models.CharField(
        _("phone code"),
        max_length=10,
        blank=True,
        help_text=_("International dialing code (e.g., +1, +971)"),
    )
    flag = models.ImageField(
        _("flag"),
        upload_to="countries/flags/",
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(_("active"), default=True)
    sort_order = models.PositiveIntegerField(_("sort order"), default=0)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("country")
        verbose_name_plural = _("countries")
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class City(models.Model):
    """
    City model linked to countries.
    
    Translatable fields: name
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        related_name="cities",
        verbose_name=_("country"),
    )
    name = models.CharField(_("city name"), max_length=100)
    state = models.CharField(
        _("state/province"),
        max_length=100,
        blank=True,
    )
    is_active = models.BooleanField(_("active"), default=True)
    sort_order = models.PositiveIntegerField(_("sort order"), default=0)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("city")
        verbose_name_plural = _("cities")
        ordering = ["sort_order", "name"]
        unique_together = ["country", "name"]

    def __str__(self):
        return f"{self.name}, {self.country.name}"



class SpaCenter(models.Model):
    """
    Spa Center / Branch model.
    
    Represents a physical spa location with its details and operating hours.
    Translatable fields: name, description, address
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic Information
    name = models.CharField(_("branch name"), max_length=200)
    slug = models.SlugField(_("slug"), max_length=200, unique=True)
    description = models.TextField(_("description"), blank=True)
    image = models.ImageField(
        _("image"),
        upload_to="spacenters/",
        null=True,
        blank=True,
    )
    
    # Location
    country = models.ForeignKey(
        Country,
        on_delete=models.PROTECT,
        related_name="spa_centers",
        verbose_name=_("country"),
    )
    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        related_name="spa_centers",
        verbose_name=_("city"),
    )
    address = models.CharField(_("address"), max_length=500)
    postal_code = models.CharField(_("postal code"), max_length=20, blank=True)
    latitude = models.DecimalField(
        _("latitude"),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    longitude = models.DecimalField(
        _("longitude"),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    
    # Contact Information
    phone = models.CharField(_("phone"), max_length=20, blank=True)
    email = models.EmailField(_("email"), blank=True)
    website = models.URLField(_("website"), blank=True)
    
    # Operating Hours (default times)
    default_opening_time = models.TimeField(
        _("default opening time"),
        default="09:00",
    )
    default_closing_time = models.TimeField(
        _("default closing time"),
        default="21:00",
    )
    
    # Status
    is_active = models.BooleanField(_("active"), default=True)
    on_service = models.BooleanField(
        _("on service"),
        default=True,
        help_text=_("Is currently operational"),
    )
    
    
    sort_order = models.PositiveIntegerField(_("sort order"), default=0)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)



    class Meta:
        verbose_name = _("spa center")
        verbose_name_plural = _("spa centers")
        ordering = ["sort_order", "country", "name"]

    def __str__(self):
        return f"{self.name} - {self.city.name}, {self.country.name}"

    def clean(self):
        """Validate that city belongs to selected country."""
        if self.city_id and self.country_id:
            if self.city.country_id != self.country_id:
                raise ValidationError(
                    {"city": _("Selected city must belong to the selected country.")}
                )

    @property
    def location(self):
        """Return location as dict."""
        if self.latitude and self.longitude:
            return {
                "lat": float(self.latitude),
                "lon": float(self.longitude),
            }
        return None

    @property
    def full_address(self):
        """Return formatted full address."""
        parts = [
            self.address,
            self.city.name if self.city else "",
            self.city.state if self.city and self.city.state else "",
            self.postal_code,
            self.country.name if self.country else "",
        ]
        return ", ".join(filter(bool, parts))


class SpaCenterOperatingHours(models.Model):
    """
    Operating hours for specific days of the week.
    
    Allows customization of hours per day, overriding defaults.
    """

    class DayOfWeek(models.IntegerChoices):
        MONDAY = 0, _("Monday")
        TUESDAY = 1, _("Tuesday")
        WEDNESDAY = 2, _("Wednesday")
        THURSDAY = 3, _("Thursday")
        FRIDAY = 4, _("Friday")
        SATURDAY = 5, _("Saturday")
        SUNDAY = 6, _("Sunday")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    spa_center = models.ForeignKey(
        SpaCenter,
        on_delete=models.CASCADE,
        related_name="operating_hours",
    )
    day_of_week = models.IntegerField(
        _("day of week"),
        choices=DayOfWeek.choices,
    )
    opening_time = models.TimeField(_("opening time"))
    closing_time = models.TimeField(_("closing time"))
    is_closed = models.BooleanField(_("closed"), default=False)

    class Meta:
        verbose_name = _("operating hours")
        verbose_name_plural = _("operating hours")
        unique_together = ["spa_center", "day_of_week"]
        ordering = ["day_of_week"]

    def __str__(self):
        if self.is_closed:
            return f"{self.spa_center.name} - {self.get_day_of_week_display()}: Closed"
        return f"{self.spa_center.name} - {self.get_day_of_week_display()}: {self.opening_time} - {self.closing_time}"



class Specialty(models.Model):
    """    
    Dynamically added by admin (e.g., Swedish Massage, Deep Tissue, Aromatherapy).
    Translatable fields: name, description
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("specialty name"), max_length=100, unique=True)
    description = models.TextField(_("description"), blank=True)
    icon = models.ImageField(
        _("icon"),
        upload_to="specialties/icons/",
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(_("active"), default=True)
    sort_order = models.PositiveIntegerField(_("sort order"), default=0)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("specialty")
        verbose_name_plural = _("specialties")
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class AddOnService(models.Model):
    """
    Add-on service model.
    
    Additional services that can be attached to main services.
    Translatable fields: name, description
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("add-on name"), max_length=150)
    description = models.TextField(_("description"), blank=True)
    
    # Duration and pricing
    duration_minutes = models.PositiveIntegerField(
        _("duration (minutes)"),
        default=15,
        help_text=_("Additional time for this add-on"),
    )
    price = models.DecimalField(
        _("price"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    currency = models.CharField(
        _("currency"),
        max_length=3,
        default="QAR",
    )
    
    # Image
    image = models.ImageField(
        _("image"),
        upload_to="services/addons/",
        null=True,
        blank=True,
    )
    
    is_active = models.BooleanField(_("active"), default=True)
    sort_order = models.PositiveIntegerField(_("sort order"), default=0)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("add-on service")
        verbose_name_plural = _("add-on services")
        ordering = ["sort_order", "name"]

    def __str__(self):
        return f"{self.name} (+{self.duration_minutes} min, {self.currency} {self.price})"


class Service(models.Model):
    """
    Service model for spa services.
    
    Added by admin or branch manager.
    Translatable fields: name, description, ideal_for
    """

    class Currency(models.TextChoices):
        USD = "USD", _("US Dollar")
        AED = "AED", _("UAE Dirham")
        SAR = "SAR", _("Saudi Riyal")
        QAR = "QAR", _("Qatari Riyal")
        KWD = "KWD", _("Kuwaiti Dinar")
        BHD = "BHD", _("Bahraini Dinar")
        OMR = "OMR", _("Omani Rial")
        EUR = "EUR", _("Euro")
        GBP = "GBP", _("British Pound")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("service name"), max_length=150)
    description = models.TextField(_("description"), blank=True)
    
    # Specialty (single foreign key)
    specialty = models.ForeignKey(
        Specialty,
        on_delete=models.PROTECT,
        related_name="services",
        verbose_name=_("specialty"),
    )
    
    # Location - Service belongs to a country and city
    country = models.ForeignKey(
        Country,
        on_delete=models.PROTECT,
        related_name="services",
        verbose_name=_("country"),
    )
    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        related_name="services",
        verbose_name=_("city"),
    )
    
    # Duration and pricing
    duration_minutes = models.PositiveIntegerField(
        _("duration (minutes)"),
        default=60,
    )
    currency = models.CharField(
        _("currency"),
        max_length=3,
        choices=Currency.choices,
        default=Currency.AED,
    )
    base_price = models.DecimalField(
        _("base price"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    discount_price = models.DecimalField(
        _("discount price"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=_("Leave blank if no discount"),
    )

    
    # Gender targeting
    is_for_male = models.BooleanField(
        _("for male"),
        default=False,
    )
    is_for_female = models.BooleanField(
        _("for female"),
        default=True,
    )
    
    # Additional info
    ideal_for = models.CharField(
        _("ideal for"),
        max_length=255,
        blank=True,
        help_text=_("e.g., 'Relaxation', 'Pain Relief', 'Couples'"),
    )
    
    # Benefits as JSON list of key-value pairs
    # Example: [{"key": "Relaxation", "value": "Reduces stress and anxiety"}, ...]
    benefits = models.JSONField(
        _("benefits"),
        default=list,
        blank=True,
        help_text=_("List of benefits as key-value pairs"),
    )

    session_benefits = models.TextField(
        _("session benefits"),
        blank=True,
        null=True,
        default=None,
        help_text=_("Free-text description of session benefits"),
    )
    


    # Spa Center
    spa_center = models.ForeignKey(
        SpaCenter,
        on_delete=models.CASCADE,
        related_name="services",
        verbose_name=_("spa center"),
    )
    
    
    # Loyalty program
    is_eligible_for_loyalty = models.BooleanField(
        _("eligible for loyalty program"),
        default=False,
        help_text=_(
            "If enabled, successful bookings for this service count towards "
            "the loyalty program. After every 5 paid bookings, the customer "
            "earns one free booking of this service."
        ),
    )

    # Booking counter — incremented atomically on each successful payment
    booking_count = models.PositiveIntegerField(
        _("booking count"),
        default=0,
        db_index=True,
        help_text=_("Total number of successful paid bookings for this service."),
    )

    is_active = models.BooleanField(_("active"), default=True)
    sort_order = models.PositiveIntegerField(_("sort order"), default=0)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)



    class Meta:
        verbose_name = _("service")
        verbose_name_plural = _("services")
        ordering = ["sort_order", "name"]

    def __str__(self):
        return f"{self.name} ({self.spa_center.name}, {self.country.code})"

    def clean(self):
        """Validate benefits JSON structure, discount price, and city belongs to country."""
        if self.benefits:
            if not isinstance(self.benefits, list):
                raise ValidationError(
                    {"benefits": _("Benefits must be a list of key-value pairs.")}
                )
            for item in self.benefits:
                if not isinstance(item, dict) or "key" not in item or "value" not in item:
                    raise ValidationError(
                        {"benefits": _("Each benefit must have 'key' and 'value' fields.")}
                    )
        
        # Validate discount price is less than base price
        if self.discount_price and self.base_price:
            if self.discount_price >= self.base_price:
                raise ValidationError(
                    {"discount_price": _("Discount price must be less than base price.")}
                )
        
        # Validate city belongs to country
        if self.city and self.country:
            if self.city.country != self.country:
                raise ValidationError(
                    {"city": _("Selected city does not belong to the selected country.")}
                )

    @property
    def current_price(self):
        """Get the current price (discount price if available, otherwise base price)."""
        if self.discount_price:
            return self.discount_price
        return self.base_price

    @property
    def has_discount(self):
        """Check if service has an active discount."""
        return self.discount_price is not None and self.discount_price < self.base_price

    @property
    def discount_percentage(self):
        """Calculate discount percentage."""
        if self.has_discount:
            discount = ((self.base_price - self.discount_price) / self.base_price) * 100
            return round(discount, 0)
        return 0

    @property
    def add_on_services(self):
        """
        Return the queryset of active add-on services available for this service
        via its spa center's active arrangements.
        """
        from django.db.models import Q
        
        arrangements = ServiceArrangement.objects.filter(
            spa_center=self.spa_center,
            is_active=True
        ).filter(
            Q(allows_all_services=True) | Q(allowed_services=self)
        )
        
        if arrangements.filter(allows_all_add_ons=True).exists():
            return AddOnService.objects.filter(is_active=True)
            
        return AddOnService.objects.filter(
            arrangements__in=arrangements,
            is_active=True
        ).distinct()



class ServiceImage(models.Model):
    """
    Service images model.
    
    Supports up to 3 images per service with minimum 1 required.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name=_("service"),
    )
    image = models.ImageField(
        _("image"),
        upload_to="services/images/",
    )
    alt_text = models.CharField(
        _("alt text"),
        max_length=255,
        blank=True,
    )
    is_primary = models.BooleanField(
        _("primary image"),
        default=False,
    )
    sort_order = models.PositiveIntegerField(_("sort order"), default=0)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("service image")
        verbose_name_plural = _("service images")
        ordering = ["sort_order", "created_at"]

    def __str__(self):
        return f"Image for {self.service.name}"

    def save(self, *args, **kwargs):
        # Ensure only one primary image per service
        if self.is_primary:
            ServiceImage.objects.filter(
                service=self.service,
                is_primary=True,
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)

# =============================================================================
# Product Models
# =============================================================================

class ProductCategory(models.Model):
    """
    Category for spa products.
    
    Examples: Skincare, Body Care, Aromatherapy, Hair Care, Wellness
    Translatable fields: name, description
    Only Admin can add/update/delete.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("category name"), max_length=100, unique=True)
    description = models.TextField(_("description"), blank=True)

    is_active = models.BooleanField(_("active"), default=True)
    sort_order = models.PositiveIntegerField(_("sort order"), default=0)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("product category")
        verbose_name_plural = _("product categories")
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class BaseProduct(models.Model):
    """
    Master product catalog.
    
    Contains product information independent of location.
    Only Admin can add/update/delete.
    Translatable fields: name, short_description
    """

    PRODUCT_TYPE_CHOICES = (
        ("retail", "Retail Product"),
        ("service_addon", "Service Add-on"),
        ("consumable", "Consumable"),
    )

    STATUS_CHOICES = (
        ("active", "Active"),
        ("inactive", "Inactive"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(_("product name"), max_length=255)
    short_description = models.CharField(
        _("short description"),
        max_length=300,
        blank=True,
    )

    product_type = models.CharField(
        _("product type"),
        max_length=20,
        choices=PRODUCT_TYPE_CHOICES,
        default="retail",
    )
    category = models.CharField(
        _("category"),
        max_length=100,
        help_text=_("e.g. Oils, Skincare, Aromatherapy"),
    )
    brand = models.CharField(_("brand"), max_length=100, blank=True)

    sku = models.CharField(
        _("SKU"),
        max_length=100,
        unique=True,
        help_text=_("Stock Keeping Unit"),
    )
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=STATUS_CHOICES,
        default="active",
    )

    image = models.ImageField(
        _("image"),
        upload_to="spa_products/",
        blank=True,
        null=True,
    )

    is_organic = models.BooleanField(_("organic"), default=False)
    is_aromatherapy = models.BooleanField(_("aromatherapy"), default=False)
    suitable_for_sensitive_skin = models.BooleanField(
        _("suitable for sensitive skin"),
        default=False,
    )

    is_featured = models.BooleanField(_("featured"), default=False)
    is_visible = models.BooleanField(_("visible"), default=True)

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("base product")
        verbose_name_plural = _("base products")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["category"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.sku})"

    @property
    def is_active(self):
        """Check if product is active."""
        return self.status == "active"


class SpaProduct(models.Model):
    """
    Stock per product per location.
    
    Links BaseProduct to specific country/city with pricing and inventory.
    Admin and Branch Manager can add/update.
    Branch Manager can only manage products in their branch's location.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    product = models.ForeignKey(
        BaseProduct,
        on_delete=models.CASCADE,
        related_name="stocks",
        verbose_name=_("product"),
    )

    # Location
    country = models.ForeignKey(
        Country,
        on_delete=models.PROTECT,
        related_name="spa_products",
        verbose_name=_("country"),
    )
    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        related_name="spa_products",
        verbose_name=_("city"),
    )

    # Pricing
    price = models.DecimalField(
        _("price"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    discounted_price = models.DecimalField(
        _("discounted price"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    currency = models.CharField(
        _("currency"),
        max_length=10,
        default="QAR",
    )

    # Inventory
    quantity = models.PositiveIntegerField(_("quantity"), default=0)
    reserved_quantity = models.PositiveIntegerField(
        _("reserved quantity"),
        default=0,
        help_text=_("For carts/orders not yet finalized"),
    )
    low_stock_threshold = models.PositiveIntegerField(
        _("low stock threshold"),
        default=5,
    )

    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("spa product")
        verbose_name_plural = _("spa products")
        ordering = ["-updated_at"]
        unique_together = ["product", "country", "city"]

    def __str__(self):
        return f"{self.product.sku} @ {self.city.name}, {self.country.code}: {self.quantity} units"

    def clean(self):
        """Validate city belongs to country."""
        if self.city and self.country:
            if self.city.country != self.country:
                raise ValidationError(
                    {"city": _("Selected city does not belong to the selected country.")}
                )

    @property
    def available_quantity(self):
        """Get available quantity (total - reserved)."""
        return max(0, self.quantity - self.reserved_quantity)

    @property
    def is_in_stock(self):
        """Check if product is in stock."""
        return self.available_quantity > 0

    @property
    def is_low_stock(self):
        """Check if stock is below threshold."""
        return self.available_quantity <= self.low_stock_threshold

    @property
    def current_price(self):
        """Get current price (discounted if available)."""
        if self.discounted_price:
            return self.discounted_price
        return self.price

    @property
    def has_discount(self):
        """Check if product has an active discount."""
        return self.discounted_price is not None and self.discounted_price < self.price

    @property
    def discount_percentage(self):
        """Calculate discount percentage."""
        if self.has_discount:
            discount = ((self.price - self.discounted_price) / self.price) * 100
            return round(discount, 0)
        return 0

    @property
    def stock_status(self):
        """Get stock status string."""
        if self.available_quantity == 0:
            return "out_of_stock"
        elif self.is_low_stock:
            return "low_stock"
        return "in_stock"


# =============================================================================
# Room Model
# =============================================================================


class Room(models.Model):
    """
    Physical room / treatment space within a Spa Center.

    Each Room has a unique identifier (room_id) within its spa center and
    can be configured for multiple service arrangements simultaneously.
    A room can serve different arrangement types concurrently (e.g. a
    large room configured as both single-room and couple-room — each
    arrangement is booked independently).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    spa_center = models.ForeignKey(
        SpaCenter,
        on_delete=models.CASCADE,
        related_name="rooms",
        verbose_name=_("spa center"),
    )
    room_id = models.CharField(
        _("room ID"),
        max_length=50,
        help_text=_(
            "Unique identifier for this room within the spa center (e.g. 'A1', 'VIP-01')."
        ),
    )
    name = models.CharField(_("room name"), max_length=100)
    description = models.TextField(_("description"), blank=True)
    is_active = models.BooleanField(_("active"), default=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("room")
        verbose_name_plural = _("rooms")
        unique_together = [("spa_center", "room_id")]
        ordering = ["spa_center", "room_id"]
        indexes = [
            models.Index(fields=["spa_center", "is_active"]),
        ]

    def __str__(self):
        return f"{self.spa_center.name} — {self.room_id} ({self.name})"


# =============================================================================
# Service Arrangement Model
# =============================================================================


class ServiceArrangement(models.Model):
    """
    Configuration for how a Room is set up to deliver spa services.

    Each arrangement belongs to a Room and defines:
    - The type of setup (single, couple, group, etc.)
    - Which services can be booked here (all or a whitelist)
    - Which add-on services are available (all, or filtered from service-level add-ons)
    - Pricing and cleanup duration

    Multiple arrangements can exist for the same Room (e.g. the same physical
    room configured as a single-room setup AND a couple-room setup).
    Each arrangement is booked independently and can run concurrently in the
    same room (user-confirmed behaviour).

    Backwards compatibility: The legacy `service` FK and `room_count` fields are
    retained so existing data and queries continue to work during migration.
    """

    class ArrangementType(models.TextChoices):
        SINGLE_ROOM = "single_room", _("Single Room")
        COUPLE_ROOM = "couple_room", _("Couple Room")
        GROUP_ROOM = "group_room", _("Group Room")
        OPEN_AREA = "open_area", _("Open Area")
        VIP_SUITE = "vip_suite", _("VIP Suite")
        OUTDOOR_ARRANGEMENT = "outdoor_arrangement", _("Outdoor Arrangement")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # ------------------------------------------------------------------
    # Room association — the physical space this arrangement belongs to
    # ------------------------------------------------------------------
    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name="arrangements",
        verbose_name=_("room"),
        null=False,
        blank=False,
        help_text=_(
            "The physical room this arrangement belongs to. "
            "Capacity is 1 (one session per arrangement)."
        ),
    )

    spa_center = models.ForeignKey(
        SpaCenter,
        on_delete=models.CASCADE,
        related_name="service_arrangements",
        verbose_name=_("spa center"),
    )

    # ------------------------------------------------------------------
    # Service whitelist
    # ------------------------------------------------------------------
    allows_all_services = models.BooleanField(
        _("allows all services"),
        default=True,
        help_text=_(
            "If True, any active service offered by this spa center can be "
            "booked in this arrangement. If False, only services listed in "
            "'Allowed services' are accepted."
        ),
    )
    allowed_services = models.ManyToManyField(
        Service,
        blank=True,
        related_name="whitelisted_arrangements",
        verbose_name=_("allowed services"),
        help_text=_(
            "Specific services that can use this arrangement. "
            "Relevant only when 'Allows all services' is False."
        ),
    )

    # ------------------------------------------------------------------
    # Add-on services — owned by the arrangement, not by the service
    # ------------------------------------------------------------------
    allows_all_add_ons = models.BooleanField(
        _("allows all add-ons"),
        default=True,
        help_text=_(
            "If True, all active add-ons in 'Allowed add-on services' are "
            "available for bookings in this arrangement. "
            "If False, add-ons must be explicitly listed below."
        ),
    )
    allowed_add_on_services = models.ManyToManyField(
        AddOnService,
        blank=True,
        related_name="arrangements",
        verbose_name=_("allowed add-on services"),
        help_text=_(
            "Add-on services available for bookings in this arrangement. "
            "When 'Allows all add-ons' is True, all active entries here are "
            "offered. When False, only those explicitly listed are offered."
        ),
    )

    arrangement_type = models.CharField(
        _("arrangement type"),
        max_length=25,
        choices=ArrangementType.choices,
        default=ArrangementType.SINGLE_ROOM,
    )

    arrangement_label = models.CharField(
        _("arrangement label"),
        max_length=100,
        help_text=_("Display label for this arrangement"),
    )

    # Cleanup time after each session (in minutes)
    cleanup_duration = models.PositiveIntegerField(
        _("cleanup duration (minutes)"),
        default=15,
        help_text=_("Time needed to clean/prepare the room after the service"),
    )

    # Per-arrangement pricing
    base_price = models.DecimalField(
        _("base price"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_("Base price for this arrangement type"),
    )
    discount_price = models.DecimalField(
        _("discount price"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=_("Discounted price if applicable"),
    )

    # Extra minutes
    extra_minutes = models.CharField(
        _("extra minutes"),
        max_length=10,
        choices=[
            ("0", _("No extra time")),
            ("15", _("15 minutes")),
            ("30", _("30 minutes")),
            ("45", _("45 minutes")),
            ("60", _("60 minutes")),
        ],
        default="0",
    )
    price_for_extra_minutes = models.DecimalField(
        _("price for extra minutes"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=_("Leave blank to use base price for extra minutes"),
    )

    is_active = models.BooleanField(_("active"), default=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = _("service arrangement")
        verbose_name_plural = _("service arrangements")
        # Removed `service` from unique_together — service is now a whitelist (M2M)
        unique_together = [["spa_center", "arrangement_type", "arrangement_label"]]
        ordering = ["spa_center", "arrangement_type"]
        indexes = [
            models.Index(fields=["spa_center", "is_active"]),
            models.Index(fields=["room", "is_active"]),
            models.Index(fields=["spa_center", "arrangement_type", "is_active"]),
        ]

    def __str__(self):
        return f"{self.spa_center.name} [{self.room.room_id}] - {self.arrangement_label}"

    def clean(self):
        """Validate room belongs to spa center and discount price."""
        # Room must belong to the same spa center
        if self.room and self.room.spa_center_id != self.spa_center_id:
            raise ValidationError({
                "room": _(
                    "The selected room does not belong to the selected spa center."
                )
            })

        if self.discount_price and self.base_price:
            if self.discount_price >= self.base_price:
                raise ValidationError({
                    "discount_price": _("Discount price must be less than base price.")
                })

    # ------------------------------------------------------------------
    # Capacity
    # ------------------------------------------------------------------

    @property
    def capacity(self) -> int:
        """Number of concurrent bookings this arrangement can handle (always 1 per room)."""
        return 1

    # ------------------------------------------------------------------
    # Service / add-on helpers
    # ------------------------------------------------------------------

    def is_service_allowed(self, service) -> bool:
        """
        Return True if *service* can be booked in this arrangement.
        """
        if self.allows_all_services:
            return True
        return self.allowed_services.filter(pk=service.pk).exists()

    def get_effective_add_on_services(self, service=None):
        """
        Return the queryset of add-on services available for a booking.

        Add-ons are now owned by the arrangement (not the service).
        When ``allows_all_add_ons`` is True, all active add-ons are returned.
        When False, only the explicitly listed add-ons are returned (still filtered
        to active ones).
        """
        if self.allows_all_add_ons:
            return AddOnService.objects.filter(is_active=True)
        return self.allowed_add_on_services.filter(is_active=True)


    # ------------------------------------------------------------------
    # Pricing helpers
    # ------------------------------------------------------------------

    @property
    def total_service_duration(self):
        """Total duration including legacy service + cleanup (if service FK is set)."""
        if self.service:
            return self.service.duration_minutes + self.cleanup_duration
        return self.cleanup_duration

    @property
    def current_price(self):
        """Get the current price (discount price if available, otherwise base price)."""
        if self.discount_price:
            return self.discount_price
        return self.base_price

    @property
    def has_discount(self):
        """Check if arrangement has an active discount."""
        return self.discount_price is not None and self.discount_price < self.base_price

    @property
    def discount_percentage(self):
        """Calculate discount percentage."""
        if self.has_discount:
            discount = ((self.base_price - self.discount_price) / self.base_price) * 100
            return round(discount, 0)
        return 0



# =============================================================================
# Home Service Model
# =============================================================================

class HomeService(models.Model):
    """
    Home Service model.

    Represents services that can be provided at the customer's home/location.
    Translatable fields: name, description
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("service name"), max_length=200)
    description = models.TextField(_("description"), blank=True)

    # Specialty
    specialty = models.ForeignKey(
        Specialty,
        on_delete=models.PROTECT,
        related_name="home_services",
        verbose_name=_("specialty"),
    )

    # Location
    country = models.ForeignKey(
        Country,
        on_delete=models.PROTECT,
        related_name="home_services",
        verbose_name=_("country"),
    )
    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        related_name="home_services",
        verbose_name=_("city"),
    )

    # Duration and pricing
    duration_minutes = models.PositiveIntegerField(
        _("duration (minutes)"),
        default=60,
    )
    price = models.DecimalField(
        _("price"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    discount_price = models.DecimalField(
        _("discount price"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=_("Leave blank if no discount"),
    )

    # Gender targeting
    is_for_male = models.BooleanField(
        _("for male"),
        default=False,
    )
    is_for_female = models.BooleanField(
        _("for female"),
        default=True,
    )

    # Image
    image = models.ImageField(
        _("image"),
        upload_to="home_services/",
        null=True,
        blank=True,
    )


    is_active = models.BooleanField(_("active"), default=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("home service")
        verbose_name_plural = _("home services")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.city.name}, {self.country.name})"

    def clean(self):
        """Validate discount price and city belongs to country."""
        if self.discount_price and self.price:
            if self.discount_price >= self.price:
                raise ValidationError(
                    {"discount_price": _("Discount price must be less than price.")}
                )

        if self.city and self.country:
            if self.city.country != self.country:
                raise ValidationError(
                    {"city": _("Selected city does not belong to the selected country.")}
                )

    @property
    def current_price(self):
        """Get the current price (discount price if available, otherwise price)."""
        if self.discount_price:
            return self.discount_price
        return self.price

    @property
    def has_discount(self):
        """Check if service has an active discount."""
        return self.discount_price is not None and self.discount_price < self.price

    @property
    def discount_percentage(self):
        """Calculate discount percentage."""
        if self.has_discount:
            discount = ((self.price - self.discount_price) / self.price) * 100
            return round(discount, 0)
        return 0
