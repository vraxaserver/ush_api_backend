"""
Serializers for Auth Microservice.

Handles user registration, authentication, and profile serialization.
"""

import random
import string
from datetime import date

from allauth.account.adapter import get_adapter
from dj_rest_auth.registration.serializers import RegisterSerializer
from dj_rest_auth.serializers import LoginSerializer
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import serializers

from .models import EmployeeRole, SocialAuthProvider, UserType, VerificationCode

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """
    User serializer for retrieving user details.

    Used for user profile and admin user management.
    """

    full_name = serializers.CharField(source="get_full_name", read_only=True)
    is_verified = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "phone_number",
            "first_name",
            "last_name",
            "full_name",
            "date_of_birth",
            "user_type",
            "is_email_verified",
            "is_phone_verified",
            "is_verified",
            "is_active",
            "date_joined",
            "last_login",
        ]
        read_only_fields = [
            "id",
            "user_type",
            "is_email_verified",
            "is_phone_verified",
            "is_active",
            "date_joined",
            "last_login",
        ]


class UserMinimalSerializer(serializers.ModelSerializer):
    """Minimal user serializer for nested representations."""

    full_name = serializers.CharField(source="get_full_name", read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "full_name", "user_type"]


class CustomRegisterSerializer(RegisterSerializer):
    """
    Custom registration serializer.

    Extends dj-rest-auth registration to support:
    - Phone number registration
    - Date of birth
    - First and last name (required)
    """

    username = None  # Remove username field
    email = serializers.EmailField(required=False, allow_blank=True)
    phone_number = PhoneNumberField(required=False, allow_blank=True)
    first_name = serializers.CharField(max_length=150, required=True)
    last_name = serializers.CharField(max_length=150, required=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    password1 = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, min_length=8)

    def validate_email(self, email):
        """Validate email uniqueness."""
        if email:
            email = get_adapter().clean_email(email)
            if User.objects.filter(email__iexact=email).exists():
                raise serializers.ValidationError(
                    _("A user with this email already exists.")
                )
        return email

    def validate_phone_number(self, phone_number):
        """Validate phone number uniqueness."""
        if phone_number:
            if User.objects.filter(phone_number=phone_number).exists():
                raise serializers.ValidationError(
                    _("A user with this phone number already exists.")
                )
        return phone_number

    def validate_date_of_birth(self, dob):
        """Validate date of birth is in the past and user is old enough."""
        if dob:
            today = date.today()
            if dob > today:
                raise serializers.ValidationError(
                    _("Date of birth cannot be in the future.")
                )
            age = (
                today.year
                - dob.year
                - ((today.month, today.day) < (dob.month, dob.day))
            )
            if age < 13:
                raise serializers.ValidationError(
                    _("You must be at least 13 years old to register.")
                )
        return dob

    def validate(self, data):
        """Validate that either email or phone is provided."""
        email = data.get("email")
        phone_number = data.get("phone_number")

        if not email and not phone_number:
            raise serializers.ValidationError(
                _("Either email or phone number is required.")
            )

        if data.get("password1") != data.get("password2"):
            raise serializers.ValidationError(
                {"password2": _("Password fields didn't match.")}
            )

        return data

    def get_cleaned_data(self):
        """Return cleaned data for user creation."""
        return {
            "email": self.validated_data.get("email", ""),
            "phone_number": self.validated_data.get("phone_number", ""),
            "first_name": self.validated_data.get("first_name", ""),
            "last_name": self.validated_data.get("last_name", ""),
            "date_of_birth": self.validated_data.get("date_of_birth"),
            "password1": self.validated_data.get("password1", ""),
        }

    def save(self, request):
        """Create and return the user."""
        adapter = get_adapter()
        user = adapter.new_user(request)
        self.cleaned_data = self.get_cleaned_data()

        # Set user fields
        user.email = self.cleaned_data.get("email") or None
        user.phone_number = self.cleaned_data.get("phone_number") or None
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.date_of_birth = self.cleaned_data.get("date_of_birth")
        user.user_type = UserType.CUSTOMER  # Default to customer on registration

        adapter.save_user(request, user, self)
        return user


class CustomLoginSerializer(LoginSerializer):
    """
    Custom login serializer supporting email or phone login.
    """

    username = None  # Remove username field
    email = serializers.CharField(required=False, allow_blank=True)
    phone_number = PhoneNumberField(required=False, allow_blank=True)

    def validate(self, attrs):
        """Validate login credentials."""
        email = attrs.get("email")
        phone_number = attrs.get("phone_number")
        password = attrs.get("password")

        if not email and not phone_number:
            raise serializers.ValidationError(
                _("Either email or phone number is required.")
            )

        # Find user by email or phone
        user = None
        if email:
            user = User.objects.filter(email__iexact=email).first()
        elif phone_number:
            user = User.objects.filter(phone_number=phone_number).first()

        if not user:
            raise serializers.ValidationError(_("Invalid credentials."))

        if not user.check_password(password):
            raise serializers.ValidationError(_("Invalid credentials."))

        if not user.is_active:
            raise serializers.ValidationError(_("User account is disabled."))

        # Check if user needs verification
        if not user.is_verified:
            raise serializers.ValidationError(
                _("Please verify your email or phone number first.")
            )

        # Set the backend attribute to avoid multiple backend error
        user.backend = "django.contrib.auth.backends.ModelBackend"
        
        attrs["user"] = user
        return attrs


class PhoneRegistrationSerializer(serializers.Serializer):
    """Serializer for phone-only registration."""

    phone_number = PhoneNumberField(required=True)
    email = serializers.CharField(required=False, allow_blank=True)
    first_name = serializers.CharField(max_length=150, required=True)
    last_name = serializers.CharField(max_length=150, required=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    def validate_phone_number(self, phone_number):
        """Validate phone number uniqueness."""
        if User.objects.filter(phone_number=phone_number).exists():
            raise serializers.ValidationError(
                _("A user with this phone number already exists.")
            )
        return phone_number

    def validate(self, data):
        """Validate passwords match."""
        if data["password"] != data["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": _("Passwords do not match.")}
            )
        return data

    def create(self, validated_data):
        """Create user with phone number."""
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")

        user = User.objects.create_user(
            phone_number=validated_data["phone_number"],
            email=validated_data.get("email"),
            password=password,
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            date_of_birth=validated_data.get("date_of_birth"),
            user_type=UserType.CUSTOMER,
        )
        return user


class VerificationCodeSerializer(serializers.Serializer):
    """Serializer for verification code requests."""

    verification_type = serializers.ChoiceField(
        choices=[("email", "Email"), ("phone", "Phone")]
    )


class VerifyCodeSerializer(serializers.Serializer):
    """Serializer for verifying codes."""

    code = serializers.CharField(max_length=10, min_length=4)
    verification_type = serializers.ChoiceField(
        choices=[("email", "Email"), ("phone", "Phone")]
    )

    def validate_code(self, code):
        """Validate code format."""
        if not code.isdigit():
            raise serializers.ValidationError(_("Code must contain only digits."))
        return code


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for password reset requests."""

    email = serializers.EmailField(required=False)
    phone_number = PhoneNumberField(required=False)

    def validate(self, data):
        """Validate that either email or phone is provided."""
        if not data.get("email") and not data.get("phone_number"):
            raise serializers.ValidationError(
                _("Either email or phone number is required.")
            )
        return data


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation."""

    code = serializers.CharField(max_length=10)
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True, min_length=8)

    def validate(self, data):
        """Validate passwords match."""
        if data["new_password"] != data["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": _("Passwords do not match.")}
            )
        return data


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password."""

    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True, min_length=8)

    def validate_old_password(self, old_password):
        """Validate old password is correct."""
        user = self.context["request"].user
        if not user.check_password(old_password):
            raise serializers.ValidationError(_("Current password is incorrect."))
        return old_password

    def validate(self, data):
        """Validate new passwords match."""
        if data["new_password"] != data["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": _("Passwords do not match.")}
            )
        return data


class SocialAuthProviderSerializer(serializers.ModelSerializer):
    """Serializer for social auth providers."""

    class Meta:
        model = SocialAuthProvider
        fields = ["id", "provider", "created_at"]
        read_only_fields = ["id", "provider", "created_at"]


# ============================================================================
# Admin Serializers for Employee Management
# ============================================================================


class CreateEmployeeSerializer(serializers.ModelSerializer):
    """
    Serializer for admin to create employee users.

    Only admins can create employees with specific roles.
    """

    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(choices=EmployeeRole.choices, write_only=True)

    class Meta:
        model = User
        fields = [
            "email",
            "phone_number",
            "first_name",
            "last_name",
            "date_of_birth",
            "password",
            "role",
        ]

    def validate_email(self, email):
        """Validate email uniqueness."""
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(
                _("A user with this email already exists.")
            )
        return email

    def create(self, validated_data):
        """Create employee user."""
        role = validated_data.pop("role")
        password = validated_data.pop("password")

        user = User.objects.create_user(
            password=password,
            user_type=UserType.EMPLOYEE,
            is_email_verified=True,  # Admin-created users are pre-verified
            **validated_data,
        )

        # Role will be set via profile creation in signals
        # Store role temporarily for profile creation
        user._employee_role = role
        return user


class UpdateEmployeeSerializer(serializers.ModelSerializer):
    """Serializer for updating employee users."""

    class Meta:
        model = User
        fields = [
            "email",
            "phone_number",
            "first_name",
            "last_name",
            "date_of_birth",
            "is_active",
        ]


class AdminUserListSerializer(serializers.ModelSerializer):
    """Serializer for admin user listing."""

    full_name = serializers.CharField(source="get_full_name", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "phone_number",
            "full_name",
            "user_type",
            "is_active",
            "is_verified",
            "date_joined",
        ]


def generate_verification_code(length=None):
    """
    Generate a random numeric verification code.

    Args:
        length: Length of the code (default from settings)

    Returns:
        str: Random numeric code
    """
    if length is None:
        length = getattr(settings, "VERIFICATION_CODE_LENGTH", 6)
    return "".join(random.choices(string.digits, k=length))
