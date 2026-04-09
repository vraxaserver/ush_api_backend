"""
Account Management URL Configuration.

Admin endpoints for managing users.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounts.views import (
    AllUsersListView,
    CustomerDetailView,
    CustomerListView,
    UserStatisticsView,
)

app_name = "accounts"

urlpatterns = [
    # Customer management
    path("customers/", CustomerListView.as_view(), name="customer-list"),
    path("customers/<uuid:pk>/", CustomerDetailView.as_view(), name="customer-detail"),
    # All users (admin)
    path("users/", AllUsersListView.as_view(), name="user-list"),
    # Statistics
    path("statistics/", UserStatisticsView.as_view(), name="user-statistics"),
]
