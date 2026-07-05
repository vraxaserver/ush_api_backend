"""
Cache utility functions for USH API Backend.

Provides cache key management, invalidation helpers, and a reusable
ViewSet mixin for DRY cache-first list + retrieve handling.
Uses Django's cache framework (backed by Redis).
"""

import hashlib
import logging

from django.core.cache import cache
from rest_framework.response import Response

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
HOME_SERVICE_CACHE_PREFIX = "home_service_list"

# Sub-resource / action-level cache prefixes
SERVICE_ARRANGEMENTS_CACHE_PREFIX = "service_arrangements"
BRANCH_SERVICES_CACHE_PREFIX = "branch_services"

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
    HOME_SERVICE_CACHE_PREFIX,
    SERVICE_ARRANGEMENTS_CACHE_PREFIX,
    BRANCH_SERVICES_CACHE_PREFIX,
]

# Default cache timeout (15 minutes)
CACHE_TIMEOUT = 900


# ============================================================================
# Cache Key Builders
# ============================================================================

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


def build_retrieve_cache_key(prefix, pk):
    """
    Build a cache key for a single-object retrieve (GET /resource/{pk}/).

    Uses the prefix + pk so each object has its own cache slot.
    """
    return f"{prefix}:retrieve:{pk}"


def build_id_cache_key(prefix, identifier, request):
    """
    Build a cache key for a sub-resource or @action endpoint scoped to an ID.

    Example uses:
    - Branch services:  build_id_cache_key(BRANCH_SERVICES_CACHE_PREFIX, branch_pk, request)
    - Arrangements:     build_id_cache_key(SERVICE_ARRANGEMENTS_CACHE_PREFIX, service_id, request)
    - City by-country:  build_id_cache_key(CITY_CACHE_PREFIX, country_code, request)

    The identifier (branch pk, service id, country code, etc.) is embedded in
    the key so that each object gets its own cache slot while still respecting
    query-string variations (filters, pagination, language).
    """
    query_string = request.META.get("QUERY_STRING", "")
    language = request.META.get("HTTP_ACCEPT_LANGUAGE", "en")

    raw = f"{prefix}:{identifier}:{query_string}:{language}"
    key_hash = hashlib.md5(raw.encode()).hexdigest()
    return f"{prefix}:{identifier}:{key_hash}"


# ============================================================================
# Cache Invalidation
# ============================================================================

def invalidate_model_cache(prefix):
    """
    Invalidate all cached entries.

    Note: Django's built-in RedisCache does not support pattern-based
    deletion, so we clear the full cache. This is acceptable because
    only public read data is cached, and cache misses are cheap.
    """
    try:
        cache.clear()
        logger.info("Entire cache cleared (triggered by prefix: %s)", prefix)
    except Exception as e:
        logger.warning("Failed to clear cache: %s", e)


def invalidate_all_caches():
    """
    Invalidate all API list caches by clearing the entire cache store.
    """
    try:
        cache.clear()
        logger.info("All API caches invalidated.")
    except Exception as e:
        logger.warning("Failed to invalidate all caches: %s", e)


# ============================================================================
# Reusable Cache Mixin for DRF ViewSets
# ============================================================================

class CachedListRetrieveMixin:
    """
    A DRF ViewSet mixin that adds cache-first logic to `list` and `retrieve`.

    Usage:
        class MyViewSet(CachedListRetrieveMixin, viewsets.ModelViewSet):
            CACHE_PREFIX = "my_model_list"

    Behaviour:
    - list():     cache_key = prefix + path + query string + Accept-Language
    - retrieve(): cache_key = prefix + "retrieve:" + pk

    Both write back to cache on a DB miss with CACHE_TIMEOUT seconds TTL.
    """

    # Subclasses must set this to one of the *_CACHE_PREFIX constants above.
    CACHE_PREFIX: str = ""

    def list(self, request, *args, **kwargs):
        if not self.CACHE_PREFIX:
            return super().list(request, *args, **kwargs)

        cache_key = build_cache_key(self.CACHE_PREFIX, request)
        cached = cache.get(cache_key)
        if cached is not None:
            logger.debug("Cache HIT  list  key=%s", cache_key)
            return Response(cached)

        logger.debug("Cache MISS list  key=%s", cache_key)
        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, CACHE_TIMEOUT)
        return response

    def retrieve(self, request, *args, **kwargs):
        if not self.CACHE_PREFIX:
            return super().retrieve(request, *args, **kwargs)

        pk = kwargs.get("pk") or kwargs.get("id")
        cache_key = build_retrieve_cache_key(self.CACHE_PREFIX, pk)
        cached = cache.get(cache_key)
        if cached is not None:
            logger.debug("Cache HIT  retrieve  key=%s", cache_key)
            return Response(cached)

        logger.debug("Cache MISS retrieve  key=%s", cache_key)
        response = super().retrieve(request, *args, **kwargs)
        cache.set(cache_key, response.data, CACHE_TIMEOUT)
        return response
