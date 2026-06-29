"""
pytest conftest.py — project-level test configuration.

Overrides settings that would cause tests to be slow or fail in environments
where external services (Redis, S3, AWS SES) are not running.
"""
import pytest


@pytest.fixture(autouse=True)
def use_fast_test_settings(settings):
    """
    Override external service settings so tests run fast without network calls.

    Without these overrides:
    - Every cache.clear() call times out connecting to Redis (~3 seconds per call)
    - Every User.create_user() triggers an AWS SES email that times out (~3 seconds)
    """
    # DummyCache: no Redis needed, cache operations are no-ops
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.dummy.DummyCache",
        }
    }
    # Use in-memory email backend: no network calls to AWS SES
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    # Run Celery tasks synchronously and eagerly (no broker needed)
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
