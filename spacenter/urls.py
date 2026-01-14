"""
Spa Center URL Configuration.

API endpoints for spa centers, services, specialties, cities, therapists, and products.
All endpoints are public (no authentication required).
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AddOnServiceViewSet,
    CityViewSet,
    CountryViewSet,
    ProductCategoryViewSet,
    ServiceViewSet,
    SpaCenterViewSet,
    SpaProductViewSet,
    SpecialtyViewSet,
    TherapistViewSet,
)

app_name = "spacenter"

router = DefaultRouter()
router.register(r"countries", CountryViewSet, basename="country")
router.register(r"cities", CityViewSet, basename="city")
router.register(r"specialties", SpecialtyViewSet, basename="specialty")
router.register(r"add-on-services", AddOnServiceViewSet, basename="addon-service")
router.register(r"services", ServiceViewSet, basename="service")
router.register(r"branches", SpaCenterViewSet, basename="spacenter")
router.register(r"therapists", TherapistViewSet, basename="therapist")
router.register(r"product-categories", ProductCategoryViewSet, basename="product-category")
router.register(r"products", SpaProductViewSet, basename="product")

urlpatterns = [
    path("", include(router.urls)),
]
