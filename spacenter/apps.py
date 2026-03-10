"""Spacenter app configuration."""

from django.apps import AppConfig


class SpacenterConfig(AppConfig):
    """Configuration for the spacenter app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "spacenter"
    verbose_name = "Spa Centers"

    def ready(self):
        import spacenter.signals  # noqa: F401
