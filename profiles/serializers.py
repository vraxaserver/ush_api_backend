"""
Serializers for Profile Models.

Handles serialization of customer and employee profiles.
"""

from rest_framework import serializers

from accounts.serializers import UserMinimalSerializer

from .models import CustomerProfile, EmployeeProfile, EmployeeSchedule, Slide


class CustomerProfileSerializer(serializers.ModelSerializer):
    """Serializer for customer profiles."""

    user = UserMinimalSerializer(read_only=True)
    full_address = serializers.CharField(read_only=True)

    class Meta:
        model = CustomerProfile
        fields = [
            "id",
            "user",
            "avatar",
            "bio",
            "address_line_1",
            "address_line_2",
            "city",
            "state",
            "postal_code",
            "country",
            "full_address",
            "preferred_language",
            "notification_preferences",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]


class CustomerProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating customer profiles."""

    class Meta:
        model = CustomerProfile
        fields = [
            "avatar",
            "bio",
            "address_line_1",
            "address_line_2",
            "city",
            "state",
            "postal_code",
            "country",
            "preferred_language",
            "notification_preferences",
        ]


class EmployeeScheduleSerializer(serializers.ModelSerializer):
    """Serializer for employee schedules."""

    day_name = serializers.CharField(source="get_day_of_week_display", read_only=True)

    class Meta:
        model = EmployeeSchedule
        fields = [
            "id",
            "day_of_week",
            "day_name",
            "start_time",
            "end_time",
            "is_working",
        ]
        read_only_fields = ["id"]


class EmployeeProfileSerializer(serializers.ModelSerializer):
    """Serializer for employee profiles."""

    user = UserMinimalSerializer(read_only=True)
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    is_manager = serializers.BooleanField(read_only=True)
    subordinates_count = serializers.IntegerField(read_only=True)
    schedules = EmployeeScheduleSerializer(many=True, read_only=True)
    manager_name = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeProfile
        fields = [
            "id",
            "user",
            "role",
            "role_display",
            "employee_id",
            "department",
            "job_title",
            "avatar",
            "bio",
            "hire_date",
            "work_location",
            "manager",
            "manager_name",
            "branch",
            "region",
            "country",
            "work_phone",
            "work_email",
            "certifications",
            "specializations",
            "is_available",
            "is_manager",
            "subordinates_count",
            "schedules",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "employee_id",
            "created_at",
            "updated_at",
        ]

    def get_manager_name(self, obj):
        """Get manager's full name."""
        if obj.manager:
            return obj.manager.user.get_full_name()
        return None


class EmployeeProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating employee profiles."""

    class Meta:
        model = EmployeeProfile
        fields = [
            "department",
            "job_title",
            "avatar",
            "bio",
            "work_location",
            "branch",
            "region",
            "country",
            "work_phone",
            "work_email",
            "certifications",
            "specializations",
            "is_available",
        ]


class EmployeeProfileAdminSerializer(serializers.ModelSerializer):
    """Serializer for admin to update employee profiles (includes role)."""

    class Meta:
        model = EmployeeProfile
        fields = [
            "role",
            "department",
            "job_title",
            "avatar",
            "bio",
            "hire_date",
            "work_location",
            "manager",
            "branch",
            "region",
            "country",
            "work_phone",
            "work_email",
            "certifications",
            "specializations",
            "is_available",
        ]


class EmployeeListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for employee listings."""

    user = UserMinimalSerializer(read_only=True)
    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = EmployeeProfile
        fields = [
            "id",
            "user",
            "role",
            "role_display",
            "employee_id",
            "department",
            "branch",
            "is_available",
        ]


class TherapistSerializer(serializers.ModelSerializer):
    """Serializer for therapist profiles (public view)."""

    user = UserMinimalSerializer(read_only=True)
    schedules = EmployeeScheduleSerializer(many=True, read_only=True)

    class Meta:
        model = EmployeeProfile
        fields = [
            "id",
            "user",
            "avatar",
            "bio",
            "work_location",
            "certifications",
            "specializations",
            "is_available",
            "schedules",
        ]


class SlideSerializer(serializers.ModelSerializer):
    """Serializer for slideshow slides (public view) with translations."""

    class Meta:
        model = Slide
        fields = [
            "id",
            "image",
            "title",
            "title_en",
            "title_ar",
            "description",
            "description_en",
            "description_ar",
            "link",
            "order",
        ]


