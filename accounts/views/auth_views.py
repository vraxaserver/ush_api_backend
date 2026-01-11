"""
Authentication Views for Auth Microservice.

Handles JWT authentication, social auth, and verification.
"""

import logging

from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from dj_rest_auth.registration.views import RegisterView, SocialLoginView
from dj_rest_auth.views import LoginView, LogoutView
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.models import VerificationCode
from accounts.serializers import (
    ChangePasswordSerializer,
    CustomLoginSerializer,
    CustomRegisterSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PhoneRegistrationSerializer,
    UserSerializer,
    VerificationCodeSerializer,
    VerifyCodeSerializer,
    generate_verification_code,
)
from accounts.tasks import send_email_verification, send_sms_verification

logger = logging.getLogger(__name__)
User = get_user_model()


class CustomRegisterView(RegisterView):
    """
    Custom registration view supporting email/phone registration.

    POST /api/v1/auth/register/
    """

    serializer_class = CustomRegisterSerializer


class PhoneRegisterView(generics.CreateAPIView):
    """
    Phone-only registration endpoint.

    POST /api/v1/auth/register/phone/
    """

    serializer_class = PhoneRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate and send verification code
        self._send_phone_verification(user)

        return Response(
            {
                "message": "Registration successful. Please verify your phone number.",
                "user_id": str(user.id),
            },
            status=status.HTTP_201_CREATED,
        )

    def _send_phone_verification(self, user):
        """Generate and send phone verification code."""
        code = generate_verification_code()
        VerificationCode.objects.create(
            user=user,
            code=code,
            verification_type=VerificationCode.VerificationType.PHONE,
        )
        # Send async via Celery
        send_sms_verification.delay(str(user.phone_number), code)


class CustomLoginView(LoginView):
    """
    Custom login view supporting email/phone login with JWT.

    POST /api/v1/auth/login/
    """

    serializer_class = CustomLoginSerializer


class CustomLogoutView(LogoutView):
    """
    Logout view that blacklists the refresh token.

    POST /api/v1/auth/logout/
    """

    permission_classes = [permissions.IsAuthenticated]


class CustomTokenRefreshView(TokenRefreshView):
    """
    Refresh JWT access token.

    POST /api/v1/auth/token/refresh/
    """

    pass


# ============================================================================
# Social Authentication Views
# ============================================================================


class GoogleLoginView(SocialLoginView):
    """
    Google OAuth2 login.

    POST /api/v1/auth/social/google/
    """

    adapter_class = GoogleOAuth2Adapter


class FacebookLoginView(SocialLoginView):
    """
    Facebook OAuth2 login.

    POST /api/v1/auth/social/facebook/
    """

    adapter_class = FacebookOAuth2Adapter


# ============================================================================
# Verification Views
# ============================================================================


class SendVerificationCodeView(APIView):
    """
    Send verification code to user's email or phone.

    POST /api/v1/auth/verify/send/
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = VerificationCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        verification_type = serializer.validated_data["verification_type"]

        # Check if already verified
        if verification_type == "email" and user.is_email_verified:
            return Response(
                {"message": "Email is already verified."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if verification_type == "phone" and user.is_phone_verified:
            return Response(
                {"message": "Phone is already verified."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check rate limiting (max 3 codes per hour)
        recent_codes = VerificationCode.objects.filter(
            user=user,
            verification_type=verification_type,
            created_at__gte=timezone.now() - timezone.timedelta(hours=1),
        ).count()

        if recent_codes >= 3:
            return Response(
                {"message": "Too many verification requests. Please try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # Invalidate existing codes
        VerificationCode.objects.filter(
            user=user,
            verification_type=verification_type,
            is_used=False,
        ).update(is_used=True)

        # Generate new code
        code = generate_verification_code()
        VerificationCode.objects.create(
            user=user,
            code=code,
            verification_type=verification_type,
        )

        # Send code
        if verification_type == "email" and user.email:
            send_email_verification.delay(user.email, code)
            masked = self._mask_email(user.email)
        elif verification_type == "phone" and user.phone_number:
            send_sms_verification.delay(str(user.phone_number), code)
            masked = self._mask_phone(str(user.phone_number))
        else:
            return Response(
                {"message": f"No {verification_type} associated with this account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"message": f"Verification code sent to {masked}."},
            status=status.HTTP_200_OK,
        )

    def _mask_email(self, email):
        """Mask email for privacy."""
        username, domain = email.split("@")
        if len(username) <= 2:
            masked_username = username[0] + "*" * (len(username) - 1)
        else:
            masked_username = username[:2] + "*" * (len(username) - 2)
        return f"{masked_username}@{domain}"

    def _mask_phone(self, phone):
        """Mask phone number for privacy."""
        return phone[:4] + "*" * (len(phone) - 6) + phone[-2:]


class VerifyCodeView(APIView):
    """
    Verify email or phone with code.

    POST /api/v1/auth/verify/confirm/
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = VerifyCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        code = serializer.validated_data["code"]
        verification_type = serializer.validated_data["verification_type"]

        # Find valid verification code
        verification = VerificationCode.objects.filter(
            user=user,
            verification_type=verification_type,
            is_used=False,
        ).order_by("-created_at").first()

        if not verification:
            return Response(
                {"message": "No pending verification found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not verification.is_valid:
            return Response(
                {"message": "Verification code has expired. Please request a new one."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if verification.code != code:
            verification.increment_attempts()
            remaining = (
                getattr(settings, "MAX_VERIFICATION_ATTEMPTS", 5)
                - verification.attempts
            )
            return Response(
                {
                    "message": "Invalid verification code.",
                    "attempts_remaining": remaining,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Mark as verified
        verification.mark_used()
        if verification_type == "email":
            user.is_email_verified = True
        else:
            user.is_phone_verified = True
        user.save(update_fields=[f"is_{verification_type}_verified"])

        return Response(
            {"message": f"{verification_type.capitalize()} verified successfully."},
            status=status.HTTP_200_OK,
        )


# ============================================================================
# Password Management Views
# ============================================================================


class PasswordResetRequestView(APIView):
    """
    Request password reset via email or phone.

    POST /api/v1/auth/password/reset/
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data.get("email")
        phone_number = serializer.validated_data.get("phone_number")

        # Find user
        user = None
        if email:
            user = User.objects.filter(email__iexact=email).first()
        elif phone_number:
            user = User.objects.filter(phone_number=phone_number).first()

        # Always return success for security (don't reveal if user exists)
        if user:
            # Rate limiting
            recent_codes = VerificationCode.objects.filter(
                user=user,
                verification_type=VerificationCode.VerificationType.PASSWORD_RESET,
                created_at__gte=timezone.now() - timezone.timedelta(hours=1),
            ).count()

            if recent_codes < 3:
                # Invalidate existing codes
                VerificationCode.objects.filter(
                    user=user,
                    verification_type=VerificationCode.VerificationType.PASSWORD_RESET,
                    is_used=False,
                ).update(is_used=True)

                # Generate new code
                code = generate_verification_code()
                VerificationCode.objects.create(
                    user=user,
                    code=code,
                    verification_type=VerificationCode.VerificationType.PASSWORD_RESET,
                )

                # Send code
                if email:
                    send_email_verification.delay(user.email, code, is_password_reset=True)
                else:
                    send_sms_verification.delay(str(user.phone_number), code)

        return Response(
            {"message": "If an account exists, a reset code has been sent."},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    """
    Confirm password reset with code.

    POST /api/v1/auth/password/reset/confirm/
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        code = serializer.validated_data["code"]
        new_password = serializer.validated_data["new_password"]

        # Find verification code
        verification = VerificationCode.objects.filter(
            code=code,
            verification_type=VerificationCode.VerificationType.PASSWORD_RESET,
            is_used=False,
        ).select_related("user").first()

        if not verification or not verification.is_valid:
            return Response(
                {"message": "Invalid or expired reset code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Reset password
        user = verification.user
        user.set_password(new_password)
        user.save()

        # Mark code as used
        verification.mark_used()

        # Blacklist all existing tokens
        try:
            from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
            OutstandingToken.objects.filter(user=user).delete()
        except Exception as e:
            logger.warning(f"Could not blacklist tokens: {e}")

        return Response(
            {"message": "Password reset successful. Please login with your new password."},
            status=status.HTTP_200_OK,
        )


class ChangePasswordView(APIView):
    """
    Change password for authenticated user.

    POST /api/v1/auth/password/change/
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save()

        # Generate new tokens
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "message": "Password changed successfully.",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_200_OK,
        )


# ============================================================================
# User Profile View
# ============================================================================


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Get and update current user's profile.

    GET /api/v1/auth/user/
    PUT/PATCH /api/v1/auth/user/
    """

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
