"""
Admin Configuration for Auth Microservice.

Customizes Django admin for user and profile management.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _

from spacenter.models import SpaCenter

from .models import SocialAuthProvider, User, UserType, VerificationCode


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom admin for User model."""

    list_display = [
        "phone_number",
        "email",
        "first_name",
        "last_name",
        "user_type",
        "get_groups",
        "is_active",
        "is_verified",
        "date_joined",
    ]
    list_filter = [
        "user_type",
        "groups",
        "is_active",
        "is_staff",
        "is_email_verified",
        "is_phone_verified",
        "date_joined",
    ]
    search_fields = ["email", "phone_number", "first_name", "last_name"]
    ordering = ["-date_joined"]
    filter_horizontal = ("groups", "user_permissions")

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
        (
            _("Group Assignment"),
            {
                "classes": ("wide",),
                "fields": ("groups",),
                "description": _(
                    "Assign user to Admin group for full access."
                ),
            },
        ),
    )

    def get_groups(self, obj):
        """Display user groups."""
        return ", ".join([g.name for g in obj.groups.all()]) or "-"
    
    get_groups.short_description = _("Groups")

    def is_verified(self, obj):
        """Display verification status."""
        return obj.is_email_verified or obj.is_phone_verified

    is_verified.boolean = True
    is_verified.short_description = _("Verified")

    def get_queryset(self, request):
        """Limit queryset based on user type."""
        qs = super().get_queryset(request)
        # Non-superusers can only see non-superusers
        if not request.user.is_superuser:
            return qs.filter(is_superuser=False)
        return qs

    def save_model(self, request, obj, form, change):
        """Auto-assign groups based on user_type."""
        super().save_model(request, obj, form, change)
        
        # Auto-assign groups based on user_type if no groups assigned yet
        if not change and not obj.groups.exists():
            self._auto_assign_group(obj)

    def _auto_assign_group(self, user):
        """Auto-assign user to appropriate group based on user_type."""
        try:
            if user.user_type == UserType.ADMIN:
                admin_group = Group.objects.get(name="Admin")
                user.groups.add(admin_group)
        except Group.DoesNotExist:
            pass  # Groups not set up yet

    def get_fieldsets(self, request, obj=None):
        """Customize fieldsets based on request user permissions."""
        fieldsets = super().get_fieldsets(request, obj)
        
        # Non-superusers cannot see superuser checkbox
        if not request.user.is_superuser:
            new_fieldsets = []
            for name, options in fieldsets:
                fields = list(options.get("fields", []))
                if "is_superuser" in fields:
                    fields.remove("is_superuser")
                new_fieldsets.append((name, {**options, "fields": tuple(fields)}))
            return tuple(new_fieldsets)
        
        return fieldsets

    def has_module_permission(self, request):
        """Determine if user has module permission."""
        return super().has_module_permission(request)


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
