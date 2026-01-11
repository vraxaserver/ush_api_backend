"""
Admin Configuration for Profiles.

Customizes Django admin for profile management.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import CustomerProfile, EmployeeProfile, EmployeeSchedule


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    """Admin for customer profiles."""

    list_display = [
        "user",
        "city",
        "country",
        "preferred_language",
        "created_at",
    ]
    list_filter = ["country", "preferred_language", "created_at"]
    search_fields = ["user__email", "user__first_name", "user__last_name", "city"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (None, {"fields": ("user",)}),
        (
            _("Profile"),
            {"fields": ("avatar", "bio")},
        ),
        (
            _("Address"),
            {
                "fields": (
                    "address_line_1",
                    "address_line_2",
                    "city",
                    "state",
                    "postal_code",
                    "country",
                )
            },
        ),
        (
            _("Preferences"),
            {"fields": ("preferred_language", "notification_preferences")},
        ),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at")},
        ),
    )


class EmployeeScheduleInline(admin.TabularInline):
    """Inline for employee schedules."""

    model = EmployeeSchedule
    extra = 0


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    """Admin for employee profiles."""

    list_display = [
        "user",
        "role",
        "employee_id",
        "department",
        "branch",
        "is_available",
        "created_at",
    ]
    list_filter = ["role", "department", "branch", "is_available", "created_at"]
    search_fields = [
        "user__email",
        "user__first_name",
        "user__last_name",
        "employee_id",
    ]
    readonly_fields = ["employee_id", "created_at", "updated_at"]
    raw_id_fields = ["user", "manager"]
    inlines = [EmployeeScheduleInline]

    fieldsets = (
        (None, {"fields": ("user", "employee_id")}),
        (
            _("Role & Position"),
            {"fields": ("role", "department", "job_title")},
        ),
        (
            _("Profile"),
            {"fields": ("avatar", "bio")},
        ),
        (
            _("Work Information"),
            {"fields": ("hire_date", "work_location", "manager")},
        ),
        (
            _("Location Assignment"),
            {"fields": ("branch", "region", "country")},
        ),
        (
            _("Contact"),
            {"fields": ("work_phone", "work_email")},
        ),
        (
            _("Qualifications"),
            {"fields": ("certifications", "specializations")},
        ),
        (
            _("Status"),
            {"fields": ("is_available",)},
        ),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at")},
        ),
    )

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return (
            super()
            .get_queryset(request)
            .select_related("user", "manager", "manager__user")
        )


@admin.register(EmployeeSchedule)
class EmployeeScheduleAdmin(admin.ModelAdmin):
    """Admin for employee schedules."""

    list_display = [
        "employee",
        "day_of_week",
        "start_time",
        "end_time",
        "is_working",
    ]
    list_filter = ["day_of_week", "is_working"]
    search_fields = ["employee__user__email", "employee__user__first_name"]
    raw_id_fields = ["employee"]
