"""
Admin Configuration for Profiles.

Customizes Django admin for profile management.
"""

from django.contrib import admin
from django.db import models
from django.utils.translation import gettext_lazy as _
from modeltranslation.admin import TranslationAdmin

from .models import CustomerProfile, EmployeeProfile, EmployeeSchedule, Slide


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
    list_filter = ["role", "department", "is_available", "created_at"]
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
        """Optimize queryset and filter for managers."""
        qs = super().get_queryset(request).select_related("user", "manager", "manager__user")
        
        # Superusers see everything
        if request.user.is_superuser:
            return qs
            
        # Branch Managers see employees in their branch
        if hasattr(request.user, 'managed_spa_center') and request.user.managed_spa_center:
            spa_center = request.user.managed_spa_center
            # Filter by branch name matching spa center name
            # Also include employees who report to this manager directly
            return qs.filter(
                models.Q(branch__iexact=spa_center.name) | 
                models.Q(manager__user=request.user)
            )
            
        return qs


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


@admin.register(Slide)
class SlideAdmin(TranslationAdmin):
    """Admin for slideshow slides with translation support."""

    list_display = [
        "title",
        "order",
        "is_active",
        "created_at",
        "updated_at",
    ]
    list_filter = ["is_active", "created_at"]
    search_fields = ["title", "title_en", "title_ar", "description"]
    list_editable = ["order", "is_active"]
    ordering = ["order", "-created_at"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (_("English"), {
            "fields": ("title_en", "description_en")
        }),
        (_("Arabic"), {
            "fields": ("title_ar", "description_ar"),
            "classes": ("collapse",)
        }),
        (_("Media & Link"), {
            "fields": ("image", "link")
        }),
        (_("Display Settings"), {
            "fields": ("order", "is_active")
        }),
        (_("Timestamps"), {
            "fields": ("created_at", "updated_at")
        }),
    )

