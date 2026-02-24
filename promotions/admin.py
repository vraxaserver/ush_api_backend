"""
Promotions (Gift Cards) Admin Configuration.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    GiftCard,
    GiftCardTemplate,
    GiftCardTransaction,
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
