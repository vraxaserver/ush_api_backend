"""
Custom User Model for Auth Microservice.

Supports three user types: Admin, Employee, Customer
with email/phone registration and social authentication.
"""

import uuid
from datetime import timedelta

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField

from .managers import UserManager


class UserType(models.TextChoices):
    """User type choices."""

    ADMIN = "admin", _("Admin")
    EMPLOYEE = "employee", _("Employee")
    CUSTOMER = "customer", _("Customer")


class EmployeeRole(models.TextChoices):
    """Employee role choices."""

    BRANCH_MANAGER = "branch_manager", _("Branch Manager")
    COUNTRY_MANAGER = "country_manager", _("Country Manager")
    THERAPIST = "therapist", _("Therapist")


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model supporting email/phone authentication.

    Fields:
        - email: Primary identifier (optional if phone provided)
        - phone_number: Alternative identifier (optional if email provided)
        - first_name, last_name: User's name
        - date_of_birth: User's DOB
        - user_type: Admin, Employee, or Customer
        - is_email_verified, is_phone_verified: Verification status
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Authentication fields
    email = models.EmailField(
        _("email address"),
        unique=True,
        null=True,
        blank=True,
        db_index=True,
    )
    phone_number = PhoneNumberField(
        _("phone number"),
        unique=True,
        null=True,
        blank=True,
        db_index=True,
    )

    # Personal information
    first_name = models.CharField(_("first name"), max_length=150)
    last_name = models.CharField(_("last name"), max_length=150)
    date_of_birth = models.DateField(_("date of birth"), null=True, blank=True)

    # User type and role
    user_type = models.CharField(
        _("user type"),
        max_length=20,
        choices=UserType.choices,
        default=UserType.CUSTOMER,
        db_index=True,
    )

    # Verification status
    is_email_verified = models.BooleanField(_("email verified"), default=False)
    is_phone_verified = models.BooleanField(_("phone verified"), default=False)

    # Status flags
    is_active = models.BooleanField(_("active"), default=True)
    is_staff = models.BooleanField(_("staff status"), default=False)

    # Timestamps
    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)
    last_login = models.DateTimeField(_("last login"), null=True, blank=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ["-date_joined"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(email__isnull=False) | models.Q(phone_number__isnull=False),
                name="email_or_phone_required",
            )
        ]

    def __str__(self):
        return self.email or str(self.phone_number) or str(self.id)

    def get_full_name(self):
        """Return the full name of the user."""
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        """Return the first name of the user."""
        return self.first_name

    @property
    def is_admin(self):
        """Check if user is admin."""
        return self.user_type == UserType.ADMIN

    @property
    def is_employee(self):
        """Check if user is employee."""
        return self.user_type == UserType.EMPLOYEE

    @property
    def is_customer(self):
        """Check if user is customer."""
        return self.user_type == UserType.CUSTOMER

    @property
    def is_verified(self):
        """Check if user has at least one verified contact method."""
        return self.is_email_verified or self.is_phone_verified

    def save(self, *args, **kwargs):
        """Override save to handle user type permissions."""
        # Employees and admins can access admin panel
        if self.user_type in [UserType.ADMIN, UserType.EMPLOYEE]:
            self.is_staff = True
        super().save(*args, **kwargs)


class VerificationCode(models.Model):
    """
    Verification codes for email/phone verification.

    Supports both email and SMS verification with expiry and attempt tracking.
    """

    class VerificationType(models.TextChoices):
        """Type of verification."""

        EMAIL = "email", _("Email")
        PHONE = "phone", _("Phone")
        PASSWORD_RESET = "password_reset", _("Password Reset")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="verification_codes",
    )
    code = models.CharField(_("verification code"), max_length=10)
    verification_type = models.CharField(
        _("verification type"),
        max_length=20,
        choices=VerificationType.choices,
    )
    is_used = models.BooleanField(_("is used"), default=False)
    attempts = models.PositiveIntegerField(_("attempts"), default=0)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    expires_at = models.DateTimeField(_("expires at"))

    class Meta:
        verbose_name = _("verification code")
        verbose_name_plural = _("verification codes")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.verification_type} - {self.code}"

    def save(self, *args, **kwargs):
        """Set expiry time if not set."""
        if not self.expires_at:
            from django.conf import settings

            expiry_minutes = getattr(settings, "VERIFICATION_CODE_EXPIRY_MINUTES", 10)
            self.expires_at = timezone.now() + timedelta(minutes=expiry_minutes)
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        """Check if the code is still valid."""
        from django.conf import settings

        max_attempts = getattr(settings, "MAX_VERIFICATION_ATTEMPTS", 5)
        return (
            not self.is_used
            and self.expires_at > timezone.now()
            and self.attempts < max_attempts
        )

    def increment_attempts(self):
        """Increment the attempt counter."""
        self.attempts += 1
        self.save(update_fields=["attempts"])

    def mark_used(self):
        """Mark the code as used."""
        self.is_used = True
        self.save(update_fields=["is_used"])


class SocialAuthProvider(models.Model):
    """
    Track social authentication providers linked to users.

    Provides additional tracking beyond allauth's default.
    """

    class Provider(models.TextChoices):
        """Social auth provider choices."""

        GOOGLE = "google", _("Google")
        FACEBOOK = "facebook", _("Facebook")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="social_providers",
    )
    provider = models.CharField(
        _("provider"),
        max_length=20,
        choices=Provider.choices,
    )
    provider_user_id = models.CharField(_("provider user ID"), max_length=255)
    access_token = models.TextField(_("access token"), blank=True)
    refresh_token = models.TextField(_("refresh token"), blank=True)
    token_expires_at = models.DateTimeField(_("token expires at"), null=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("social auth provider")
        verbose_name_plural = _("social auth providers")
        unique_together = ["user", "provider"]

    def __str__(self):
        return f"{self.user} - {self.provider}"
