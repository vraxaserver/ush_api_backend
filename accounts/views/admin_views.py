"""
Admin Views for Employee Management.

Only admins can create and manage employee users.
"""

import logging

from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import filters, generics, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from accounts.models import UserType
from accounts.permissions import IsAdminUser
from accounts.serializers import (
    AdminUserListSerializer,
    CreateEmployeeSerializer,
    UpdateEmployeeSerializer,
    UserSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()


class EmployeeViewSet(ModelViewSet):
    """
    ViewSet for admin to manage employee users.

    Endpoints:
    - GET /api/v1/accounts/employees/ - List employees
    - POST /api/v1/accounts/employees/ - Create employee
    - GET /api/v1/accounts/employees/{id}/ - Get employee detail
    - PUT /api/v1/accounts/employees/{id}/ - Update employee
    - PATCH /api/v1/accounts/employees/{id}/ - Partial update
    - DELETE /api/v1/accounts/employees/{id}/ - Deactivate employee
    """

    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["email", "first_name", "last_name", "phone_number"]
    ordering_fields = ["date_joined", "first_name", "last_name"]
    ordering = ["-date_joined"]

    def get_queryset(self):
        """Return only employee users."""
        return User.objects.filter(user_type=UserType.EMPLOYEE)

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == "create":
            return CreateEmployeeSerializer
        elif self.action in ["update", "partial_update"]:
            return UpdateEmployeeSerializer
        elif self.action == "list":
            return AdminUserListSerializer
        return UserSerializer

    def create(self, request, *args, **kwargs):
        """Create a new employee user."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        logger.info(
            f"Employee created: {user.email} by admin: {request.user.email}"
        )

        return Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        """Deactivate employee instead of deleting."""
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=["is_active"])

        logger.info(
            f"Employee deactivated: {instance.email} by admin: {request.user.email}"
        )

        return Response(
            {"message": "Employee deactivated successfully."},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        """Reactivate a deactivated employee."""
        instance = self.get_object()
        instance.is_active = True
        instance.save(update_fields=["is_active"])

        logger.info(
            f"Employee reactivated: {instance.email} by admin: {request.user.email}"
        )

        return Response(
            {"message": "Employee activated successfully."},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def reset_password(self, request, pk=None):
        """Reset employee password (admin action)."""
        instance = self.get_object()
        new_password = request.data.get("new_password")

        if not new_password or len(new_password) < 8:
            return Response(
                {"message": "Password must be at least 8 characters."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance.set_password(new_password)
        instance.save()

        logger.info(
            f"Employee password reset: {instance.email} by admin: {request.user.email}"
        )

        return Response(
            {"message": "Password reset successfully."},
            status=status.HTTP_200_OK,
        )


class CustomerListView(generics.ListAPIView):
    """
    List customer users (admin only).

    GET /api/v1/accounts/customers/
    """

    serializer_class = AdminUserListSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["email", "first_name", "last_name", "phone_number"]
    ordering_fields = ["date_joined", "first_name", "last_name"]
    ordering = ["-date_joined"]

    def get_queryset(self):
        """Return only customer users."""
        queryset = User.objects.filter(user_type=UserType.CUSTOMER)

        # Filter by verification status
        verified = self.request.query_params.get("verified")
        if verified is not None:
            if verified.lower() == "true":
                queryset = queryset.filter(
                    Q(is_email_verified=True) | Q(is_phone_verified=True)
                )
            else:
                queryset = queryset.filter(
                    is_email_verified=False, is_phone_verified=False
                )

        # Filter by active status
        active = self.request.query_params.get("active")
        if active is not None:
            queryset = queryset.filter(is_active=active.lower() == "true")

        return queryset


class CustomerDetailView(generics.RetrieveUpdateAPIView):
    """
    Get/update customer details (admin only).

    GET /api/v1/accounts/customers/{id}/
    PUT/PATCH /api/v1/accounts/customers/{id}/
    """

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        """Return only customer users."""
        return User.objects.filter(user_type=UserType.CUSTOMER)


class AllUsersListView(generics.ListAPIView):
    """
    List all users (admin only).

    GET /api/v1/accounts/users/
    """

    serializer_class = AdminUserListSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["email", "first_name", "last_name", "phone_number"]
    ordering_fields = ["date_joined", "first_name", "last_name", "user_type"]
    ordering = ["-date_joined"]

    def get_queryset(self):
        """Return all users with optional filtering."""
        queryset = User.objects.all()

        # Filter by user type
        user_type = self.request.query_params.get("user_type")
        if user_type:
            queryset = queryset.filter(user_type=user_type)

        # Filter by active status
        active = self.request.query_params.get("active")
        if active is not None:
            queryset = queryset.filter(is_active=active.lower() == "true")

        return queryset


class UserStatisticsView(generics.GenericAPIView):
    """
    Get user statistics (admin only).

    GET /api/v1/accounts/statistics/
    """

    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get(self, request):
        """Return user statistics."""
        from django.db.models import Count
        from django.utils import timezone
        from datetime import timedelta

        # Total counts by type
        type_counts = User.objects.values("user_type").annotate(count=Count("id"))

        # Active vs inactive
        active_count = User.objects.filter(is_active=True).count()
        inactive_count = User.objects.filter(is_active=False).count()

        # Verified counts
        verified_count = User.objects.filter(
            Q(is_email_verified=True) | Q(is_phone_verified=True)
        ).count()

        # New users (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        new_users = User.objects.filter(date_joined__gte=thirty_days_ago).count()

        # Social auth users
        from accounts.models import SocialAuthProvider
        social_users = SocialAuthProvider.objects.values("provider").annotate(
            count=Count("user", distinct=True)
        )

        return Response({
            "total_users": User.objects.count(),
            "by_type": {item["user_type"]: item["count"] for item in type_counts},
            "active_users": active_count,
            "inactive_users": inactive_count,
            "verified_users": verified_count,
            "new_users_30_days": new_users,
            "social_auth_users": {
                item["provider"]: item["count"] for item in social_users
            },
        })
