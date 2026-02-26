"""
Promotions (Gift Cards & Loyalty Program) Admin Configuration.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    LoyaltyReward,
    LoyaltyTracker,
)


# =============================================================================
# Loyalty Program Admin
# =============================================================================

class LoyaltyRewardInline(admin.TabularInline):
    """Inline for loyalty rewards within tracker."""

    model = LoyaltyReward
    extra = 0
    readonly_fields = [
        "status",
        "earned_from_booking",
        "redeemed_in_booking",
        "redeemed_at",
        "expires_at",
        "created_at",
    ]
    fields = [
        "status",
        "earned_from_booking",
        "redeemed_in_booking",
        "redeemed_at",
        "expires_at",
        "created_at",
    ]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(LoyaltyTracker)
class LoyaltyTrackerAdmin(admin.ModelAdmin):
    """Admin for LoyaltyTracker – shows loyalty progress per customer per service."""

    list_display = [
        "customer",
        "service",
        "progress_display",
        "booking_count",
        "bookings_required",
        "total_bookings",
        "total_rewards_earned",
        "updated_at",
    ]
    list_filter = [
        "service__spa_center",
        "bookings_required",
    ]
    search_fields = [
        "customer__email",
        "customer__first_name",
        "customer__last_name",
        "service__name",
    ]
    ordering = ["-updated_at"]
    readonly_fields = [
        "customer",
        "service",
        "booking_count",
        "bookings_required",
        "total_bookings",
        "total_rewards_earned",
        "created_at",
        "updated_at",
    ]
    autocomplete_fields = ["customer", "service"]

    fieldsets = (
        ("Tracking", {
            "fields": ("customer", "service")
        }),
        ("Progress", {
            "fields": (
                "booking_count",
                "bookings_required",
                "total_bookings",
                "total_rewards_earned",
            )
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def progress_display(self, obj):
        """Display progress bar towards next reward."""
        pct = obj.progress_percentage
        remaining = obj.bookings_remaining
        if pct >= 100:
            color = "#28a745"
        elif pct >= 60:
            color = "#ffc107"
        else:
            color = "#17a2b8"
        return format_html(
            '<div style="width:120px; background:#e9ecef; border-radius:4px;">'
            '<div style="width:{pct}%; background:{color}; height:18px; '
            'border-radius:4px; text-align:center; color:#fff; font-size:11px; '
            'line-height:18px;">{count}/{required}</div></div>'
            '<small>{remaining} more to earn reward</small>',
            pct=min(pct, 100),
            color=color,
            count=obj.booking_count,
            required=obj.bookings_required,
            remaining=remaining,
        )
    progress_display.short_description = "Progress"

    def has_add_permission(self, request):
        # Trackers are created automatically via the booking flow
        return False


@admin.register(LoyaltyReward)
class LoyaltyRewardAdmin(admin.ModelAdmin):
    """Admin for LoyaltyReward – shows earned free-booking rewards."""

    list_display = [
        "customer",
        "service",
        "status_display",
        "earned_from_booking",
        "redeemed_in_booking",
        "redeemed_at",
        "expires_at",
        "created_at",
    ]
    list_filter = [
        "status",
        "service__spa_center",
    ]
    search_fields = [
        "customer__email",
        "customer__first_name",
        "customer__last_name",
        "service__name",
    ]
    ordering = ["-created_at"]
    readonly_fields = [
        "customer",
        "service",
        "status",
        "earned_from_booking",
        "redeemed_in_booking",
        "redeemed_at",
        "created_at",
        "updated_at",
    ]

    fieldsets = (
        ("Reward", {
            "fields": ("customer", "service", "status")
        }),
        ("Bookings", {
            "fields": ("earned_from_booking", "redeemed_in_booking")
        }),
        ("Dates", {
            "fields": ("redeemed_at", "expires_at", "created_at", "updated_at"),
        }),
    )

    def status_display(self, obj):
        """Display status with color coding."""
        colors = {
            "available": "#28a745",
            "redeemed": "#6c757d",
            "expired": "#dc3545",
            "cancelled": "#343a40",
        }
        color = colors.get(obj.status, "#6c757d")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display(),
        )
    status_display.short_description = "Status"

    actions = ["expire_rewards", "cancel_rewards"]

    @admin.action(description="Mark selected rewards as expired")
    def expire_rewards(self, request, queryset):
        count = queryset.filter(
            status=LoyaltyReward.RewardStatus.AVAILABLE,
        ).update(status=LoyaltyReward.RewardStatus.EXPIRED)
        self.message_user(request, f"{count} rewards marked as expired.")

    @admin.action(description="Cancel selected rewards")
    def cancel_rewards(self, request, queryset):
        count = queryset.filter(
            status=LoyaltyReward.RewardStatus.AVAILABLE,
        ).update(status=LoyaltyReward.RewardStatus.CANCELLED)
        self.message_user(request, f"{count} rewards cancelled.")

    def has_add_permission(self, request):
        # Rewards are created automatically via the loyalty tracker
        return False

