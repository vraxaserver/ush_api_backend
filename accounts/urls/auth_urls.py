"""
Authentication URL Configuration.

All authentication-related endpoints.
"""

from django.urls import path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from accounts.views import (
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


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """Health check endpoint for Docker/Kubernetes."""
    return Response({"status": "healthy", "service": "auth-service"})


app_name = "auth"

urlpatterns = [
    # Health Check
    path("health/", health_check, name="health-check"),
    # Registration
    path("register/", CustomRegisterView.as_view(), name="register"),
    path("register/phone/", PhoneRegisterView.as_view(), name="register-phone"),
    # Login/Logout
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", CustomLogoutView.as_view(), name="logout"),
    # JWT Token
    path("token/refresh/", CustomTokenRefreshView.as_view(), name="token-refresh"),
    # Social Authentication
    path("social/google/", GoogleLoginView.as_view(), name="google-login"),
    path("social/facebook/", FacebookLoginView.as_view(), name="facebook-login"),
    # Verification
    path("verify/send/", SendVerificationCodeView.as_view(), name="verify-send"),
    path("verify/confirm/", VerifyCodeView.as_view(), name="verify-confirm"),
    # Password Management
    path("password/reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path(
        "password/reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path("password/change/", ChangePasswordView.as_view(), name="password-change"),
    # User Profile
    path("user/", UserProfileView.as_view(), name="user-profile"),
]
