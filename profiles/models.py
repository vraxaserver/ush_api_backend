"""
Profile Models for Auth Microservice.

CustomerProfile: Extended profile for customer users
EmployeeProfile: Extended profile for employee users with roles
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from accounts.models import EmployeeRole


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


class EmployeeProfile(models.Model):
    """
    Extended profile for employee users.

    Includes role and organizational information.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="employee_profile",
    )

    # Role and position
    role = models.CharField(
        _("role"),
        max_length=30,
        choices=EmployeeRole.choices,
        default=EmployeeRole.THERAPIST,
        db_index=True,
    )
    employee_id = models.CharField(
        _("employee ID"),
        max_length=50,
        unique=True,
        null=True,
        blank=True,
    )
    department = models.CharField(_("department"), max_length=100, blank=True)
    job_title = models.CharField(_("job title"), max_length=100, blank=True)

    # Profile fields
    avatar = models.ImageField(
        _("avatar"),
        upload_to="avatars/employees/",
        null=True,
        blank=True,
    )
    bio = models.TextField(_("bio"), blank=True, max_length=500)

    # Work information
    hire_date = models.DateField(_("hire date"), null=True, blank=True)
    work_location = models.CharField(_("work location"), max_length=255, blank=True)

    # Manager relationship (for hierarchy)
    manager = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="direct_reports",
        verbose_name=_("manager"),
    )

    # Branch/Region assignment
    branch = models.CharField(_("branch"), max_length=100, blank=True)
    region = models.CharField(_("region"), max_length=100, blank=True)
    country = models.CharField(_("country"), max_length=100, blank=True)

    # Contact information
    work_phone = models.CharField(_("work phone"), max_length=20, blank=True)
    work_email = models.EmailField(_("work email"), blank=True)

    # Certifications and qualifications (for therapists)
    certifications = models.JSONField(
        _("certifications"),
        default=list,
        blank=True,
    )
    specializations = models.JSONField(
        _("specializations"),
        default=list,
        blank=True,
    )

    # Status
    is_available = models.BooleanField(_("is available"), default=True)

    # Timestamps
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("employee profile")
        verbose_name_plural = _("employee profiles")

    def __str__(self):
        return f"Employee Profile: {self.user.get_full_name()} ({self.get_role_display()})"

    def save(self, *args, **kwargs):
        """Generate employee ID if not set."""
        if not self.employee_id:
            self.employee_id = self._generate_employee_id()
        super().save(*args, **kwargs)

    def _generate_employee_id(self):
        """Generate unique employee ID."""
        import random
        import string

        prefix = self.role[:2].upper() if self.role else "EM"
        suffix = "".join(random.choices(string.digits, k=6))
        return f"{prefix}-{suffix}"

    @property
    def is_manager(self):
        """Check if employee is a manager."""
        return self.role in [
            EmployeeRole.BRANCH_MANAGER,
            EmployeeRole.COUNTRY_MANAGER,
        ]

    @property
    def subordinates_count(self):
        """Return count of direct reports."""
        return self.direct_reports.count()

    def get_team_members(self):
        """Get all team members under this manager."""
        if not self.is_manager:
            return EmployeeProfile.objects.none()
        return self.direct_reports.all()


class EmployeeSchedule(models.Model):
    """
    Work schedule for employees (especially therapists).
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
    employee = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.CASCADE,
        related_name="schedules",
    )
    day_of_week = models.IntegerField(
        _("day of week"),
        choices=DayOfWeek.choices,
    )
    start_time = models.TimeField(_("start time"))
    end_time = models.TimeField(_("end time"))
    is_working = models.BooleanField(_("is working"), default=True)

    class Meta:
        verbose_name = _("employee schedule")
        verbose_name_plural = _("employee schedules")
        unique_together = ["employee", "day_of_week"]
        ordering = ["day_of_week", "start_time"]

    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.get_day_of_week_display()}"
