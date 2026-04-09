"""
Profile Models for Auth Microservice.

CustomerProfile: Extended profile for customer users
EmployeeProfile: Extended profile for employee users with roles
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Gender(models.TextChoices):
    """Gender choices."""

    MALE = "male", _("Male")
    FEMALE = "female", _("Female")
    OTHER = "other", _("Other")


class CustomerProfile(models.Model):
    """
    Extended profile for customer users.

    Stores additional customer-specific information.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer_profile",
    )

    # Profile fields
    avatar = models.ImageField(
        _("avatar"),
        upload_to="avatars/customers/",
        null=True,
        blank=True,
    )
    bio = models.TextField(_("bio"), blank=True, max_length=500)

    # Address information
    address_line_1 = models.CharField(
        _("address line 1"),
        max_length=255,
        blank=True,
    )
    address_line_2 = models.CharField(
        _("address line 2"),
        max_length=255,
        blank=True,
    )
    city = models.CharField(_("city"), max_length=100, blank=True)
    state = models.CharField(_("state/province"), max_length=100, blank=True)
    postal_code = models.CharField(_("postal code"), max_length=20, blank=True)
    country = models.CharField(_("country"), max_length=100, blank=True)

    # Preferences
    preferred_language = models.CharField(
        _("preferred language"),
        max_length=10,
        default="en",
    )

    gender = models.CharField(
        _("gender"),
        max_length=10,
        choices=Gender.choices,
        default=Gender.MALE,
    )
    dob = models.DateField(_("date of birth"), null=True, blank=True)
    notification_preferences = models.JSONField(
        _("notification preferences"),
        default=dict,
        blank=True,
    )

    # Timestamps
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("customer profile")
        verbose_name_plural = _("customer profiles")

    def __str__(self):
        return f"Customer Profile: {self.user.get_full_name()}"

    @property
    def full_address(self):
        """Return formatted full address."""
        parts = [
            self.address_line_1,
            self.address_line_2,
            self.city,
            self.state,
            self.postal_code,
            self.country,
        ]
        return ", ".join(filter(bool, parts))


class Slide(models.Model):
    """
    Slideshow slide for landing page.

    Stores image, title, description, and link for each slide.
    Supports multi-language for title and description (EN/AR).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    image = models.ImageField(
        _("image"),
        upload_to="slides/",
        null=True,
        blank=True,
        help_text=_("Slide image"),
    )
    title = models.CharField(
        _("title"),
        max_length=255,
        blank=True,
    )
    description = models.TextField(
        _("description"),
        blank=True,
        max_length=500,
    )
    link = models.URLField(
        _("link"),
        max_length=500,
        blank=True,
        help_text=_("URL to navigate to when slide is clicked"),
    )
    order = models.PositiveIntegerField(
        _("order"),
        default=0,
        help_text=_("Display order (lower numbers appear first)"),
    )
    is_active = models.BooleanField(
        _("is active"),
        default=True,
        help_text=_("Only active slides are displayed"),
    )

    # Timestamps
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("slide")
        verbose_name_plural = _("slides")
        ordering = ["order", "-created_at"]

    def __str__(self):
        return self.title or f"Slide {self.order}"
