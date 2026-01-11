"""
Celery Configuration for Auth Microservice.

Handles async tasks like email and SMS verification.
"""

import os

from celery import Celery

# Set the default Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("auth_service")

# Load config from Django settings
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks in all registered Django apps
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery."""
    print(f"Request: {self.request!r}")
