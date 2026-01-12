"""
Spa Center Serializers.

Serializers for spa centers, services, specialties, and therapist management.
Supports multi-language (English, Arabic) output.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from accounts.models import EmployeeRole, UserType
from profiles.models import EmployeeProfile

from .models import (
    City,
    Country,
    Service,
    ServiceImage,
    SpaCenter,
    SpaCenterOperatingHours,
    Specialty,
    TherapistProfile,
    ProductCategory,
    BaseProduct,
    SpaProduct,
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
            "is_home_service",
            "price_for_home_service",
            "home_service_price",
            "ideal_for",
            "ideal_for_en",
            "ideal_for_ar",
            "benefits",
            "images",
            "branches",
            "is_active",
            "sort_order",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_branches(self, obj):
        """Get list of branches offering this service."""
        return [
            {"id": str(b.id), "name": b.name}
            for b in obj.spa_centers.filter(is_active=True)[:5]
        ]

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
            "is_home_service",
            "price_for_home_service",
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
    current_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )
    has_discount = serializers.BooleanField(read_only=True)
    discount_percentage = serializers.IntegerField(read_only=True)

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
            "is_home_service",
            "home_service_price",
            "ideal_for",
            "primary_image",
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
    therapist_count = serializers.SerializerMethodField()
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
            "therapist_count",
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

    def get_therapist_count(self, obj):
        return obj.therapists.filter(is_available=True).count()

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
# Therapist Serializers
# =============================================================================

class TherapistProfileSerializer(serializers.ModelSerializer):
    """Serializer for therapist profile with translations."""

    user_id = serializers.UUIDField(source="employee_profile.user.id", read_only=True)
    full_name = serializers.CharField(
        source="employee_profile.user.get_full_name",
        read_only=True,
    )
    email = serializers.EmailField(source="employee_profile.user.email", read_only=True)
    phone = serializers.CharField(
        source="employee_profile.user.phone_number",
        read_only=True,
    )
    spa_center_name = serializers.CharField(source="spa_center.name", read_only=True)
    country_name = serializers.SerializerMethodField()
    city_name = serializers.SerializerMethodField()
    specialties = SpecialtyListSerializer(many=True, read_only=True)
    services = ServiceListSerializer(many=True, read_only=True)

    class Meta:
        model = TherapistProfile
        fields = [
            "id",
            "user_id",
            "full_name",
            "email",
            "phone",
            "spa_center",
            "spa_center_name",
            "country_name",
            "city_name",
            "specialties",
            "services",
            "years_of_experience",
            "bio",
            "bio_en",
            "bio_ar",
            "is_available",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_country_name(self, obj):
        if obj.spa_center and obj.spa_center.country:
            return obj.spa_center.country.name
        return None

    def get_city_name(self, obj):
        if obj.spa_center and obj.spa_center.city:
            return obj.spa_center.city.name
        return None


class TherapistCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a therapist by branch manager.
    
    Creates both User and TherapistProfile in one request.
    """

    # User fields
    email = serializers.EmailField(required=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    first_name = serializers.CharField(max_length=150, required=True)
    last_name = serializers.CharField(max_length=150, required=True)
    password = serializers.CharField(write_only=True, min_length=8)

    # Therapist profile fields
    specialty_ids = serializers.PrimaryKeyRelatedField(
        queryset=Specialty.objects.filter(is_active=True),
        many=True,
        required=False,
    )
    service_ids = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.filter(is_active=True),
        many=True,
        required=False,
    )
    years_of_experience = serializers.IntegerField(default=0, min_value=0)
    bio = serializers.CharField(required=False, allow_blank=True)
    bio_en = serializers.CharField(required=False, allow_blank=True)
    bio_ar = serializers.CharField(required=False, allow_blank=True)

    def validate_email(self, value):
        """Check email uniqueness."""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_phone_number(self, value):
        """Check phone uniqueness if provided."""
        if value and User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        """Create user, employee profile, and therapist profile."""
        request = self.context.get("request")
        branch_manager = request.user
        
        try:
            spa_center = branch_manager.managed_spa_center
        except SpaCenter.DoesNotExist:
            raise serializers.ValidationError(
                "You must be assigned as a branch manager to create therapists."
            )

        specialty_ids = validated_data.pop("specialty_ids", [])
        service_ids = validated_data.pop("service_ids", [])
        years_of_experience = validated_data.pop("years_of_experience", 0)
        bio = validated_data.pop("bio", "")
        bio_en = validated_data.pop("bio_en", "")
        bio_ar = validated_data.pop("bio_ar", "")
        password = validated_data.pop("password")

        user = User.objects.create_user(
            email=validated_data["email"],
            phone_number=validated_data.get("phone_number") or None,
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            password=password,
            user_type=UserType.EMPLOYEE,
            is_email_verified=True,
        )

        employee_profile, _ = EmployeeProfile.objects.get_or_create(
            user=user,
            defaults={
                "role": EmployeeRole.THERAPIST,
                "branch": spa_center.name,
                "country": spa_center.country.name if spa_center.country else "",
            },
        )
        employee_profile.role = EmployeeRole.THERAPIST
        employee_profile.save()

        therapist_profile = TherapistProfile.objects.create(
            employee_profile=employee_profile,
            spa_center=spa_center,
            years_of_experience=years_of_experience,
            bio=bio,
            bio_en=bio_en or bio,
            bio_ar=bio_ar,
        )

        if specialty_ids:
            therapist_profile.specialties.set(specialty_ids)
        if service_ids:
            therapist_profile.services.set(service_ids)

        return therapist_profile


class TherapistUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating therapist profile."""

    specialty_ids = serializers.PrimaryKeyRelatedField(
        queryset=Specialty.objects.filter(is_active=True),
        many=True,
        write_only=True,
        required=False,
    )
    service_ids = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.filter(is_active=True),
        many=True,
        write_only=True,
        required=False,
    )

    class Meta:
        model = TherapistProfile
        fields = [
            "spa_center",
            "specialty_ids",
            "service_ids",
            "years_of_experience",
            "bio",
            "bio_en",
            "bio_ar",
            "is_available",
        ]

    def update(self, instance, validated_data):
        specialty_ids = validated_data.pop("specialty_ids", None)
        service_ids = validated_data.pop("service_ids", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if specialty_ids is not None:
            instance.specialties.set(specialty_ids)
        if service_ids is not None:
            instance.services.set(service_ids)

        return instance



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

