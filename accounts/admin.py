"""
Admin Configuration for Auth Microservice.

Customizes Django admin for user and profile management.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import SocialAuthProvider, User, VerificationCode


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom admin for User model."""

    list_display = [
        "phone_number",
        "email",
        "first_name",
        "last_name",
        "user_type",
        "is_active",
        "is_verified",
        "date_joined",
    ]
    list_filter = [
        "user_type",
        "is_active",
        "is_staff",
        "is_email_verified",
        "is_phone_verified",
        "date_joined",
    ]
    search_fields = ["email", "phone_number", "first_name", "last_name"]
    ordering = ["-date_joined"]

    fieldsets = (
        (None, {"fields": ("email", "phone_number", "password")}),
        (
            _("Personal info"),
            {"fields": ("first_name", "last_name", "date_of_birth")},
        ),
        (
            _("User Type"),
            {"fields": ("user_type",)},
        ),
        (
            _("Verification"),
            {"fields": ("is_email_verified", "is_phone_verified")},
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "phone_number",
                    "first_name",
                    "last_name",
                    "user_type",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    def is_verified(self, obj):
        """Display verification status."""
        return obj.is_email_verified or obj.is_phone_verified

    is_verified.boolean = True
    is_verified.short_description = _("Verified")

    def get_queryset(self, request):
        """Limit queryset based on user type."""
        qs = super().get_queryset(request)
        # Non-superusers can only see users they manage
        if not request.user.is_superuser:
            if request.user.user_type == "admin":
                return qs
            # Employees can only see customers in their scope
            return qs.filter(user_type="customer")
        return qs


@admin.register(VerificationCode)
class VerificationCodeAdmin(admin.ModelAdmin):
    """Admin for verification codes."""

    list_display = [
        "user",
        "verification_type",
        "code",
        "is_used",
        "attempts",
        "created_at",
        "expires_at",
    ]
    list_filter = ["verification_type", "is_used", "created_at"]
    search_fields = ["user__email", "user__phone_number", "code"]
    readonly_fields = ["code", "created_at"]
    ordering = ["-created_at"]


@admin.register(SocialAuthProvider)
class SocialAuthProviderAdmin(admin.ModelAdmin):
    """Admin for social auth providers."""

    list_display = ["user", "provider", "created_at"]
    list_filter = ["provider", "created_at"]
    search_fields = ["user__email", "provider_user_id"]
    readonly_fields = ["provider_user_id", "created_at", "updated_at"]
