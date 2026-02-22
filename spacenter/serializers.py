"""
Spa Center Serializers.

Serializers for spa centers, services, specialties management.
Supports multi-language (English, Arabic) output.
"""

from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from accounts.models import EmployeeRole, UserType
from profiles.models import EmployeeProfile

from .models import (
    AddOnService,
    BaseProduct,
    City,
    Country,
    ProductCategory,
    Service,
    ServiceImage,
    SpaCenter,
    SpaCenterOperatingHours,
    SpaProduct,
    Specialty
)

User = get_user_model()


# =============================================================================
# Base Translation Mixin
# =============================================================================

class TranslatedFieldsMixin:
    """
    Mixin to include translated fields in serializers.
    
    Automatically includes _en and _ar versions of translatable fields.
    """
    
    def get_translated_field(self, obj, field_name):
        """Get field value for current language or default."""
        request = self.context.get("request")
        lang = getattr(request, "LANGUAGE_CODE", None) if request else None
        
        if lang and hasattr(obj, f"{field_name}_{lang}"):
            value = getattr(obj, f"{field_name}_{lang}")
            if value:
                return value
        
        return getattr(obj, field_name, "")


# =============================================================================
# Country Serializers
# =============================================================================

class CountrySerializer(serializers.ModelSerializer):
    """Serializer for Country model with translations."""
    
    class Meta:
        model = Country
        fields = [
            "id",
            "name",
            "name_en",
            "name_ar",
            "code",
            "phone_code",
            "flag",
            "is_active",
            "sort_order",
        ]
        read_only_fields = ["id"]


class CountryListSerializer(serializers.ModelSerializer):
    """Minimal serializer for country lists."""

    class Meta:
        model = Country
        fields = ["id", "name", "name_en", "name_ar", "code", "phone_code", "flag"]


# =============================================================================
# City Serializers
# =============================================================================

class CitySerializer(serializers.ModelSerializer):
    """Serializer for City model with translations."""
    
    country_name = serializers.CharField(source="country.name", read_only=True)
    
    class Meta:
        model = City
        fields = [
            "id",
            "country",
            "country_name",
            "name",
            "name_en",
            "name_ar",
            "state",
            "state_en",
            "state_ar",
            "is_active",
            "sort_order",
        ]
        read_only_fields = ["id"]


class CityListSerializer(serializers.ModelSerializer):
    """Minimal serializer for city lists."""
    
    country_name = serializers.CharField(source="country.name", read_only=True)
    country_code = serializers.CharField(source="country.code", read_only=True)

    class Meta:
        model = City
        fields = [
            "id",
            "name",
            "name_en",
            "name_ar",
            "state",
            "country",
            "country_name",
            "country_code",
        ]


# =============================================================================
# Specialty Serializers
# =============================================================================

class SpecialtySerializer(serializers.ModelSerializer):
    """Serializer for Specialty model with translations."""

    class Meta:
        model = Specialty
        fields = [
            "id",
            "name",
            "name_en",
            "name_ar",
            "description",
            "description_en",
            "description_ar",
            "icon",
            "is_active",
            "sort_order",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class SpecialtyListSerializer(serializers.ModelSerializer):
    """Minimal serializer for specialty lists."""

    class Meta:
        model = Specialty
        fields = ["id", "name", "name_en", "name_ar", "icon"]


# =============================================================================
# Add-on Service Serializers
# =============================================================================

class AddOnServiceSerializer(serializers.ModelSerializer):
    """Serializer for AddOnService model with translations."""

    class Meta:
        model = AddOnService
        fields = [
            "id",
            "name",
            "name_en",
            "name_ar",
            "description",
            "description_en",
            "description_ar",
            "duration_minutes",
            "price",
            "currency",
            "image",
            "is_active",
            "sort_order",
        ]
        read_only_fields = ["id"]


class AddOnServiceListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for AddOnService in lists."""

    class Meta:
        model = AddOnService
        fields = [
            "id",
            "name",
            "name_en",
            "name_ar",
            "duration_minutes",
            "price",
            "currency",
            "image",
        ]


# =============================================================================
# Service Serializers
# =============================================================================

class ServiceImageSerializer(serializers.ModelSerializer):
    """Serializer for ServiceImage model."""
    
    class Meta:
        model = ServiceImage
        fields = ["id", "image", "alt_text", "is_primary", "sort_order"]
        read_only_fields = ["id"]


class ServiceSerializer(serializers.ModelSerializer):
    """Serializer for Service model with translations."""
    
    specialty_detail = SpecialtyListSerializer(source="specialty", read_only=True)
    country_detail = CountryListSerializer(source="country", read_only=True)
    city_detail = CityListSerializer(source="city", read_only=True)
    images = ServiceImageSerializer(many=True, read_only=True)
    add_on_services = AddOnServiceListSerializer(many=True, read_only=True)
    current_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )
    has_discount = serializers.BooleanField(read_only=True)
    discount_percentage = serializers.IntegerField(read_only=True)
    home_service_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )
    branches = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = [
            "id",
            "name",
            "name_en",
            "name_ar",
            "description",
            "description_en",
            "description_ar",
            "specialty",
            "specialty_detail",
            "country",
            "country_detail",
            "city",
            "city_detail",
            "duration_minutes",
            "currency",
            "base_price",
            "discount_price",
            "current_price",
            "has_discount",
            "discount_percentage",
            "extra_minutes",
            "price_for_extra_minutes",
            "is_home_service",
            "price_for_home_service",
            "home_service_price",
            "is_for_male",
            "is_for_female",
            "ideal_for",
            "ideal_for_en",
            "ideal_for_ar",
            "benefits",
            "add_on_services",
            "images",
            "branches",
            "is_active",
            "sort_order",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_branches(self, obj):
        """Get list of branches offering this service with availability."""
        from bookings.utils import calculate_service_availability

        # Default availability for next 30 days
        today = timezone.now().date()
        date_to = today + timedelta(days=30)

        branches_data = []
        # Filter active spa centers that offer this service
        for spa_center in obj.spa_centers.filter(is_active=True):
            availability = calculate_service_availability(
                obj, spa_center, today, date_to
            )
            
            branches_data.append({
                "id": str(spa_center.id),
                "name": spa_center.name,
                "arrangements": availability["arrangements"],
                "timeslots_availability": availability["timeslots_availability"]
            })
            
        return branches_data

    def validate(self, attrs): 
        """Validate city belongs to country."""
        city = attrs.get("city", getattr(self.instance, "city", None))
        country = attrs.get("country", getattr(self.instance, "country", None))
        
        if city and country and city.country != country:
            raise serializers.ValidationError({
                "city": "Selected city does not belong to the selected country."
            })
        return attrs


class ServiceCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating services with images."""
    
    images = serializers.ListField(
        child=serializers.ImageField(),
        min_length=1,
        max_length=3,
        write_only=True,
    )
    branch_ids = serializers.PrimaryKeyRelatedField(
        queryset=SpaCenter.objects.filter(is_active=True),
        many=True,
        required=False,
        write_only=True,
        help_text="Required for admin. Branch managers auto-assign to their branch.",
    )

    class Meta:
        model = Service
        fields = [
            "name",
            "name_en",
            "name_ar",
            "description",
            "description_en",
            "description_ar",
            "specialty",
            "country",
            "city",
            "duration_minutes",
            "currency",
            "base_price",
            "discount_price",
            "extra_minutes",
            "price_for_extra_minutes",
            "is_home_service",
            "price_for_home_service",
            "is_for_male",
            "is_for_female",
            "ideal_for",
            "ideal_for_en",
            "ideal_for_ar",
            "benefits",
            "images",
            "branch_ids",
            "is_active",
            "sort_order",
        ]

    def validate(self, attrs):
        """Validate discount price, branch assignment, and city belongs to country."""
        base_price = attrs.get("base_price")
        discount_price = attrs.get("discount_price")
        city = attrs.get("city")
        country = attrs.get("country")
        
        if discount_price and base_price and discount_price >= base_price:
            raise serializers.ValidationError({
                "discount_price": "Discount price must be less than base price."
            })
        
        if city and country and city.country != country:
            raise serializers.ValidationError({
                "city": "Selected city does not belong to the selected country."
            })
        
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            # Admin must provide branch_ids
            if request.user.is_admin:
                branch_ids = attrs.get("branch_ids", [])
                if not branch_ids:
                    raise serializers.ValidationError({
                        "branch_ids": "Admin must select at least one branch for the service."
                    })
        
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        images_data = validated_data.pop("images", [])
        branch_ids = validated_data.pop("branch_ids", [])
        
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["created_by"] = request.user
        
        service = Service.objects.create(**validated_data)
        
        # Create images
        for idx, image in enumerate(images_data):
            ServiceImage.objects.create(
                service=service,
                image=image,
                is_primary=(idx == 0),
                sort_order=idx,
            )
        
        # Assign to branches
        if request and request.user.is_authenticated:
            if request.user.is_admin:
                # Admin provided branches
                for branch in branch_ids:
                    branch.services.add(service)
            else:
                # Branch manager - auto-assign to their branch
                try:
                    spa_center = request.user.managed_spa_center
                    spa_center.services.add(service)
                except SpaCenter.DoesNotExist:
                    pass
        
        return service


class ServiceListSerializer(serializers.ModelSerializer):
    """Minimal serializer for service lists."""
    
    specialty_name = serializers.CharField(source="specialty.name", read_only=True)
    country_code = serializers.CharField(source="country.code", read_only=True)
    country_name = serializers.CharField(source="country.name", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)
    primary_image = serializers.SerializerMethodField()
    add_on_services = AddOnServiceListSerializer(many=True, read_only=True)
    addon_count = serializers.SerializerMethodField()
    current_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )
    has_discount = serializers.BooleanField(read_only=True)
    discount_percentage = serializers.IntegerField(read_only=True)
    branches = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = [
            "id",
            "name",
            "name_en",
            "name_ar",
            "specialty",
            "specialty_name",
            "country",
            "country_code",
            "country_name",
            "city",
            "city_name",
            "duration_minutes",
            "currency",
            "base_price",
            "discount_price",
            "current_price",
            "has_discount",
            "discount_percentage",
            "extra_minutes",
            "price_for_extra_minutes",
            "is_home_service",
            "home_service_price",
            "is_for_male",
            "is_for_female",
            "ideal_for",
            "primary_image",
            "add_on_services",
            "addon_count",
            "branches",
        ]

    def get_primary_image(self, obj):
        primary = obj.images.filter(is_primary=True).first()
        if primary:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(primary.image.url)
            return primary.image.url
        first_image = obj.images.first()
        if first_image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(first_image.image.url)
            return first_image.image.url
        return None

    def get_addon_count(self, obj):
        """Get count of add-on services."""
        return obj.add_on_services.filter(is_active=True).count()

    def get_branches(self, obj):
        """Get list of spa centers (branches) offering this service."""
        # If specific spa center context is provided (e.g., from branch services view),
        # return only that branch.
        context_spa_center = self.context.get("spa_center")
        if context_spa_center:
            return [{"id": str(context_spa_center.id), "name": context_spa_center.name}]

        return [
            {"id": str(sc.id), "name": sc.name}
            for sc in obj.spa_centers.filter(is_active=True)
        ]


# =============================================================================
# Spa Center Serializers
# =============================================================================

class SpaCenterOperatingHoursSerializer(serializers.ModelSerializer):
    """Serializer for operating hours."""

    day_name = serializers.CharField(source="get_day_of_week_display", read_only=True)

    class Meta:
        model = SpaCenterOperatingHours
        fields = [
            "id",
            "day_of_week",
            "day_name",
            "opening_time",
            "closing_time",
            "is_closed",
        ]
        read_only_fields = ["id"]


class SpaCenterListSerializer(serializers.ModelSerializer):
    """Serializer for spa center list view with translations."""

    country_name = serializers.CharField(source="country.name", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)
    location = serializers.SerializerMethodField()
    branch_manager_name = serializers.SerializerMethodField()

    class Meta:
        model = SpaCenter
        fields = [
            "id",
            "name",
            "name_en",
            "name_ar",
            "slug",
            "image",
            "country",
            "country_name",
            "city",
            "city_name",
            "address",
            "location",
            "default_opening_time",
            "default_closing_time",
            "is_active",
            "on_service",
            "branch_manager_name",
        ]

    def get_location(self, obj):
        return obj.location

    def get_branch_manager_name(self, obj):
        if obj.branch_manager:
            return obj.branch_manager.get_full_name()
        return None


class SpaCenterDetailSerializer(serializers.ModelSerializer):
    """Serializer for spa center detail view with translations."""

    country_detail = CountryListSerializer(source="country", read_only=True)
    city_detail = CityListSerializer(source="city", read_only=True)
    services = ServiceListSerializer(many=True, read_only=True)
    service_ids = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.filter(is_active=True),
        many=True,
        write_only=True,
        required=False,
        source="services",
    )
    operating_hours = SpaCenterOperatingHoursSerializer(many=True, read_only=True)
    location = serializers.SerializerMethodField()
    branch_manager_name = serializers.SerializerMethodField()
    full_address = serializers.CharField(read_only=True)

    class Meta:
        model = SpaCenter
        fields = [
            "id",
            "name",
            "name_en",
            "name_ar",
            "slug",
            "description",
            "description_en",
            "description_ar",
            "image",
            "country",
            "country_detail",
            "city",
            "city_detail",
            "address",
            "address_en",
            "address_ar",
            "full_address",
            "postal_code",
            "latitude",
            "longitude",
            "location",
            "phone",
            "email",
            "website",
            "default_opening_time",
            "default_closing_time",
            "is_active",
            "on_service",
            "branch_manager",
            "branch_manager_name",
            "services",
            "service_ids",
            "operating_hours",
            "sort_order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_location(self, obj):
        return obj.location

    def get_branch_manager_name(self, obj):
        if obj.branch_manager:
            return obj.branch_manager.get_full_name()
        return None

    def validate(self, attrs):
        """Validate city belongs to country."""
        country = attrs.get("country") or (self.instance.country if self.instance else None)
        city = attrs.get("city") or (self.instance.city if self.instance else None)
        
        if country and city and city.country_id != country.id:
            raise serializers.ValidationError({
                "city": "Selected city must belong to the selected country."
            })
        
        return attrs


class SpaCenterCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating spa centers with translations."""

    class Meta:
        model = SpaCenter
        fields = [
            "name",
            "name_en",
            "name_ar",
            "slug",
            "description",
            "description_en",
            "description_ar",
            "image",
            "country",
            "city",
            "address",
            "address_en",
            "address_ar",
            "postal_code",
            "latitude",
            "longitude",
            "phone",
            "email",
            "website",
            "default_opening_time",
            "default_closing_time",
            "is_active",
            "on_service",
            "branch_manager",
            "sort_order",
        ]

    def validate(self, attrs):
        """Validate city belongs to country."""
        country = attrs.get("country")
        city = attrs.get("city")
        
        if country and city and city.country_id != country.id:
            raise serializers.ValidationError({
                "city": "Selected city must belong to the selected country."
            })
        
        return attrs


# =============================================================================
# Product Serializers (SpaProduct API - Read Only)
# =============================================================================

class ProductCategorySerializer(serializers.ModelSerializer):
    """Serializer for ProductCategory."""

    class Meta:
        model = ProductCategory
        fields = [
            "id",
            "name",
            "name_en",
            "name_ar",
            "description",
            "description_en",
            "description_ar",
            "is_active",
        ]


class BaseProductSerializer(serializers.ModelSerializer):
    """Serializer for BaseProduct (master product catalog)."""

    class Meta:
        model = BaseProduct
        fields = [
            "id",
            "name",
            "name_en",
            "name_ar",
            "short_description",
            "short_description_en",
            "short_description_ar",
            "product_type",
            "category",
            "brand",
            "sku",
            "status",
            "image",
            "is_organic",
            "is_aromatherapy",
            "suitable_for_sensitive_skin",
            "is_featured",
            "is_visible",
            "created_at",
            "updated_at",
        ]


class BaseProductListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for BaseProduct in lists."""

    class Meta:
        model = BaseProduct
        fields = [
            "id",
            "name",
            "name_en",
            "name_ar",
            "short_description",
            "product_type",
            "category",
            "brand",
            "sku",
            "status",
            "image",
            "is_organic",
            "is_aromatherapy",
            "suitable_for_sensitive_skin",
            "is_featured",
        ]


class SpaProductListSerializer(serializers.ModelSerializer):
    """
    Serializer for SpaProduct listing.
    
    Includes product details, location, pricing, and stock information.
    Used for public API listing.
    """

    # Product details
    product = BaseProductListSerializer(read_only=True)
    product_id = serializers.UUIDField(source="product.id", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    product_image = serializers.ImageField(source="product.image", read_only=True)
    category = serializers.CharField(source="product.category", read_only=True)

    # Location
    country_code = serializers.CharField(source="country.code", read_only=True)
    country_name = serializers.CharField(source="country.name", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)

    # Computed fields
    current_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )
    has_discount = serializers.BooleanField(read_only=True)
    discount_percentage = serializers.IntegerField(read_only=True)
    is_in_stock = serializers.BooleanField(read_only=True)
    available_quantity = serializers.IntegerField(read_only=True)
    stock_status = serializers.CharField(read_only=True)

    class Meta:
        model = SpaProduct
        fields = [
            "id",
            # Product info
            "product",
            "product_id",
            "product_name",
            "product_sku",
            "product_image",
            "category",
            # Location
            "country",
            "country_code",
            "country_name",
            "city",
            "city_name",
            # Pricing
            "currency",
            "price",
            "discounted_price",
            "current_price",
            "has_discount",
            "discount_percentage",
            # Stock
            "quantity",
            "available_quantity",
            "is_in_stock",
            "stock_status",
            # Timestamps
            "updated_at",
        ]


class SpaProductDetailSerializer(SpaProductListSerializer):
    """
    Detailed serializer for SpaProduct.
    
    Includes all fields including reserved quantity and low stock threshold.
    """

    class Meta(SpaProductListSerializer.Meta):
        fields = SpaProductListSerializer.Meta.fields + [
            "reserved_quantity",
            "low_stock_threshold",
        ]
