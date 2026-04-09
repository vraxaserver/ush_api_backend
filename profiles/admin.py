"""
Admin Configuration for Profiles.

Customizes Django admin for profile management.
"""

from django.contrib import admin
from django.db import models
from django.utils.translation import gettext_lazy as _
from modeltranslation.admin import TranslationAdmin

from .models import CustomerProfile, Slide


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    """Admin for customer profiles."""

    list_display = [
        "user",
        "city",
        "country",
        "gender",
        "dob",
        "preferred_language",
        "created_at",
    ]
    list_filter = ["country", "gender", "preferred_language", "created_at"]
    search_fields = ["user__email", "user__first_name", "user__last_name", "city"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (None, {"fields": ("user",)}),
        (
            _("Profile"),
            {"fields": ("avatar", "bio", "gender", "dob")},
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

