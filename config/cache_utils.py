"""
Cache utility functions for USH API Backend.

Provides cache key management and invalidation helpers for list endpoints.
Uses Django's cache framework (backed by Redis via django-redis).
"""

import hashlib
import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)

# ============================================================================
# Cache Key Prefixes (one per cacheable model/endpoint)
# ============================================================================
COUNTRY_CACHE_PREFIX = "country_list"
CITY_CACHE_PREFIX = "city_list"
SPECIALTY_CACHE_PREFIX = "specialty_list"
SERVICE_CACHE_PREFIX = "service_list"
SPA_CENTER_CACHE_PREFIX = "spacenter_list"
PRODUCT_CATEGORY_CACHE_PREFIX = "product_category_list"
SPA_PRODUCT_CACHE_PREFIX = "spa_product_list"
ADDON_SERVICE_CACHE_PREFIX = "addon_service_list"

# All prefixes for bulk invalidation
ALL_CACHE_PREFIXES = [
    COUNTRY_CACHE_PREFIX,
    CITY_CACHE_PREFIX,
    SPECIALTY_CACHE_PREFIX,
    SERVICE_CACHE_PREFIX,
    SPA_CENTER_CACHE_PREFIX,
    PRODUCT_CATEGORY_CACHE_PREFIX,
    SPA_PRODUCT_CACHE_PREFIX,
    ADDON_SERVICE_CACHE_PREFIX,
]

# Default cache timeout (15 minutes)
CACHE_TIMEOUT = 900


def build_cache_key(prefix, request):
    """
    Build a unique cache key from the prefix and full request query string.

    Includes path, query params (filters, search, ordering, pagination),
    and Accept-Language header to handle multi-language responses.
    """
    query_string = request.META.get("QUERY_STRING", "")
    language = request.META.get("HTTP_ACCEPT_LANGUAGE", "en")
    path = request.path

    raw = f"{prefix}:{path}:{query_string}:{language}"
    key_hash = hashlib.md5(raw.encode()).hexdigest()
    return f"{prefix}:{key_hash}"


def invalidate_model_cache(prefix):
    """
    Invalidate all cached entries for a given model prefix.

    Uses Django-Redis's delete_pattern to remove all keys matching the prefix.
    """
    pattern = f"*{prefix}:*"
    try:
        cache.delete_pattern(pattern)
        logger.info("Cache invalidated for prefix: %s", prefix)
    except Exception as e:
        logger.warning("Failed to invalidate cache for prefix %s: %s", prefix, e)


def invalidate_all_caches():
    """
    Invalidate all API list caches.
    """
    for prefix in ALL_CACHE_PREFIXES:
        invalidate_model_cache(prefix)
    logger.info("All API caches invalidated.")
