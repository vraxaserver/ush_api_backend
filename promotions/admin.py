"""
Promotions (Gift Cards & Loyalty Program) Admin Configuration.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    GiftCard,
    GiftCardTemplate,
    GiftCardTransaction,
    LoyaltyReward,
    LoyaltyTracker,
)


# =============================================================================
# Gift Card Admin
# =============================================================================

@admin.register(GiftCardTemplate)
class GiftCardTemplateAdmin(admin.ModelAdmin):
    """Admin for GiftCardTemplate model."""

    list_display = [
        "name",
        "amount",
        "currency",
        "validity_days",
        "applicable_to_services",
        "applicable_to_products",
        "country",
        "is_active",
        "sort_order",
        "cards_sold_count",
    ]
    list_filter = [
        "is_active",
        "currency",
        "country",
        "applicable_to_services",
        "applicable_to_products",
    ]
    search_fields = ["name", "description"]
    ordering = ["sort_order", "amount"]
    list_editable = ["is_active", "sort_order"]

    fieldsets = (
        (None, {
            "fields": ("name", "description", "image")
        }),
        ("Value", {
            "fields": ("amount", "currency", "validity_days")
        }),
        ("Applicability", {
            "fields": (
                "applicable_to_services",
                "applicable_to_products",
                "country",
            )
        }),
        ("Display", {
            "fields": ("is_active", "sort_order")
        }),
    )

    def cards_sold_count(self, obj):
        """Display number of gift cards sold from this template."""
        return obj.gift_cards.count()
    cards_sold_count.short_description = "Cards Sold"


class GiftCardTransactionInline(admin.TabularInline):
    """Inline for gift card transactions."""

    model = GiftCardTransaction
    extra = 0
    readonly_fields = [
        "transaction_type",
        "amount",
        "balance_after",
        "user",
        "order_reference",
        "order_type",
        "notes",
        "created_at",
    ]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(GiftCard)
class GiftCardAdmin(admin.ModelAdmin):
    """Admin for GiftCard model."""

    list_display = [
        "code",
        "template",
        "balance_display",
        "status_display",
        "owner",
        "purchased_by",
        "valid_period_display",
        "is_valid_now",
    ]
    list_filter = [
        "status",
        "currency",
        "country",
        "template",
        "is_transferable",
        "applicable_to_services",
        "applicable_to_products",
    ]
    search_fields = [
        "code",
        "recipient_email",
        "recipient_name",
        "owner__email",
        "purchased_by__email",
    ]
    ordering = ["-created_at"]
    readonly_fields = [
        "code",
        "initial_amount",
        "current_balance",
        "purchased_at",
        "activated_at",
        "created_at",
        "updated_at",
    ]
    autocomplete_fields = ["template", "purchased_by", "owner", "country"]
    inlines = [GiftCardTransactionInline]

    fieldsets = (
        ("Card Details", {
            "fields": ("code", "pin", "template")
        }),
        ("Value", {
            "fields": ("initial_amount", "current_balance", "currency")
        }),
        ("Ownership", {
            "fields": (
                "purchased_by",
                "owner",
                "recipient_email",
                "recipient_name",
                "recipient_message",
            )
        }),
        ("Restrictions", {
            "fields": (
                "country",
                "applicable_to_services",
                "applicable_to_products",
                "is_transferable",
            )
        }),
        ("Validity", {
            "fields": ("valid_from", "valid_until")
        }),
        ("Status", {
            "fields": ("status", "payment_reference")
        }),
        ("Timestamps", {
            "fields": (
                "purchased_at",
                "activated_at",
                "created_at",
                "updated_at",
            ),
            "classes": ("collapse",),
        }),
    )

    def balance_display(self, obj):
        """Display balance with visual indicator."""
        percentage = (obj.current_balance / obj.initial_amount * 100) if obj.initial_amount else 0
        if percentage <= 0:
            color = "red"
        elif percentage < 25:
            color = "orange"
        else:
            color = "green"
        return format_html(
            '<span style="color: {};">{} {} / {} {}</span>',
            color,
            obj.currency,
            obj.current_balance,
            obj.currency,
            obj.initial_amount,
        )
    balance_display.short_description = "Balance"

    def status_display(self, obj):
        """Display status with color coding."""
        colors = {
            "pending": "gray",
            "active": "green",
            "partially_used": "blue",
            "fully_used": "orange",
            "expired": "red",
            "cancelled": "black",
        }
        color = colors.get(obj.status, "black")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = "Status"

    def valid_period_display(self, obj):
        """Display validity period."""
        return f"{obj.valid_from.strftime('%Y-%m-%d')} to {obj.valid_until.strftime('%Y-%m-%d')}"
    valid_period_display.short_description = "Valid Period"

    def is_valid_now(self, obj):
        """Display if gift card is currently valid."""
        if obj.is_valid:
            return format_html('<span style="color: green;">✓ Valid</span>')
        return format_html('<span style="color: red;">✗ Invalid</span>')
    is_valid_now.short_description = "Valid Now"

    actions = ["activate_cards", "expire_cards"]

    @admin.action(description="Activate selected gift cards")
    def activate_cards(self, request, queryset):
        count = 0
        for card in queryset.filter(status=GiftCard.Status.PENDING):
            card.activate()
            count += 1
        self.message_user(request, f"{count} gift cards activated.")

    @admin.action(description="Mark selected gift cards as expired")
    def expire_cards(self, request, queryset):
        count = queryset.exclude(
            status__in=[GiftCard.Status.CANCELLED, GiftCard.Status.EXPIRED]
        ).update(status=GiftCard.Status.EXPIRED)
        self.message_user(request, f"{count} gift cards marked as expired.")


@admin.register(GiftCardTransaction)
class GiftCardTransactionAdmin(admin.ModelAdmin):
    """Admin for GiftCardTransaction model."""

    list_display = [
        "gift_card",
        "transaction_type",
        "amount_display",
        "balance_after",
        "user",
        "order_reference",
        "created_at",
    ]
    list_filter = ["transaction_type", "created_at"]
    search_fields = [
        "gift_card__code",
        "user__email",
        "order_reference",
    ]
    ordering = ["-created_at"]
    readonly_fields = [
        "gift_card",
        "transaction_type",
        "amount",
        "balance_after",
        "user",
        "order_reference",
        "order_type",
        "notes",
        "created_at",
    ]

    def amount_display(self, obj):
        """Display amount with color."""
        if obj.amount >= 0:
            return format_html(
                '<span style="color: green;">+{}</span>',
                obj.amount
            )
        return format_html(
            '<span style="color: red;">{}</span>',
            obj.amount
        )
    amount_display.short_description = "Amount"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


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

