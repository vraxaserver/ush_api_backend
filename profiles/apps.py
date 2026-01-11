"""Profiles app configuration."""

from django.apps import AppConfig


class ProfilesConfig(AppConfig):
    """Configuration for the profiles app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "profiles"
    verbose_name = "User Profiles"
