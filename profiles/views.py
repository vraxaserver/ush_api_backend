"""
Views for Profile Management.

Handles customer and employee profile CRUD operations.
"""

import logging

from django.shortcuts import get_object_or_404
from rest_framework import filters, generics, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from accounts.permissions import (
    IsAdminUser,
    IsOwnerOrAdmin,
)

from .models import CustomerProfile, Slide
from .serializers import (
    CustomerProfileSerializer,
    CustomerProfileUpdateSerializer,
    SlideSerializer,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Customer Profile Views
# ============================================================================


class CustomerProfileView(generics.RetrieveUpdateAPIView):
    """
    Get/update current customer's profile.

    GET /api/v1/profiles/customer/me/
    PUT/PATCH /api/v1/profiles/customer/me/
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return CustomerProfileUpdateSerializer
        return CustomerProfileSerializer

    def get_object(self):
        """Get current user's customer profile."""
        user = self.request.user
        from accounts.models import UserType
        if user.user_type != UserType.CUSTOMER:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Only customers can access this endpoint.")

        profile, _ = CustomerProfile.objects.get_or_create(user=user)
        return profile



# ============================================================================
# Public Slideshow Views
# ============================================================================


class SlideListView(generics.ListAPIView):
    """
    List active slides for landing page slideshow (public endpoint).

    GET /api/v1/profiles/slides/
    """

    serializer_class = SlideSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        """Return active slides ordered by order field."""
        return Slide.objects.filter(is_active=True)
