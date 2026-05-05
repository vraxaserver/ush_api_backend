"""
Admin Configuration for Auth Microservice.

Customizes Django admin for user and profile management.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.contrib.admin.models import LogEntry
from django.utils.translation import gettext_lazy as _
from simple_history.admin import SimpleHistoryAdmin

from spacenter.models import SpaCenter

from .models import DataDeletionRequest, SocialAuthProvider, User, UserType, VerificationCode


@admin.register(User)
class UserAdmin(SimpleHistoryAdmin, BaseUserAdmin):
    """Custom admin for User model."""

    list_display = [
        "phone_number",
        "email",
        "first_name",
        "last_name",
        "user_type",
        "spa_center",
        "get_groups",
        "is_active",
        "is_verified",
        "date_joined",
    ]
    list_filter = [
        "user_type",
        "spa_center",
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
            {"fields": ("user_type", "spa_center")},
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
                    "spa_center",
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


@admin.register(DataDeletionRequest)
class DataDeletionRequestAdmin(admin.ModelAdmin):
    """Admin for user data deletion requests."""

    list_display = [
        "user",
        "status",
        "requested_at",
        "processed_at",
    ]
    list_editable = ["status"]
    list_filter = ["status", "requested_at", "processed_at"]
    search_fields = ["user__email", "user__phone_number", "reason", "notes"]
    readonly_fields = ["requested_at"]
    ordering = ["-requested_at"]
    actions = ["mark_processing", "mark_completed", "mark_cancelled"]

    def mark_processing(self, request, queryset):
        for obj in queryset:
            obj.status = DataDeletionRequest.Status.PROCESSING
            self.save_model(request, obj, None, True)
    mark_processing.short_description = _("Mark selected as Processing")

    def mark_completed(self, request, queryset):
        for obj in queryset:
            obj.status = DataDeletionRequest.Status.COMPLETED
            self.save_model(request, obj, None, True)
    mark_completed.short_description = _("Mark selected as Completed")

    def mark_cancelled(self, request, queryset):
        for obj in queryset:
            obj.status = DataDeletionRequest.Status.CANCELLED
            self.save_model(request, obj, None, True)
    mark_cancelled.short_description = _("Mark selected as Cancelled")
    
    fieldsets = (
        (None, {"fields": ("user", "reason", "status")}),
        (_("Processing"), {"fields": ("processed_at", "notes")}),
        (_("Timestamps"), {"fields": ("requested_at",)}),
    )

    def save_model(self, request, obj, form, change):
        """Handle status changes and user activation."""
        if change:
            # Handle user activation status based on deletion request status
            user = obj.user
            if obj.status == DataDeletionRequest.Status.CANCELLED:
                User.objects.filter(pk=user.pk).update(is_active=True)
            elif obj.status in [DataDeletionRequest.Status.PENDING, DataDeletionRequest.Status.PROCESSING]:
                # If moved back to active request status, ensure user is inactive
                User.objects.filter(pk=user.pk).update(is_active=False)
                
                # Also blacklist tokens if moved back to active request
                try:
                    from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
                    OutstandingToken.objects.filter(user=user).delete()
                except Exception:
                    pass

            # Set processing timestamp
            if obj.status == DataDeletionRequest.Status.COMPLETED and not obj.processed_at:
                obj.processed_at = timezone.now()
        
        super().save_model(request, obj, form, change)


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    """Admin for Django LogEntry to show all admin actions."""

    list_display = [
        "action_time",
        "user",
        "content_type",
        "object_repr",
        "action_flag",
    ]
    list_filter = ["action_time", "action_flag"]
    search_fields = ["object_repr", "change_message"]
    date_hierarchy = "action_time"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# Unregister SimpleJWT Token Blacklist models
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from django.contrib.auth.models import Group
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken

try:
    admin.site.unregister(BlacklistedToken)
    admin.site.unregister(OutstandingToken)
    admin.site.unregister(Group)
    admin.site.unregister(EmailAddress)
    admin.site.unregister(SocialAccount)
    admin.site.unregister(SocialApp)
    admin.site.unregister(SocialToken)
except admin.sites.NotRegistered:
    pass
