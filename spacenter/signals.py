"""
Signals for automatic cache invalidation in the spacenter app.

When any cached model is saved or deleted, the corresponding cache
is cleared so that subsequent API requests return fresh data.
"""

import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from config.cache_utils import (
    ADDON_SERVICE_CACHE_PREFIX,
    CITY_CACHE_PREFIX,
    COUNTRY_CACHE_PREFIX,
    HOME_SERVICE_CACHE_PREFIX,
    PRODUCT_CATEGORY_CACHE_PREFIX,
    SERVICE_CACHE_PREFIX,
    SPA_CENTER_CACHE_PREFIX,
    SPA_PRODUCT_CACHE_PREFIX,
    SPECIALTY_CACHE_PREFIX,
    invalidate_model_cache,
)

from .models import (
    AddOnService,
    BaseProduct,
    City,
    Country,
    HomeService,
    ProductCategory,
    Service,
    ServiceArrangement,
    ServiceImage,
    SpaCenter,
    SpaCenterOperatingHours,
    SpaProduct,
    Specialty,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Country
# ============================================================================
@receiver([post_save, post_delete], sender=Country)
def invalidate_country_cache(sender, **kwargs):
    invalidate_model_cache(COUNTRY_CACHE_PREFIX)
    # Cities and SpaCenters reference countries
    invalidate_model_cache(CITY_CACHE_PREFIX)
    invalidate_model_cache(SPA_CENTER_CACHE_PREFIX)


# ============================================================================
# City
# ============================================================================
@receiver([post_save, post_delete], sender=City)
def invalidate_city_cache(sender, **kwargs):
    invalidate_model_cache(CITY_CACHE_PREFIX)
    # SpaCenters reference cities
    invalidate_model_cache(SPA_CENTER_CACHE_PREFIX)


# ============================================================================
# Specialty
# ============================================================================
@receiver([post_save, post_delete], sender=Specialty)
def invalidate_specialty_cache(sender, **kwargs):
    invalidate_model_cache(SPECIALTY_CACHE_PREFIX)
    # Services reference specialties
    invalidate_model_cache(SERVICE_CACHE_PREFIX)


# ============================================================================
# Service & related
# ============================================================================
@receiver([post_save, post_delete], sender=Service)
def invalidate_service_cache(sender, **kwargs):
    invalidate_model_cache(SERVICE_CACHE_PREFIX)
    # SpaCenters list may include service counts
    invalidate_model_cache(SPA_CENTER_CACHE_PREFIX)


@receiver([post_save, post_delete], sender=ServiceImage)
def invalidate_service_image_cache(sender, **kwargs):
    invalidate_model_cache(SERVICE_CACHE_PREFIX)


@receiver([post_save, post_delete], sender=ServiceArrangement)
def invalidate_service_arrangement_cache(sender, **kwargs):
    invalidate_model_cache(SERVICE_CACHE_PREFIX)
    invalidate_model_cache(SPA_CENTER_CACHE_PREFIX)


# ============================================================================
# SpaCenter & related
# ============================================================================
@receiver([post_save, post_delete], sender=SpaCenter)
def invalidate_spacenter_cache(sender, **kwargs):
    invalidate_model_cache(SPA_CENTER_CACHE_PREFIX)


@receiver([post_save, post_delete], sender=SpaCenterOperatingHours)
def invalidate_operating_hours_cache(sender, **kwargs):
    invalidate_model_cache(SPA_CENTER_CACHE_PREFIX)


# ============================================================================
# AddOnService
# ============================================================================
@receiver([post_save, post_delete], sender=AddOnService)
def invalidate_addon_cache(sender, **kwargs):
    invalidate_model_cache(ADDON_SERVICE_CACHE_PREFIX)


# ============================================================================
# Products
# ============================================================================
@receiver([post_save, post_delete], sender=ProductCategory)
def invalidate_product_category_cache(sender, **kwargs):
    invalidate_model_cache(PRODUCT_CATEGORY_CACHE_PREFIX)


@receiver([post_save, post_delete], sender=BaseProduct)
def invalidate_base_product_cache(sender, **kwargs):
    invalidate_model_cache(SPA_PRODUCT_CACHE_PREFIX)


@receiver([post_save, post_delete], sender=SpaProduct)
def invalidate_spa_product_cache(sender, **kwargs):
    invalidate_model_cache(SPA_PRODUCT_CACHE_PREFIX)


# ============================================================================
# HomeService
# ============================================================================
@receiver([post_save, post_delete], sender=HomeService)
def invalidate_home_service_cache(sender, **kwargs):
    invalidate_model_cache(HOME_SERVICE_CACHE_PREFIX)
