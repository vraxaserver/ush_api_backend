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



class ReadOnly(permissions.BasePermission):
    """
    Permission allowing only safe methods (GET, HEAD, OPTIONS).
    """

    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS
