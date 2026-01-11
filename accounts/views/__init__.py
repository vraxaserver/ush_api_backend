"""Views package for accounts app."""

from .admin_views import (
    AllUsersListView,
    CustomerDetailView,
    CustomerListView,
    EmployeeViewSet,
    UserStatisticsView,
)
from .auth_views import (
    ChangePasswordView,
    CustomLoginView,
    CustomLogoutView,
    CustomRegisterView,
    CustomTokenRefreshView,
    FacebookLoginView,
    GoogleLoginView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    PhoneRegisterView,
    SendVerificationCodeView,
    UserProfileView,
    VerifyCodeView,
)

__all__ = [
    # Auth views
    "CustomRegisterView",
    "PhoneRegisterView",
    "CustomLoginView",
    "CustomLogoutView",
    "CustomTokenRefreshView",
    "GoogleLoginView",
    "FacebookLoginView",
    "SendVerificationCodeView",
    "VerifyCodeView",
    "PasswordResetRequestView",
    "PasswordResetConfirmView",
    "ChangePasswordView",
    "UserProfileView",
    # Admin views
    "EmployeeViewSet",
    "CustomerListView",
    "CustomerDetailView",
    "AllUsersListView",
    "UserStatisticsView",
]
