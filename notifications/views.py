from rest_framework import generics, permissions, status
from rest_framework.response import Response

from .models import ContactMessage
from .serializers import ContactMessageCreateSerializer, ContactMessageListSerializer


class ContactMessageCreateView(generics.CreateAPIView):
    """
    POST /api/v1/notifications/contact/

    Public endpoint for submitting a 'Get in Touch' message.
    No authentication required.
    """

    serializer_class = ContactMessageCreateSerializer
    permission_classes = [permissions.AllowAny]
    throttle_scope = "anon"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {"message": "Your message has been sent successfully. We will get back to you soon."},
            status=status.HTTP_201_CREATED,
        )


class ContactMessageListView(generics.ListAPIView):
    """
    GET /api/v1/notifications/contact/list/

    Admin-only endpoint to list all contact messages.
    """

    serializer_class = ContactMessageListSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = ContactMessage.objects.all()
    filterset_fields = ["status"]
    search_fields = ["full_name", "email", "subject"]
    ordering_fields = ["created_at", "status"]


class ContactMessageDetailView(generics.RetrieveUpdateAPIView):
    """
    GET/PATCH /api/v1/notifications/contact/<id>/

    Admin-only endpoint to retrieve or update a contact message (e.g. change status).
    """

    serializer_class = ContactMessageListSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = ContactMessage.objects.all()
    lookup_field = "pk"
