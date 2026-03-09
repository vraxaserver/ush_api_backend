from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    # Public endpoint
    path("contact/", views.ContactMessageCreateView.as_view(), name="contact-create"),
    # Admin endpoints
    path("contact/list/", views.ContactMessageListView.as_view(), name="contact-list"),
    path("contact/<uuid:pk>/", views.ContactMessageDetailView.as_view(), name="contact-detail"),
]
