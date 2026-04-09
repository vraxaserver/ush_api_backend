"""
Serializers for Profile Models.

Handles serialization of customer and employee profiles.
"""

from rest_framework import serializers

from accounts.serializers import UserMinimalSerializer

from .models import CustomerProfile, Slide


class CustomerProfileSerializer(serializers.ModelSerializer):
    """Serializer for customer profiles."""

    user = UserMinimalSerializer(read_only=True)
    full_name = serializers.SerializerMethodField()
    full_address = serializers.CharField(read_only=True)

    class Meta:
        model = CustomerProfile
        fields = [
            "id",
            "user",
            "full_name",
            "avatar",
            "bio",
            "gender",
            "dob",
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
        read_only_fields = ["id", "user", "full_name", "created_at", "updated_at"]

    def get_full_name(self, obj):
        """Return the user's full name."""
        return obj.user.get_full_name()


class CustomerProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating customer profiles (includes full name)."""

    full_name = serializers.CharField(
        max_length=300, required=False,
        help_text="User's full name (e.g. 'Ahmed Al Thani')",
    )

    class Meta:
        model = CustomerProfile
        fields = [
            "full_name",
            "avatar",
            "bio",
            "gender",
            "dob",
            "address_line_1",
            "address_line_2",
            "city",
            "state",
            "postal_code",
            "country",
            "preferred_language",
            "notification_preferences",
        ]

    def update(self, instance, validated_data):
        # Extract full_name and split into first/last name on the User model
        full_name = validated_data.pop("full_name", None)

        if full_name is not None:
            parts = full_name.strip().split(" ", 1)
            user = instance.user
            user.first_name = parts[0]
            user.last_name = parts[1] if len(parts) > 1 else ""
            user.save(update_fields=["first_name", "last_name", "updated_at"])

        return super().update(instance, validated_data)



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


