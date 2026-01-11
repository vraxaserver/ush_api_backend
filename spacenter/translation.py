"""
Model Translation Configuration for Spa Center.

Defines which fields are translatable for multi-language support (English, Arabic).
Uses django-modeltranslation.
"""

from modeltranslation.translator import TranslationOptions, register

from .models import (
    City,
    Country,
    Service,
    SpaCenter,
    Specialty,
    TherapistProfile,
)


@register(Country)
class CountryTranslationOptions(TranslationOptions):
    """Translation options for Country model."""
    
    fields = ("name",)


@register(City)
class CityTranslationOptions(TranslationOptions):
    """Translation options for City model."""
    
    fields = ("name", "state")


@register(Specialty)
class SpecialtyTranslationOptions(TranslationOptions):
    """Translation options for Specialty model."""
    
    fields = ("name", "description")


@register(Service)
class ServiceTranslationOptions(TranslationOptions):
    """Translation options for Service model."""
    
    fields = ("name", "description", "ideal_for")


@register(SpaCenter)
class SpaCenterTranslationOptions(TranslationOptions):
    """Translation options for SpaCenter model."""
    
    fields = ("name", "description", "address")


@register(TherapistProfile)
class TherapistProfileTranslationOptions(TranslationOptions):
    """Translation options for TherapistProfile model."""
    
    fields = ("bio",)
