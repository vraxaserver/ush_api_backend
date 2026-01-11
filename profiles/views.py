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

from accounts.models import EmployeeRole, UserType
from accounts.permissions import (
    IsAdminUser,
    IsEmployeeUser,
    IsOwnerOrAdmin,
)

from .models import CustomerProfile, EmployeeProfile, EmployeeSchedule
from .serializers import (
    CustomerProfileSerializer,
    CustomerProfileUpdateSerializer,
    EmployeeListSerializer,
    EmployeeProfileAdminSerializer,
    EmployeeProfileSerializer,
    EmployeeProfileUpdateSerializer,
    EmployeeScheduleSerializer,
    TherapistSerializer,
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
        if user.user_type != UserType.CUSTOMER:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Only customers can access this endpoint.")

        profile, _ = CustomerProfile.objects.get_or_create(user=user)
        return profile


# ============================================================================
# Employee Profile Views
# ============================================================================


class EmployeeProfileView(generics.RetrieveUpdateAPIView):
    """
    Get/update current employee's profile.

    GET /api/v1/profiles/employee/me/
    PUT/PATCH /api/v1/profiles/employee/me/
    """

    permission_classes = [permissions.IsAuthenticated, IsEmployeeUser]

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return EmployeeProfileUpdateSerializer
        return EmployeeProfileSerializer

    def get_object(self):
        """Get current user's employee profile."""
        user = self.request.user
        if user.user_type not in [UserType.EMPLOYEE, UserType.ADMIN]:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Only employees can access this endpoint.")

        profile, _ = EmployeeProfile.objects.get_or_create(user=user)
        return profile


class EmployeeProfileAdminViewSet(ModelViewSet):
    """
    Admin viewset for managing employee profiles.

    GET /api/v1/profiles/admin/employees/
    GET /api/v1/profiles/admin/employees/{id}/
    PUT/PATCH /api/v1/profiles/admin/employees/{id}/
    """

    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        "user__email",
        "user__first_name",
        "user__last_name",
        "employee_id",
    ]
    ordering_fields = ["created_at", "role", "branch"]
    ordering = ["-created_at"]

    def get_queryset(self):
        """Return all employee profiles with optional filtering."""
        queryset = EmployeeProfile.objects.select_related("user", "manager")

        # Filter by role
        role = self.request.query_params.get("role")
        if role:
            queryset = queryset.filter(role=role)

        # Filter by branch
        branch = self.request.query_params.get("branch")
        if branch:
            queryset = queryset.filter(branch__icontains=branch)

        # Filter by availability
        available = self.request.query_params.get("available")
        if available is not None:
            queryset = queryset.filter(is_available=available.lower() == "true")

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return EmployeeListSerializer
        elif self.action in ["update", "partial_update"]:
            return EmployeeProfileAdminSerializer
        return EmployeeProfileSerializer

    @action(detail=True, methods=["post"])
    def assign_manager(self, request, pk=None):
        """Assign a manager to an employee."""
        profile = self.get_object()
        manager_id = request.data.get("manager_id")

        if not manager_id:
            return Response(
                {"error": "manager_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            manager = EmployeeProfile.objects.get(id=manager_id)
            if not manager.is_manager:
                return Response(
                    {"error": "Selected employee is not a manager"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            profile.manager = manager
            profile.save(update_fields=["manager"])
            return Response({"message": "Manager assigned successfully"})
        except EmployeeProfile.DoesNotExist:
            return Response(
                {"error": "Manager not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=True, methods=["post"])
    def change_role(self, request, pk=None):
        """Change an employee's role."""
        profile = self.get_object()
        new_role = request.data.get("role")

        if new_role not in [choice[0] for choice in EmployeeRole.choices]:
            return Response(
                {"error": "Invalid role"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        profile.role = new_role
        profile.save(update_fields=["role"])

        # Update user's group
        from accounts.signals import assign_employee_group

        profile.user.groups.clear()
        assign_employee_group(profile.user, new_role)

        return Response(
            {
                "message": "Role updated successfully",
                "new_role": new_role,
            }
        )

    @action(detail=True, methods=["get"])
    def team(self, request, pk=None):
        """Get team members under this manager."""
        profile = self.get_object()
        if not profile.is_manager:
            return Response(
                {"error": "This employee is not a manager"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        team = profile.get_team_members()
        serializer = EmployeeListSerializer(team, many=True)
        return Response(serializer.data)


# ============================================================================
# Employee Schedule Views
# ============================================================================


class EmployeeScheduleViewSet(ModelViewSet):
    """
    Manage employee schedules.

    GET /api/v1/profiles/employee/me/schedules/
    POST /api/v1/profiles/employee/me/schedules/
    PUT/DELETE /api/v1/profiles/employee/me/schedules/{id}/
    """

    serializer_class = EmployeeScheduleSerializer
    permission_classes = [permissions.IsAuthenticated, IsEmployeeUser]

    def get_queryset(self):
        """Return schedules for the current employee."""
        user = self.request.user
        try:
            profile = EmployeeProfile.objects.get(user=user)
            return EmployeeSchedule.objects.filter(employee=profile)
        except EmployeeProfile.DoesNotExist:
            return EmployeeSchedule.objects.none()

    def perform_create(self, serializer):
        """Create schedule for current employee."""
        profile = EmployeeProfile.objects.get(user=self.request.user)
        serializer.save(employee=profile)

    def perform_update(self, serializer):
        """Update schedule (only own schedules)."""
        schedule = self.get_object()
        if schedule.employee.user != self.request.user:
            if self.request.user.user_type != UserType.ADMIN:
                from rest_framework.exceptions import PermissionDenied

                raise PermissionDenied("You can only modify your own schedules.")
        serializer.save()


# ============================================================================
# Public Therapist Views
# ============================================================================


class TherapistListView(generics.ListAPIView):
    """
    List available therapists (public endpoint).

    GET /api/v1/profiles/therapists/
    """

    serializer_class = TherapistSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["user__first_name", "user__last_name", "specializations"]
    ordering_fields = ["user__first_name"]

    def get_queryset(self):
        """Return available therapists."""
        queryset = EmployeeProfile.objects.filter(
            role=EmployeeRole.THERAPIST,
            is_available=True,
            user__is_active=True,
        ).select_related("user").prefetch_related("schedules")

        # Filter by branch/location
        branch = self.request.query_params.get("branch")
        if branch:
            queryset = queryset.filter(branch__icontains=branch)

        # Filter by specialization
        specialization = self.request.query_params.get("specialization")
        if specialization:
            queryset = queryset.filter(specializations__contains=[specialization])

        return queryset


class TherapistDetailView(generics.RetrieveAPIView):
    """
    Get therapist details (public endpoint).

    GET /api/v1/profiles/therapists/{id}/
    """

    serializer_class = TherapistSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "id"

    def get_queryset(self):
        """Return available therapists."""
        return EmployeeProfile.objects.filter(
            role=EmployeeRole.THERAPIST,
            user__is_active=True,
        ).select_related("user").prefetch_related("schedules")
