from rest_framework import serializers

from .models import ContactMessage


class ContactMessageCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new contact message (public endpoint).
    """

    class Meta:
        model = ContactMessage
        fields = ["full_name", "email", "subject", "message"]


class ContactMessageListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing/retrieving contact messages (admin use).
    """

    class Meta:
        model = ContactMessage
        fields = [
            "id",
            "full_name",
            "email",
            "subject",
            "message",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
