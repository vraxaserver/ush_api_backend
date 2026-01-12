"""
Spa Center Models.

Models for managing spa centers/branches, services, specialties, and therapist assignments.
Supports multi-language (English, Arabic) via django-modeltranslation.
"""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


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


class Specialty(models.Model):
    """
    Specialty model for therapist specializations.
    
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
    
    # Home service
    is_home_service = models.BooleanField(
        _("available for home service"),
        default=False,
    )
    price_for_home_service = models.DecimalField(
        _("price for home service"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=_("Leave blank to use base price for home service"),
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
    
    # Created by tracking
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_services",
        verbose_name=_("created by"),
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
        return f"{self.name} ({self.city.name}, {self.country.code})"

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
    def home_service_price(self):
        """Get the effective home service price."""
        if self.is_home_service:
            return self.price_for_home_service or self.current_price
        return None


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
    
    # Management
    branch_manager = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_spa_center",
        verbose_name=_("branch manager"),
        limit_choices_to={"user_type": "employee"},
    )
    
    # Services offered at this branch
    services = models.ManyToManyField(
        Service,
        related_name="spa_centers",
        blank=True,
        verbose_name=_("services offered"),
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


class TherapistProfile(models.Model):
    """
    Extended profile for therapist employees.
    
    Links therapists to branches, specialties, and services they can perform.
    Translatable fields: bio
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Link to employee profile
    employee_profile = models.OneToOneField(
        "profiles.EmployeeProfile",
        on_delete=models.CASCADE,
        related_name="therapist_profile",
        verbose_name=_("employee profile"),
    )
    
    # Branch assignment
    spa_center = models.ForeignKey(
        SpaCenter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="therapists",
        verbose_name=_("spa center"),
    )
    
    # Specialties and services
    specialties = models.ManyToManyField(
        Specialty,
        related_name="therapists",
        blank=True,
        verbose_name=_("specialties"),
    )
    services = models.ManyToManyField(
        Service,
        related_name="therapists",
        blank=True,
        verbose_name=_("services can perform"),
    )
    
    # Additional info
    years_of_experience = models.PositiveIntegerField(
        _("years of experience"),
        default=0,
    )
    bio = models.TextField(_("bio"), blank=True)
    
    # Availability
    is_available = models.BooleanField(_("available"), default=True)
    
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("therapist profile")
        verbose_name_plural = _("therapist profiles")

    def __str__(self):
        user = self.employee_profile.user
        return f"Therapist: {user.get_full_name()}"

    @property
    def user(self):
        """Get the associated user."""
        return self.employee_profile.user

    @property
    def country(self):
        """Get the country from the spa center."""
        if self.spa_center:
            return self.spa_center.country
        return None
