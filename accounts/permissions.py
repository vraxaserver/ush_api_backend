"""
Custom Permissions for Auth Microservice.

Provides role-based access control for different user types.
"""

from rest_framework import permissions

from .models import UserType


class IsAdminUser(permissions.BasePermission):
    """
    Permission class for admin users only.

    Allows access only to users with user_type='admin'.
    """

    message = "Only admin users can perform this action."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.user_type == UserType.ADMIN
        )


class IsEmployeeUser(permissions.BasePermission):
    """
    Permission class for employee users.

    Allows access to users with user_type='employee' or 'admin'.
    """

    message = "Only employee or admin users can perform this action."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.user_type in [UserType.EMPLOYEE, UserType.ADMIN]
        )


class IsCustomerUser(permissions.BasePermission):
    """
    Permission class for customer users.

    Allows access to users with user_type='customer'.
    """

    message = "Only customer users can perform this action."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.user_type == UserType.CUSTOMER
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission class allowing object owners or admins.

    For object-level permissions where users can only access their own resources.
    """

    message = "You can only access your own resources."

    def has_object_permission(self, request, view, obj):
        if request.user.user_type == UserType.ADMIN:
            return True

        # Check if object has a user field
        if hasattr(obj, "user"):
            return obj.user == request.user
        elif hasattr(obj, "owner"):
            return obj.owner == request.user

        # If the object is the user itself
        return obj == request.user


class IsVerifiedUser(permissions.BasePermission):
    """
    Permission class for verified users only.

    Requires user to have verified email or phone.
    """

    message = "Please verify your email or phone number to access this resource."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_verified
        )


class HasEmployeeRole(permissions.BasePermission):
    """
    Permission class checking for specific employee roles.

    Usage:
        class MyView(APIView):
            permission_classes = [HasEmployeeRole]
            required_roles = ['branch_manager', 'country_manager']
    """

    message = "You don't have the required role for this action."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Admins always have access
        if request.user.user_type == UserType.ADMIN:
            return True

        # Check if user is employee
        if request.user.user_type != UserType.EMPLOYEE:
            return False

        # Get required roles from view
        required_roles = getattr(view, "required_roles", None)
        if not required_roles:
            return True  # No specific role required

        # Check user's role via employee profile
        if hasattr(request.user, "employee_profile"):
            user_role = request.user.employee_profile.role
            return user_role in required_roles

        return False


class IsBranchManager(permissions.BasePermission):
    """Permission for branch managers."""

    message = "Only branch managers can perform this action."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.user_type == UserType.ADMIN:
            return True

        if request.user.user_type == UserType.EMPLOYEE:
            if hasattr(request.user, "employee_profile"):
                return request.user.employee_profile.role == "branch_manager"

        return False


class IsCountryManager(permissions.BasePermission):
    """Permission for country managers."""

    message = "Only country managers can perform this action."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.user_type == UserType.ADMIN:
            return True

        if request.user.user_type == UserType.EMPLOYEE:
            if hasattr(request.user, "employee_profile"):
                return request.user.employee_profile.role in [
                    "country_manager",
                    "branch_manager",
                ]

        return False


class IsTherapist(permissions.BasePermission):
    """Permission for therapists."""

    message = "Only therapists can perform this action."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.user_type == UserType.ADMIN:
            return True

        if request.user.user_type == UserType.EMPLOYEE:
            if hasattr(request.user, "employee_profile"):
                return request.user.employee_profile.role == "therapist"

        return False


class ReadOnly(permissions.BasePermission):
    """
    Permission allowing only safe methods (GET, HEAD, OPTIONS).
    """

    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS
