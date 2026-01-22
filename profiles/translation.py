"""
Model Translation Configuration for Profiles.

Defines which fields are translatable for multi-language support (English, Arabic).
Uses django-modeltranslation.
"""

from modeltranslation.translator import TranslationOptions, register

from .models import Slide


@register(Slide)
class SlideTranslationOptions(TranslationOptions):
    """Translation options for Slide model."""

    fields = ("title", "description")
