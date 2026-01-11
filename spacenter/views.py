"""
Spa Center Views.

Views for managing spa centers, services, specialties, and therapists.
Includes filtering capabilities and multi-language support.
Public endpoints for list/retrieve, authenticated for create/update/delete on services.
"""

import logging

from django_filters import rest_framework as django_filters
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.models import EmployeeRole
from accounts.permissions import IsAdminUser

from .models import (
    City,
    Country,
    Service,
    ServiceImage,
    SpaCenter,
    SpaCenterOperatingHours,
    Specialty,
    TherapistProfile,
)
from .serializers import (
    CityListSerializer,
    CitySerializer,
    CountryListSerializer,
    CountrySerializer,
    ServiceCreateSerializer,
    ServiceImageSerializer,
    ServiceListSerializer,
    ServiceSerializer,
    SpaCenterCreateSerializer,
    SpaCenterDetailSerializer,
    SpaCenterListSerializer,
    SpaCenterOperatingHoursSerializer,
    SpecialtyListSerializer,
    SpecialtySerializer,
    TherapistProfileSerializer,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Custom Permissions
# =============================================================================

class IsAdminOrBranchManager(permissions.BasePermission):
    """
    Permission for admins and branch managers.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Admin has full access
        if request.user.is_admin:
            return True
        
        # Branch manager has access
        if request.user.is_employee:
            try:
                employee_profile = request.user.employee_profile
                return employee_profile.role == EmployeeRole.BRANCH_MANAGER
            except Exception:
                pass
        
        return False


# =============================================================================
# Filters
# =============================================================================

class CityFilter(django_filters.FilterSet):
    """Filter for cities."""
    
    country = django_filters.CharFilter(
        field_name="country__code",
        lookup_expr="iexact",
        help_text="Filter by country code (e.g., UAE, SAU, QAT)",
    )
    name = django_filters.CharFilter(lookup_expr="icontains")
    is_active = django_filters.BooleanFilter()

    class Meta:
        model = City
        fields = ["country", "name", "is_active"]


class SpaCenterFilter(django_filters.FilterSet):
    """Filter for spa centers."""

    country = django_filters.CharFilter(
        field_name="country__code",
        lookup_expr="iexact",
        help_text="Filter by country code (e.g., UAE, SAU, QAT)",
    )
    city = django_filters.UUIDFilter(field_name="city__id")
    city_name = django_filters.CharFilter(field_name="city__name", lookup_expr="icontains")
    is_active = django_filters.BooleanFilter()
    on_service = django_filters.BooleanFilter()
    has_service = django_filters.UUIDFilter(field_name="services__id")
    
    # Opening time filters
    opens_before = django_filters.TimeFilter(
        field_name="default_opening_time",
        lookup_expr="lte",
    )
    opens_after = django_filters.TimeFilter(
        field_name="default_opening_time",
        lookup_expr="gte",
    )
    closes_before = django_filters.TimeFilter(
        field_name="default_closing_time",
        lookup_expr="lte",
    )
    closes_after = django_filters.TimeFilter(
        field_name="default_closing_time",
        lookup_expr="gte",
    )

    class Meta:
        model = SpaCenter
        fields = [
            "country",
            "city",
            "city_name",
            "is_active",
            "on_service",
            "has_service",
            "opens_before",
            "opens_after",
            "closes_before",
            "closes_after",
        ]


class ServiceFilter(django_filters.FilterSet):
    """Filter for services."""
    
    specialty = django_filters.UUIDFilter(field_name="specialty__id")
    specialty_name = django_filters.CharFilter(
        field_name="specialty__name",
        lookup_expr="icontains",
    )
    is_home_service = django_filters.BooleanFilter()
    is_active = django_filters.BooleanFilter()
    currency = django_filters.CharFilter(lookup_expr="iexact")
    has_discount = django_filters.BooleanFilter(
        field_name="discount_price",
        lookup_expr="isnull",
        exclude=True,
    )
    min_price = django_filters.NumberFilter(field_name="base_price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="base_price", lookup_expr="lte")
    min_duration = django_filters.NumberFilter(field_name="duration_minutes", lookup_expr="gte")
    max_duration = django_filters.NumberFilter(field_name="duration_minutes", lookup_expr="lte")
    
    # Filter by spa center, city, country (using country code)
    spa_center = django_filters.UUIDFilter(field_name="spa_centers__id")
    city = django_filters.UUIDFilter(field_name="spa_centers__city__id")
    country = django_filters.CharFilter(
        field_name="spa_centers__country__code",
        lookup_expr="iexact",
        help_text="Filter by country code (e.g., UAE, SAU, QAT)",
    )

    class Meta:
        model = Service
        fields = [
            "specialty",
            "specialty_name",
            "is_home_service",
            "is_active",
            "currency",
            "has_discount",
            "min_price",
            "max_price",
            "min_duration",
            "max_duration",
            "spa_center",
            "city",
            "country",
        ]


class TherapistFilter(django_filters.FilterSet):
    """Filter for therapists."""

    country = django_filters.CharFilter(
        field_name="spa_center__country__code",
        lookup_expr="iexact",
        help_text="Filter by country code (e.g., UAE, SAU, QAT)",
    )
    city = django_filters.UUIDFilter(field_name="spa_center__city__id")
    spa_center = django_filters.UUIDFilter(field_name="spa_center__id")
    specialty = django_filters.UUIDFilter(field_name="specialties__id")
    service = django_filters.UUIDFilter(field_name="services__id")
    is_available = django_filters.BooleanFilter()
    min_experience = django_filters.NumberFilter(
        field_name="years_of_experience",
        lookup_expr="gte",
    )

    class Meta:
        model = TherapistProfile
        fields = [
            "country",
            "city",
            "spa_center",
            "specialty",
            "service",
            "is_available",
            "min_experience",
        ]


# =============================================================================
# Country Views
# =============================================================================

class CountryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing countries.
    
    All endpoints are public.
    
    GET /api/v1/spa/countries/ - List all active countries
    GET /api/v1/spa/countries/{id}/ - Get country details
    POST /api/v1/spa/countries/ - Create country
    PUT /api/v1/spa/countries/{id}/ - Update country
    DELETE /api/v1/spa/countries/{id}/ - Delete country
    """

    queryset = Country.objects.all()
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "name_en", "name_ar", "code"]
    ordering_fields = ["name", "code", "sort_order"]
    ordering = ["sort_order", "name"]

    def get_serializer_class(self):
        if self.action == "list":
            return CountryListSerializer
        return CountrySerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        # Only show active countries in list view
        if self.action == "list":
            queryset = queryset.filter(is_active=True)
        return queryset


# =============================================================================
# City Views
# =============================================================================

class CityViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing cities.
    
    All endpoints are public.
    
    GET /api/v1/spa/cities/ - List all active cities
    GET /api/v1/spa/cities/?country={id} - List cities by country
    GET /api/v1/spa/cities/{id}/ - Get city details
    GET /api/v1/spa/cities/by-country/{country_id}/ - Get cities by country ID
    """

    queryset = City.objects.select_related("country")
    permission_classes = [permissions.AllowAny]
    filterset_class = CityFilter
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = ["name", "name_en", "name_ar", "state"]
    ordering_fields = ["name", "sort_order", "country__name"]
    ordering = ["sort_order", "name"]

    def get_serializer_class(self):
        if self.action == "list":
            return CityListSerializer
        return CitySerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        # Only show active cities in list view
        if self.action == "list":
            queryset = queryset.filter(is_active=True, country__is_active=True)
        return queryset

    @action(detail=False, methods=["get"], url_path="by-country/(?P<country_code>[^/.]+)")
    def by_country(self, request, country_code=None):
        """Get cities filtered by country code (e.g., UAE, SAU, QAT)."""
        queryset = self.get_queryset().filter(
            country__code__iexact=country_code,
            is_active=True,
        )
        serializer = CityListSerializer(queryset, many=True)
        return Response(serializer.data)


# =============================================================================
# Specialty Views
# =============================================================================

class SpecialtyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing specialties.
    
    All endpoints are public.
    
    GET /api/v1/spa/specialties/ - List all active specialties
    GET /api/v1/spa/specialties/{id}/ - Get specialty details
    """

    queryset = Specialty.objects.all()
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "name_en", "name_ar", "description"]
    ordering_fields = ["name", "sort_order", "created_at"]
    ordering = ["sort_order", "name"]

    def get_serializer_class(self):
        if self.action == "list":
            return SpecialtyListSerializer
        return SpecialtySerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        # Only show active specialties in list view
        if self.action == "list":
            queryset = queryset.filter(is_active=True)
        return queryset


# =============================================================================
# Service Views
# =============================================================================

class ServiceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing services.
    
    GET endpoints are public.
    POST/PUT/DELETE require authentication (Admin or Branch Manager).
    
    Admin: Must select branch(es) when creating service.
    Branch Manager: Service auto-assigned to their branch. Can only see/manage their branch services.
    
    GET /api/v1/spa/services/ - List all active services (public)
    GET /api/v1/spa/services/?country={id} - Filter by country
    GET /api/v1/spa/services/?city={id} - Filter by city
    GET /api/v1/spa/services/?spa_center={id} - Filter by spa center
    GET /api/v1/spa/services/?specialty={id} - Filter by specialty
    GET /api/v1/spa/services/?is_home_service=true - Filter home services
    GET /api/v1/spa/services/{id}/ - Get service details
    POST /api/v1/spa/services/ - Create service (Admin/Branch Manager)
    PUT /api/v1/spa/services/{id}/ - Update service (Admin/Branch Manager)
    DELETE /api/v1/spa/services/{id}/ - Delete service (Admin/Branch Manager)
    """

    queryset = Service.objects.select_related("specialty", "created_by").prefetch_related("images", "spa_centers")
    filterset_class = ServiceFilter
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = ["name", "name_en", "name_ar", "description", "ideal_for"]
    ordering_fields = ["name", "base_price", "duration_minutes", "sort_order", "created_at"]
    ordering = ["sort_order", "name"]

    def get_permissions(self):
        """Set permissions based on action."""
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        return [IsAdminOrBranchManager()]

    def get_serializer_class(self):
        if self.action == "list":
            return ServiceListSerializer
        if self.action == "create":
            return ServiceCreateSerializer
        return ServiceSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # For list/retrieve - show only active services
        if self.action in ["list", "retrieve"]:
            queryset = queryset.filter(is_active=True)
        
        # For management actions (update, delete) - branch managers see only their branch services
        if self.action in ["update", "partial_update", "destroy"]:
            if user.is_authenticated and not user.is_admin:
                try:
                    spa_center = user.managed_spa_center
                    queryset = queryset.filter(spa_centers=spa_center)
                except SpaCenter.DoesNotExist:
                    queryset = queryset.none()
        
        # Filter by branch manager's branch if they are viewing as authenticated
        if self.action == "list" and user.is_authenticated:
            # Check if 'my_branch' query param is provided
            my_branch_only = self.request.query_params.get("my_branch", "").lower() == "true"
            if my_branch_only and not user.is_admin:
                try:
                    spa_center = user.managed_spa_center
                    queryset = queryset.filter(spa_centers=spa_center)
                except SpaCenter.DoesNotExist:
                    queryset = queryset.none()
        
        return queryset.distinct()

    @action(detail=True, methods=["post"], permission_classes=[IsAdminOrBranchManager])
    def add_image(self, request, pk=None):
        """Add image to a service (max 3 images)."""
        service = self.get_object()
        
        if service.images.count() >= 3:
            return Response(
                {"error": "Service can have maximum 3 images."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        serializer = ServiceImageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(service=service)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["delete"], permission_classes=[IsAdminOrBranchManager])
    def remove_image(self, request, pk=None):
        """Remove image from service (must keep at least 1)."""
        service = self.get_object()
        image_id = request.data.get("image_id")
        
        if service.images.count() <= 1:
            return Response(
                {"error": "Service must have at least 1 image."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        try:
            image = service.images.get(id=image_id)
            image.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ServiceImage.DoesNotExist:
            return Response(
                {"error": "Image not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=False, methods=["get"], permission_classes=[IsAdminOrBranchManager])
    def my_branch_services(self, request):
        """
        Get services for the current branch manager's branch.
        Admin sees all services.
        """
        user = request.user
        
        if user.is_admin:
            queryset = self.get_queryset()
        else:
            try:
                spa_center = user.managed_spa_center
                queryset = Service.objects.filter(
                    spa_centers=spa_center,
                    is_active=True,
                ).select_related("specialty").prefetch_related("images")
            except SpaCenter.DoesNotExist:
                return Response(
                    {"error": "You are not assigned as a branch manager."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        
        # Apply filters
        queryset = self.filter_queryset(queryset)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ServiceListSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)
        
        serializer = ServiceListSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=["post"], permission_classes=[IsAdminOrBranchManager])
    def assign_to_branch(self, request, pk=None):
        """Assign service to additional branches (Admin only)."""
        if not request.user.is_admin:
            return Response(
                {"error": "Only admin can assign services to branches."},
                status=status.HTTP_403_FORBIDDEN,
            )
        
        service = self.get_object()
        branch_ids = request.data.get("branch_ids", [])
        
        if not branch_ids:
            return Response(
                {"error": "branch_ids is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        branches = SpaCenter.objects.filter(id__in=branch_ids, is_active=True)
        service.spa_centers.add(*branches)
        
        return Response({
            "message": f"Service assigned to {branches.count()} branch(es).",
            "branches": [{"id": str(b.id), "name": b.name} for b in branches],
        })

    @action(detail=True, methods=["post"], permission_classes=[IsAdminOrBranchManager])
    def remove_from_branch(self, request, pk=None):
        """Remove service from a branch (Admin only)."""
        if not request.user.is_admin:
            return Response(
                {"error": "Only admin can remove services from branches."},
                status=status.HTTP_403_FORBIDDEN,
            )
        
        service = self.get_object()
        branch_id = request.data.get("branch_id")
        
        if not branch_id:
            return Response(
                {"error": "branch_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        try:
            branch = SpaCenter.objects.get(id=branch_id)
            service.spa_centers.remove(branch)
            return Response({
                "message": f"Service removed from {branch.name}.",
            })
        except SpaCenter.DoesNotExist:
            return Response(
                {"error": "Branch not found."},
                status=status.HTTP_404_NOT_FOUND,
            )


# =============================================================================
# Spa Center Views
# =============================================================================

class SpaCenterViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing spa centers/branches.
    
    All endpoints are public.
    
    GET /api/v1/spa/branches/ - List all active branches
    GET /api/v1/spa/branches/?country={id} - Filter by country
    GET /api/v1/spa/branches/?city={id} - Filter by city
    GET /api/v1/spa/branches/?opens_after=09:00 - Filter by opening time
    GET /api/v1/spa/branches/{id}/ - Get branch details
    GET /api/v1/spa/branches/{id}/therapists/ - Get therapists for branch
    GET /api/v1/spa/branches/{id}/services/ - Get services for branch
    """

    queryset = SpaCenter.objects.select_related(
        "country", "city", "branch_manager"
    ).prefetch_related("services", "operating_hours")
    permission_classes = [permissions.AllowAny]
    filterset_class = SpaCenterFilter
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = ["name", "name_en", "name_ar", "address", "city__name"]
    ordering_fields = ["name", "sort_order", "created_at", "default_opening_time"]
    ordering = ["sort_order", "name"]

    def get_serializer_class(self):
        if self.action == "list":
            return SpaCenterListSerializer
        if self.action == "create":
            return SpaCenterCreateSerializer
        return SpaCenterDetailSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        # Only show active spa centers in list view
        if self.action == "list":
            queryset = queryset.filter(is_active=True)
        return queryset

    @action(detail=True, methods=["get"])
    def therapists(self, request, pk=None):
        """Get therapists for a specific spa center."""
        spa_center = self.get_object()
        therapists = TherapistProfile.objects.filter(
            spa_center=spa_center,
            is_available=True,
        ).select_related("employee_profile__user").prefetch_related("specialties", "services")
        
        serializer = TherapistProfileSerializer(therapists, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def services(self, request, pk=None):
        """Get services for a specific spa center."""
        spa_center = self.get_object()
        services = spa_center.services.filter(is_active=True)
        
        serializer = ServiceListSerializer(services, many=True, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def set_operating_hours(self, request, pk=None):
        """Set operating hours for a spa center."""
        spa_center = self.get_object()
        hours_data = request.data.get("operating_hours", [])
        
        for hour_data in hours_data:
            day = hour_data.get("day_of_week")
            SpaCenterOperatingHours.objects.update_or_create(
                spa_center=spa_center,
                day_of_week=day,
                defaults={
                    "opening_time": hour_data.get("opening_time"),
                    "closing_time": hour_data.get("closing_time"),
                    "is_closed": hour_data.get("is_closed", False),
                },
            )
        
        serializer = SpaCenterDetailSerializer(spa_center, context={"request": request})
        return Response(serializer.data)


# =============================================================================
# Therapist Views
# =============================================================================

class TherapistViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing therapists.
    
    All endpoints are public.
    
    GET /api/v1/spa/therapists/ - List all available therapists
    GET /api/v1/spa/therapists/?country={id} - Filter by country
    GET /api/v1/spa/therapists/?city={id} - Filter by city
    GET /api/v1/spa/therapists/?spa_center={id} - Filter by spa center
    GET /api/v1/spa/therapists/?specialty={id} - Filter by specialty
    GET /api/v1/spa/therapists/?service={id} - Filter by service
    GET /api/v1/spa/therapists/{id}/ - Get therapist details
    """

    queryset = TherapistProfile.objects.select_related(
        "employee_profile__user",
        "spa_center__country",
        "spa_center__city",
    ).prefetch_related("specialties", "services")
    permission_classes = [permissions.AllowAny]
    filterset_class = TherapistFilter
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = [
        "employee_profile__user__first_name",
        "employee_profile__user__last_name",
    ]
    ordering_fields = ["created_at", "years_of_experience"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        return TherapistProfileSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        # Only show available therapists in list view
        if self.action == "list":
            queryset = queryset.filter(is_available=True)
        return queryset.distinct()
