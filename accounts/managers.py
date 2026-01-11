"""
Custom User Manager for Auth Microservice.

Handles user creation with email/phone authentication.
"""

from django.contrib.auth.models import BaseUserManager
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """
    Custom user manager for User model.

    Supports creating users with email or phone number as identifier.
    """

    def create_user(
        self,
        email=None,
        phone_number=None,
        password=None,
        **extra_fields,
    ):
        """
        Create and save a regular user.

        Args:
            email: User's email address (optional if phone provided)
            phone_number: User's phone number (optional if email provided)
            password: User's password
            **extra_fields: Additional fields for the user

        Returns:
            User: The created user instance

        Raises:
            ValueError: If neither email nor phone is provided
        """
        if not email and not phone_number:
            raise ValueError(_("Users must have either an email or phone number"))

        if email:
            email = self.normalize_email(email)

        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("is_active", True)

        user = self.model(
            email=email,
            phone_number=phone_number,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and save a superuser.

        Args:
            email: User's email address (required for superusers)
            password: User's password
            **extra_fields: Additional fields for the user

        Returns:
            User: The created superuser instance

        Raises:
            ValueError: If required superuser flags are not set correctly
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("user_type", "admin")
        extra_fields.setdefault("is_email_verified", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(email=email, password=password, **extra_fields)

    def create_employee(
        self,
        email,
        password=None,
        role=None,
        created_by=None,
        **extra_fields,
    ):
        """
        Create and save an employee user.

        Args:
            email: Employee's email address
            password: Employee's password
            role: Employee's role (branch_manager, country_manager, therapist)
            created_by: Admin user who created this employee
            **extra_fields: Additional fields for the user

        Returns:
            User: The created employee instance
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields["user_type"] = "employee"

        user = self.create_user(email=email, password=password, **extra_fields)

        # Note: Employee profile with role is created via signals
        return user

    def get_by_email_or_phone(self, identifier):
        """
        Get user by email or phone number.

        Args:
            identifier: Email or phone number

        Returns:
            User: The user instance or None
        """
        if "@" in identifier:
            return self.filter(email__iexact=identifier).first()
        return self.filter(phone_number=identifier).first()

    def active_users(self):
        """Return queryset of active users."""
        return self.filter(is_active=True)

    def verified_users(self):
        """Return queryset of verified users."""
        return self.filter(
            is_active=True,
        ).filter(
            models.Q(is_email_verified=True) | models.Q(is_phone_verified=True)
        )

    def employees(self):
        """Return queryset of employee users."""
        return self.filter(user_type="employee", is_active=True)

    def customers(self):
        """Return queryset of customer users."""
        return self.filter(user_type="customer", is_active=True)

    def admins(self):
        """Return queryset of admin users."""
        return self.filter(user_type="admin", is_active=True)
