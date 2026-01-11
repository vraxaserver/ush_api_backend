"""
Seed Data Management Command.

Creates demo data for testing the spa center application including:
- Countries and Cities
- Specialties and Services
- Spa Centers/Branches
- Branch Managers and Therapists

Usage:
    python manage.py seed_data
    python manage.py seed_data --clear  # Clear existing data first
    python manage.py seed_data --use-local-images  # Use localhost images
"""

import random
import uuid
from decimal import Decimal
from io import BytesIO
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from accounts.models import EmployeeRole, UserType
from profiles.models import EmployeeProfile
from spacenter.models import (
    City,
    Country,
    Service,
    ServiceImage,
    SpaCenter,
    SpaCenterOperatingHours,
    Specialty,
    TherapistProfile,
)

User = get_user_model()


# =============================================================================
# Image Configuration
# =============================================================================

# Cloud images (Unsplash - free to use)
CLOUD_IMAGES = {
    "services": {
        "swedish_massage": "https://images.unsplash.com/photo-1544161515-4ab6ce6db874?w=800",
        "deep_tissue": "https://images.unsplash.com/photo-1519824145371-296894a0daa9?w=800",
        "thai_massage": "https://images.unsplash.com/photo-1600334089648-b0d9d3028eb2?w=800",
        "hot_stone": "https://images.unsplash.com/photo-1515377905703-c4788e51af15?w=800",
        "aromatherapy": "https://images.unsplash.com/photo-1507652313519-d4e9174996dd?w=800",
        "facial": "https://images.unsplash.com/photo-1570172619644-dfd03ed5d881?w=800",
        "body_scrub": "https://images.unsplash.com/photo-1540555700478-4be289fbecef?w=800",
        "reflexology": "https://images.unsplash.com/photo-1519824145371-296894a0daa9?w=800",
        "couples": "https://images.unsplash.com/photo-1591343395082-e120087004b4?w=800",
        "sports": "https://images.unsplash.com/photo-1519824145371-296894a0daa9?w=800",
    },
    "specialties": {
        "default": "https://images.unsplash.com/photo-1544161515-4ab6ce6db874?w=400",
    },
    "spa_centers": {
        "default": "https://images.unsplash.com/photo-1540555700478-4be289fbecef?w=800",
    },
}

# Local development images (placeholder paths)
LOCAL_IMAGES = {
    "services": {
        "swedish_massage": "/media/services/swedish_massage.jpg",
        "deep_tissue": "/media/services/deep_tissue.jpg",
        "thai_massage": "/media/services/thai_massage.jpg",
        "hot_stone": "/media/services/hot_stone.jpg",
        "aromatherapy": "/media/services/aromatherapy.jpg",
        "facial": "/media/services/facial.jpg",
        "body_scrub": "/media/services/body_scrub.jpg",
        "reflexology": "/media/services/reflexology.jpg",
        "couples": "/media/services/couples.jpg",
        "sports": "/media/services/sports.jpg",
    },
    "specialties": {
        "default": "/media/specialties/default.jpg",
    },
    "spa_centers": {
        "default": "/media/spacenters/default.jpg",
    },
}


class Command(BaseCommand):
    help = "Seed database with demo data for spa center application"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_local_images = False
        self.base_url = ""

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing data before seeding",
        )
        parser.add_argument(
            "--use-local-images",
            action="store_true",
            help="Use local image paths instead of cloud URLs",
        )
        parser.add_argument(
            "--base-url",
            type=str,
            default="http://localhost:8000",
            help="Base URL for local images (default: http://localhost:8000)",
        )

    def handle(self, *args, **options):
        self.use_local_images = options.get("use_local_images", False)
        self.base_url = options.get("base_url", "http://localhost:8000")
        
        if options["clear"]:
            self.clear_data()

        with transaction.atomic():
            self.stdout.write("🌍 Creating countries...")
            countries = self.create_countries()

            self.stdout.write("🏙️ Creating cities...")
            cities = self.create_cities(countries)

            self.stdout.write("⭐ Creating specialties...")
            specialties = self.create_specialties()

            self.stdout.write("💆 Creating services...")
            services = self.create_services(specialties)

            self.stdout.write("👔 Creating branch managers...")
            branch_managers = self.create_branch_managers()

            self.stdout.write("🏢 Creating spa centers...")
            spa_centers = self.create_spa_centers(countries, cities, services, branch_managers)

            self.stdout.write("💪 Creating therapists...")
            self.create_therapists(spa_centers, specialties, services)

            self.stdout.write(self.style.SUCCESS("\n✅ Demo data seeded successfully!"))
            self.print_summary()

    def get_image_url(self, category, key):
        """Get image URL based on configuration."""
        if self.use_local_images:
            images = LOCAL_IMAGES.get(category, {})
            path = images.get(key, images.get("default", ""))
            return urljoin(self.base_url, path)
        else:
            images = CLOUD_IMAGES.get(category, {})
            return images.get(key, images.get("default", ""))

    def download_image(self, url, filename):
        """Download image from URL and return ContentFile."""
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return ContentFile(response.content, name=filename)
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Could not download image: {e}"))
        return None

    def clear_data(self):
        """Clear existing demo data."""
        self.stdout.write(self.style.WARNING("⚠️ Clearing existing data..."))
        
        TherapistProfile.objects.all().delete()
        SpaCenterOperatingHours.objects.all().delete()
        SpaCenter.objects.all().delete()
        ServiceImage.objects.all().delete()
        Service.objects.all().delete()
        Specialty.objects.all().delete()
        City.objects.all().delete()
        Country.objects.all().delete()
        
        # Delete demo users (employees)
        User.objects.filter(email__endswith="@demo.spa.com").delete()
        
        self.stdout.write(self.style.SUCCESS("✓ Existing data cleared"))

    def create_countries(self):
        """Create demo countries with translations."""
        countries_data = [
            {
                "name_en": "United Arab Emirates",
                "name_ar": "الإمارات العربية المتحدة",
                "code": "UAE",
                "phone_code": "+971",
                "sort_order": 1,
            },
            {
                "name_en": "Saudi Arabia",
                "name_ar": "المملكة العربية السعودية",
                "code": "SAU",
                "phone_code": "+966",
                "sort_order": 2,
            },
            {
                "name_en": "Qatar",
                "name_ar": "قطر",
                "code": "QAT",
                "phone_code": "+974",
                "sort_order": 3,
            },
            {
                "name_en": "Kuwait",
                "name_ar": "الكويت",
                "code": "KWT",
                "phone_code": "+965",
                "sort_order": 4,
            },
            {
                "name_en": "Bahrain",
                "name_ar": "البحرين",
                "code": "BHR",
                "phone_code": "+973",
                "sort_order": 5,
            },
            {
                "name_en": "Oman",
                "name_ar": "عُمان",
                "code": "OMN",
                "phone_code": "+968",
                "sort_order": 6,
            },
        ]

        countries = []
        for data in countries_data:
            country, created = Country.objects.update_or_create(
                code=data["code"],
                defaults={
                    "name": data["name_en"],
                    "name_en": data["name_en"],
                    "name_ar": data["name_ar"],
                    "phone_code": data["phone_code"],
                    "sort_order": data["sort_order"],
                    "is_active": True,
                },
            )
            countries.append(country)
            status = "Created" if created else "Updated"
            self.stdout.write(f"  {status}: {country.name}")

        return countries

    def create_cities(self, countries):
        """Create demo cities for each country with translations."""
        cities_data = {
            "UAE": [
                {"name_en": "Dubai", "name_ar": "دبي", "state_en": "Dubai", "state_ar": "دبي"},
                {"name_en": "Abu Dhabi", "name_ar": "أبوظبي", "state_en": "Abu Dhabi", "state_ar": "أبوظبي"},
                {"name_en": "Sharjah", "name_ar": "الشارقة", "state_en": "Sharjah", "state_ar": "الشارقة"},
                {"name_en": "Ajman", "name_ar": "عجمان", "state_en": "Ajman", "state_ar": "عجمان"},
            ],
            "SAU": [
                {"name_en": "Riyadh", "name_ar": "الرياض", "state_en": "Riyadh", "state_ar": "الرياض"},
                {"name_en": "Jeddah", "name_ar": "جدة", "state_en": "Makkah", "state_ar": "مكة المكرمة"},
                {"name_en": "Dammam", "name_ar": "الدمام", "state_en": "Eastern Province", "state_ar": "المنطقة الشرقية"},
                {"name_en": "Mecca", "name_ar": "مكة المكرمة", "state_en": "Makkah", "state_ar": "مكة المكرمة"},
            ],
            "QAT": [
                {"name_en": "Doha", "name_ar": "الدوحة", "state_en": "Doha", "state_ar": "الدوحة"},
                {"name_en": "Al Wakrah", "name_ar": "الوكرة", "state_en": "Al Wakrah", "state_ar": "الوكرة"},
                {"name_en": "Al Khor", "name_ar": "الخور", "state_en": "Al Khor", "state_ar": "الخور"},
            ],
            "KWT": [
                {"name_en": "Kuwait City", "name_ar": "مدينة الكويت", "state_en": "Al Asimah", "state_ar": "العاصمة"},
                {"name_en": "Hawalli", "name_ar": "حولي", "state_en": "Hawalli", "state_ar": "حولي"},
                {"name_en": "Salmiya", "name_ar": "السالمية", "state_en": "Hawalli", "state_ar": "حولي"},
            ],
            "BHR": [
                {"name_en": "Manama", "name_ar": "المنامة", "state_en": "Capital", "state_ar": "العاصمة"},
                {"name_en": "Muharraq", "name_ar": "المحرق", "state_en": "Muharraq", "state_ar": "المحرق"},
                {"name_en": "Riffa", "name_ar": "الرفاع", "state_en": "Southern", "state_ar": "الجنوبية"},
            ],
            "OMN": [
                {"name_en": "Muscat", "name_ar": "مسقط", "state_en": "Muscat", "state_ar": "مسقط"},
                {"name_en": "Salalah", "name_ar": "صلالة", "state_en": "Dhofar", "state_ar": "ظفار"},
                {"name_en": "Sohar", "name_ar": "صحار", "state_en": "North Al Batinah", "state_ar": "شمال الباطنة"},
            ],
        }

        cities = []
        country_map = {c.code: c for c in countries}

        for country_code, city_list in cities_data.items():
            country = country_map.get(country_code)
            if not country:
                continue

            for idx, data in enumerate(city_list):
                city, created = City.objects.update_or_create(
                    country=country,
                    name_en=data["name_en"],
                    defaults={
                        "name": data["name_en"],
                        "name_ar": data["name_ar"],
                        "state": data["state_en"],
                        "state_en": data["state_en"],
                        "state_ar": data["state_ar"],
                        "sort_order": idx,
                        "is_active": True,
                    },
                )
                cities.append(city)

        self.stdout.write(f"  Created {len(cities)} cities")
        return cities

    def create_specialties(self):
        """Create demo specialties with translations."""
        specialties_data = [
            {
                "name_en": "Swedish Massage",
                "name_ar": "التدليك السويدي",
                "description_en": "Classic relaxation massage using long, flowing strokes to promote overall wellness.",
                "description_ar": "تدليك استرخائي كلاسيكي باستخدام حركات طويلة ومتدفقة لتعزيز الصحة العامة.",
            },
            {
                "name_en": "Deep Tissue Massage",
                "name_ar": "تدليك الأنسجة العميقة",
                "description_en": "Intensive massage targeting deep muscle layers for chronic tension relief.",
                "description_ar": "تدليك مكثف يستهدف طبقات العضلات العميقة لتخفيف التوتر المزمن.",
            },
            {
                "name_en": "Thai Massage",
                "name_ar": "التدليك التايلاندي",
                "description_en": "Traditional Thai techniques combining stretching and pressure point therapy.",
                "description_ar": "تقنيات تايلاندية تقليدية تجمع بين التمدد والعلاج بنقاط الضغط.",
            },
            {
                "name_en": "Hot Stone Therapy",
                "name_ar": "العلاج بالأحجار الساخنة",
                "description_en": "Heated basalt stones placed on key points for deep relaxation.",
                "description_ar": "أحجار بازلتية ساخنة توضع على نقاط رئيسية للاسترخاء العميق.",
            },
            {
                "name_en": "Aromatherapy",
                "name_ar": "العلاج بالروائح العطرية",
                "description_en": "Essential oil massage therapy for mind-body balance.",
                "description_ar": "علاج بالتدليك بالزيوت العطرية لتوازن العقل والجسم.",
            },
            {
                "name_en": "Facial Treatment",
                "name_ar": "علاج الوجه",
                "description_en": "Skincare treatments for cleansing, rejuvenation, and anti-aging.",
                "description_ar": "علاجات للعناية بالبشرة للتنظيف والتجديد ومكافحة الشيخوخة.",
            },
            {
                "name_en": "Body Scrub",
                "name_ar": "تقشير الجسم",
                "description_en": "Exfoliating treatments to remove dead skin and improve circulation.",
                "description_ar": "علاجات تقشير لإزالة الجلد الميت وتحسين الدورة الدموية.",
            },
            {
                "name_en": "Reflexology",
                "name_ar": "العلاج الانعكاسي",
                "description_en": "Pressure point therapy on feet and hands to promote healing.",
                "description_ar": "علاج بنقاط الضغط على القدمين واليدين لتعزيز الشفاء.",
            },
        ]

        specialties = []
        for idx, data in enumerate(specialties_data):
            specialty, created = Specialty.objects.update_or_create(
                name_en=data["name_en"],
                defaults={
                    "name": data["name_en"],
                    "name_ar": data["name_ar"],
                    "description": data["description_en"],
                    "description_en": data["description_en"],
                    "description_ar": data["description_ar"],
                    "sort_order": idx,
                    "is_active": True,
                },
            )
            specialties.append(specialty)

        self.stdout.write(f"  Created {len(specialties)} specialties")
        return specialties

    def create_services(self, specialties):
        """Create demo services with translations."""
        services_data = [
            {
                "name_en": "Classic Swedish Massage",
                "name_ar": "التدليك السويدي الكلاسيكي",
                "description_en": "A gentle, relaxing full-body massage using smooth, gliding strokes to ease muscle tension and improve circulation.",
                "description_ar": "تدليك لطيف ومريح لكامل الجسم باستخدام حركات انزلاقية ناعمة لتخفيف توتر العضلات وتحسين الدورة الدموية.",
                "specialty_name": "Swedish Massage",
                "duration_minutes": 60,
                "currency": "AED",
                "base_price": Decimal("250.00"),
                "discount_price": Decimal("199.00"),  # 20% off
                "is_home_service": True,
                "price_for_home_service": Decimal("350.00"),
                "ideal_for_en": "Relaxation, Stress Relief",
                "ideal_for_ar": "الاسترخاء، تخفيف التوتر",
                "image_key": "swedish_massage",
                "benefits": [
                    {"key": "Relaxation", "value": "Promotes deep relaxation and reduces stress"},
                    {"key": "Circulation", "value": "Improves blood flow throughout the body"},
                    {"key": "Flexibility", "value": "Increases muscle flexibility and range of motion"},
                ],
            },
            {
                "name_en": "Deep Tissue Therapy",
                "name_ar": "علاج الأنسجة العميقة",
                "description_en": "Intensive massage focusing on deeper layers of muscle tissue to release chronic patterns of tension.",
                "description_ar": "تدليك مكثف يركز على الطبقات العميقة من الأنسجة العضلية لتحرير أنماط التوتر المزمنة.",
                "specialty_name": "Deep Tissue Massage",
                "duration_minutes": 90,
                "currency": "AED",
                "base_price": Decimal("350.00"),
                "discount_price": None,  # No discount
                "is_home_service": True,
                "price_for_home_service": Decimal("450.00"),
                "ideal_for_en": "Chronic Pain, Athletes",
                "ideal_for_ar": "الألم المزمن، الرياضيين",
                "image_key": "deep_tissue",
                "benefits": [
                    {"key": "Pain Relief", "value": "Targets chronic muscle pain and knots"},
                    {"key": "Recovery", "value": "Speeds up muscle recovery after exercise"},
                    {"key": "Posture", "value": "Helps correct postural imbalances"},
                ],
            },
            {
                "name_en": "Traditional Thai Massage",
                "name_ar": "التدليك التايلاندي التقليدي",
                "description_en": "Ancient healing system combining acupressure, Indian Ayurvedic principles, and assisted yoga postures.",
                "description_ar": "نظام شفاء قديم يجمع بين العلاج بالضغط ومبادئ الأيورفيدا الهندية ووضعيات اليوغا المساعدة.",
                "specialty_name": "Thai Massage",
                "duration_minutes": 120,
                "currency": "AED",
                "base_price": Decimal("400.00"),
                "discount_price": Decimal("320.00"),  # 20% off
                "is_home_service": False,
                "price_for_home_service": None,
                "ideal_for_en": "Flexibility, Energy Balance",
                "ideal_for_ar": "المرونة، توازن الطاقة",
                "image_key": "thai_massage",
                "benefits": [
                    {"key": "Flexibility", "value": "Increases range of motion and flexibility"},
                    {"key": "Energy", "value": "Balances energy flow throughout the body"},
                    {"key": "Stress", "value": "Reduces stress and promotes mental clarity"},
                ],
            },
            {
                "name_en": "Hot Stone Relaxation",
                "name_ar": "استرخاء الأحجار الساخنة",
                "description_en": "Smooth, heated stones are placed on key points of the body while the therapist uses Swedish massage techniques.",
                "description_ar": "توضع أحجار ناعمة ساخنة على نقاط رئيسية من الجسم بينما يستخدم المعالج تقنيات التدليك السويدي.",
                "specialty_name": "Hot Stone Therapy",
                "duration_minutes": 75,
                "currency": "AED",
                "base_price": Decimal("380.00"),
                "discount_price": None,
                "is_home_service": False,
                "price_for_home_service": None,
                "ideal_for_en": "Deep Relaxation, Muscle Tension",
                "ideal_for_ar": "الاسترخاء العميق، توتر العضلات",
                "image_key": "hot_stone",
                "benefits": [
                    {"key": "Heat Therapy", "value": "Heat penetrates deep into muscles for relief"},
                    {"key": "Relaxation", "value": "Promotes profound state of relaxation"},
                    {"key": "Circulation", "value": "Enhances blood circulation"},
                ],
            },
            {
                "name_en": "Aromatherapy Journey",
                "name_ar": "رحلة العلاج بالروائح",
                "description_en": "A sensory experience combining massage with carefully selected essential oils tailored to your needs.",
                "description_ar": "تجربة حسية تجمع بين التدليك والزيوت العطرية المختارة بعناية حسب احتياجاتك.",
                "specialty_name": "Aromatherapy",
                "duration_minutes": 60,
                "currency": "AED",
                "base_price": Decimal("300.00"),
                "discount_price": Decimal("249.00"),  # ~17% off
                "is_home_service": True,
                "price_for_home_service": Decimal("400.00"),
                "ideal_for_en": "Stress Relief, Mood Enhancement",
                "ideal_for_ar": "تخفيف التوتر، تحسين المزاج",
                "image_key": "aromatherapy",
                "benefits": [
                    {"key": "Mood", "value": "Essential oils elevate mood naturally"},
                    {"key": "Sleep", "value": "Promotes better sleep quality"},
                    {"key": "Healing", "value": "Supports natural healing processes"},
                ],
            },
            {
                "name_en": "Luxury Facial Treatment",
                "name_ar": "علاج الوجه الفاخر",
                "description_en": "Premium facial treatment with deep cleansing, exfoliation, mask, and hydration for radiant skin.",
                "description_ar": "علاج فاخر للوجه مع تنظيف عميق وتقشير وقناع وترطيب للحصول على بشرة مشرقة.",
                "specialty_name": "Facial Treatment",
                "duration_minutes": 60,
                "currency": "AED",
                "base_price": Decimal("280.00"),
                "discount_price": None,
                "is_home_service": True,
                "price_for_home_service": Decimal("380.00"),
                "ideal_for_en": "Skin Rejuvenation, Anti-Aging",
                "ideal_for_ar": "تجديد البشرة، مكافحة الشيخوخة",
                "image_key": "facial",
                "benefits": [
                    {"key": "Cleansing", "value": "Deep pore cleansing and purification"},
                    {"key": "Hydration", "value": "Intense moisturization for dry skin"},
                    {"key": "Anti-Aging", "value": "Reduces fine lines and wrinkles"},
                ],
            },
            {
                "name_en": "Dead Sea Salt Scrub",
                "name_ar": "تقشير ملح البحر الميت",
                "description_en": "Exfoliating body treatment using mineral-rich Dead Sea salt to reveal smooth, glowing skin.",
                "description_ar": "علاج تقشير للجسم باستخدام ملح البحر الميت الغني بالمعادن للكشف عن بشرة ناعمة ومتوهجة.",
                "specialty_name": "Body Scrub",
                "duration_minutes": 45,
                "currency": "AED",
                "base_price": Decimal("220.00"),
                "discount_price": Decimal("175.00"),  # ~20% off
                "is_home_service": False,
                "price_for_home_service": None,
                "ideal_for_en": "Skin Renewal, Detox",
                "ideal_for_ar": "تجديد البشرة، إزالة السموم",
                "image_key": "body_scrub",
                "benefits": [
                    {"key": "Exfoliation", "value": "Removes dead skin cells effectively"},
                    {"key": "Minerals", "value": "Infuses skin with essential minerals"},
                    {"key": "Smoothness", "value": "Leaves skin silky smooth"},
                ],
            },
            {
                "name_en": "Foot Reflexology",
                "name_ar": "العلاج الانعكاسي للقدم",
                "description_en": "Therapeutic foot massage applying pressure to specific points that correspond to body organs and systems.",
                "description_ar": "تدليك علاجي للقدم بالضغط على نقاط محددة تتوافق مع أعضاء وأنظمة الجسم.",
                "specialty_name": "Reflexology",
                "duration_minutes": 45,
                "currency": "AED",
                "base_price": Decimal("180.00"),
                "discount_price": None,
                "is_home_service": True,
                "price_for_home_service": Decimal("250.00"),
                "ideal_for_en": "Stress Relief, Overall Wellness",
                "ideal_for_ar": "تخفيف التوتر، الصحة العامة",
                "image_key": "reflexology",
                "benefits": [
                    {"key": "Balance", "value": "Restores body's natural balance"},
                    {"key": "Relaxation", "value": "Deeply relaxing foot treatment"},
                    {"key": "Circulation", "value": "Improves blood flow to extremities"},
                ],
            },
            {
                "name_en": "Couples Massage Package",
                "name_ar": "باقة تدليك للأزواج",
                "description_en": "Romantic side-by-side massage experience for couples in a private suite.",
                "description_ar": "تجربة تدليك رومانسية جنباً إلى جنب للأزواج في جناح خاص.",
                "specialty_name": "Swedish Massage",
                "duration_minutes": 90,
                "currency": "AED",
                "base_price": Decimal("600.00"),
                "discount_price": Decimal("499.00"),  # ~17% off
                "is_home_service": False,
                "price_for_home_service": None,
                "ideal_for_en": "Couples, Special Occasions",
                "ideal_for_ar": "الأزواج، المناسبات الخاصة",
                "image_key": "couples",
                "benefits": [
                    {"key": "Bonding", "value": "Shared relaxation experience"},
                    {"key": "Romance", "value": "Perfect for anniversaries and dates"},
                    {"key": "Privacy", "value": "Private suite for two"},
                ],
            },
            {
                "name_en": "Sports Recovery Massage",
                "name_ar": "تدليك التعافي الرياضي",
                "description_en": "Specialized massage designed for athletes to prevent injury and speed up recovery.",
                "description_ar": "تدليك متخصص مصمم للرياضيين لمنع الإصابات وتسريع التعافي.",
                "specialty_name": "Deep Tissue Massage",
                "duration_minutes": 60,
                "currency": "AED",
                "base_price": Decimal("320.00"),
                "discount_price": None,
                "is_home_service": True,
                "price_for_home_service": Decimal("420.00"),
                "ideal_for_en": "Athletes, Active Individuals",
                "ideal_for_ar": "الرياضيين، الأشخاص النشطين",
                "image_key": "sports",
                "benefits": [
                    {"key": "Recovery", "value": "Accelerates muscle recovery"},
                    {"key": "Prevention", "value": "Helps prevent sports injuries"},
                    {"key": "Performance", "value": "Enhances athletic performance"},
                ],
            },
        ]

        specialty_map = {s.name_en: s for s in specialties}
        services = []

        for idx, data in enumerate(services_data):
            specialty = specialty_map.get(data["specialty_name"])
            if not specialty:
                continue

            image_key = data.pop("image_key", "default")
            
            service, created = Service.objects.update_or_create(
                name_en=data["name_en"],
                defaults={
                    "name": data["name_en"],
                    "name_ar": data["name_ar"],
                    "description": data["description_en"],
                    "description_en": data["description_en"],
                    "description_ar": data["description_ar"],
                    "specialty": specialty,
                    "duration_minutes": data["duration_minutes"],
                    "currency": data["currency"],
                    "base_price": data["base_price"],
                    "discount_price": data["discount_price"],
                    "is_home_service": data["is_home_service"],
                    "price_for_home_service": data["price_for_home_service"],
                    "ideal_for": data["ideal_for_en"],
                    "ideal_for_en": data["ideal_for_en"],
                    "ideal_for_ar": data["ideal_for_ar"],
                    "benefits": data["benefits"],
                    "sort_order": idx,
                    "is_active": True,
                },
            )
            services.append(service)

            # Create image for service (if none exists)
            if not service.images.exists():
                self.create_service_image(service, image_key)
                self.stdout.write(f"    Created image for: {service.name}")

        self.stdout.write(f"  Created {len(services)} services")
        return services

    def create_service_image(self, service, image_key):
        """Create a service image from cloud or local URL."""
        image_url = self.get_image_url("services", image_key)
        filename = f"{slugify(service.name)}_{service.id}.jpg"
        
        if self.use_local_images:
            # For local images, just store the path reference
            ServiceImage.objects.create(
                service=service,
                image=f"services/images/{filename}",
                alt_text=f"{service.name} image",
                is_primary=True,
                sort_order=0,
            )
        else:
            # Download from cloud
            image_content = self.download_image(image_url, filename)
            if image_content:
                service_image = ServiceImage(
                    service=service,
                    alt_text=f"{service.name} image",
                    is_primary=True,
                    sort_order=0,
                )
                service_image.image.save(filename, image_content, save=True)
            else:
                # Fallback to placeholder path
                ServiceImage.objects.create(
                    service=service,
                    image=f"services/images/{filename}",
                    alt_text=f"{service.name} image",
                    is_primary=True,
                    sort_order=0,
                )

    def create_branch_managers(self):
        """Create branch manager users."""
        managers_data = [
            {
                "email": "manager.dubai@demo.spa.com",
                "first_name": "Ahmed",
                "last_name": "Al Maktoum",
                "phone_number": "+971501234567",
            },
            {
                "email": "manager.abudhabi@demo.spa.com",
                "first_name": "Fatima",
                "last_name": "Al Nahyan",
                "phone_number": "+971502345678",
            },
            {
                "email": "manager.riyadh@demo.spa.com",
                "first_name": "Mohammed",
                "last_name": "Al Saud",
                "phone_number": "+966501234567",
            },
            {
                "email": "manager.doha@demo.spa.com",
                "first_name": "Sara",
                "last_name": "Al Thani",
                "phone_number": "+974501234567",
            },
            {
                "email": "manager.kuwait@demo.spa.com",
                "first_name": "Khalid",
                "last_name": "Al Sabah",
                "phone_number": "+965501234567",
            },
        ]

        managers = []
        for data in managers_data:
            user, created = User.objects.update_or_create(
                email=data["email"],
                defaults={
                    "first_name": data["first_name"],
                    "last_name": data["last_name"],
                    "phone_number": data["phone_number"],
                    "user_type": UserType.EMPLOYEE,
                    "is_email_verified": True,
                    "is_active": True,
                },
            )
            
            if created:
                user.set_password("Demo@123")
                user.save()

            # Create or update employee profile
            employee_profile, _ = EmployeeProfile.objects.update_or_create(
                user=user,
                defaults={
                    "role": EmployeeRole.BRANCH_MANAGER,
                    "department": "Management",
                    "is_profile_complete": True,
                },
            )
            
            managers.append(user)

        self.stdout.write(f"  Created {len(managers)} branch managers")
        return managers

    def create_spa_centers(self, countries, cities, services, branch_managers):
        """Create demo spa centers/branches."""
        spa_centers_data = [
            {
                "name_en": "Serenity Spa Dubai Marina",
                "name_ar": "سيرينيتي سبا دبي مارينا",
                "description_en": "Luxurious spa retreat in the heart of Dubai Marina with stunning views.",
                "description_ar": "ملاذ سبا فاخر في قلب دبي مارينا مع إطلالات خلابة.",
                "city_name": "Dubai",
                "country_code": "UAE",
                "address_en": "Marina Walk, Tower 1, Ground Floor",
                "address_ar": "ممشى المارينا، البرج 1، الطابق الأرضي",
                "latitude": Decimal("25.0772"),
                "longitude": Decimal("55.1392"),
                "phone": "+971 4 123 4567",
                "email": "dubai@serenity-spa.com",
                "manager_email": "manager.dubai@demo.spa.com",
            },
            {
                "name_en": "Serenity Spa Abu Dhabi Corniche",
                "name_ar": "سيرينيتي سبا كورنيش أبوظبي",
                "description_en": "Premium wellness center on the beautiful Abu Dhabi Corniche.",
                "description_ar": "مركز صحي متميز على كورنيش أبوظبي الجميل.",
                "city_name": "Abu Dhabi",
                "country_code": "UAE",
                "address_en": "Corniche Road, Nation Towers, Level 2",
                "address_ar": "طريق الكورنيش، أبراج الأمة، الطابق 2",
                "latitude": Decimal("24.4539"),
                "longitude": Decimal("54.3773"),
                "phone": "+971 2 234 5678",
                "email": "abudhabi@serenity-spa.com",
                "manager_email": "manager.abudhabi@demo.spa.com",
            },
            {
                "name_en": "Serenity Spa Riyadh Olaya",
                "name_ar": "سيرينيتي سبا الرياض العليا",
                "description_en": "Elegant spa experience in Riyadh's prestigious Olaya district.",
                "description_ar": "تجربة سبا أنيقة في حي العليا الراقي بالرياض.",
                "city_name": "Riyadh",
                "country_code": "SAU",
                "address_en": "Olaya Street, Kingdom Centre, Level 3",
                "address_ar": "شارع العليا، مركز المملكة، الطابق 3",
                "latitude": Decimal("24.7116"),
                "longitude": Decimal("46.6752"),
                "phone": "+966 11 345 6789",
                "email": "riyadh@serenity-spa.com",
                "manager_email": "manager.riyadh@demo.spa.com",
            },
            {
                "name_en": "Serenity Spa Doha Pearl",
                "name_ar": "سيرينيتي سبا الدوحة اللؤلؤة",
                "description_en": "Exclusive spa on The Pearl-Qatar's stunning waterfront.",
                "description_ar": "سبا حصري على الواجهة البحرية الرائعة للؤلؤة قطر.",
                "city_name": "Doha",
                "country_code": "QAT",
                "address_en": "The Pearl-Qatar, Porto Arabia, Building 15",
                "address_ar": "اللؤلؤة قطر، بورتو أرابيا، المبنى 15",
                "latitude": Decimal("25.3665"),
                "longitude": Decimal("51.5511"),
                "phone": "+974 4 456 7890",
                "email": "doha@serenity-spa.com",
                "manager_email": "manager.doha@demo.spa.com",
            },
            {
                "name_en": "Serenity Spa Kuwait Avenues",
                "name_ar": "سيرينيتي سبا أڤنيوز الكويت",
                "description_en": "Modern spa destination at Kuwait's premier shopping destination.",
                "description_ar": "وجهة سبا حديثة في أفضل وجهة تسوق بالكويت.",
                "city_name": "Kuwait City",
                "country_code": "KWT",
                "address_en": "The Avenues Mall, Phase 4, Level 1",
                "address_ar": "مجمع الأڤنيوز، المرحلة 4، الطابق 1",
                "latitude": Decimal("29.3117"),
                "longitude": Decimal("47.9167"),
                "phone": "+965 2 567 8901",
                "email": "kuwait@serenity-spa.com",
                "manager_email": "manager.kuwait@demo.spa.com",
            },
        ]

        country_map = {c.code: c for c in countries}
        city_map = {(c.country.code, c.name_en): c for c in cities}
        manager_map = {m.email: m for m in branch_managers}
        
        spa_centers = []
        for idx, data in enumerate(spa_centers_data):
            country = country_map.get(data["country_code"])
            city = city_map.get((data["country_code"], data["city_name"]))
            manager = manager_map.get(data["manager_email"])

            if not country or not city:
                continue

            slug = slugify(data["name_en"])
            
            spa_center, created = SpaCenter.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": data["name_en"],
                    "name_en": data["name_en"],
                    "name_ar": data["name_ar"],
                    "description": data["description_en"],
                    "description_en": data["description_en"],
                    "description_ar": data["description_ar"],
                    "country": country,
                    "city": city,
                    "address": data["address_en"],
                    "address_en": data["address_en"],
                    "address_ar": data["address_ar"],
                    "latitude": data["latitude"],
                    "longitude": data["longitude"],
                    "phone": data["phone"],
                    "email": data["email"],
                    "branch_manager": manager,
                    "default_opening_time": "09:00",
                    "default_closing_time": "22:00",
                    "is_active": True,
                    "on_service": True,
                    "sort_order": idx,
                },
            )

            # Add all services to the spa center
            spa_center.services.set(services)

            # Create operating hours
            self.create_operating_hours(spa_center)

            spa_centers.append(spa_center)

        self.stdout.write(f"  Created {len(spa_centers)} spa centers")
        return spa_centers

    def create_operating_hours(self, spa_center):
        """Create operating hours for a spa center."""
        # Standard hours for most days
        for day in range(7):
            is_friday = day == 4  # Friday
            
            SpaCenterOperatingHours.objects.update_or_create(
                spa_center=spa_center,
                day_of_week=day,
                defaults={
                    "opening_time": "14:00" if is_friday else "09:00",
                    "closing_time": "22:00",
                    "is_closed": False,
                },
            )

    def create_therapists(self, spa_centers, specialties, services):
        """Create demo therapists for each spa center."""
        therapists_per_branch = [
            # Dubai branch therapists
            [
                {"first_name": "Maria", "last_name": "Santos", "experience": 8, "specialties": ["Swedish Massage", "Aromatherapy"]},
                {"first_name": "Li", "last_name": "Wei", "experience": 12, "specialties": ["Thai Massage", "Reflexology"]},
                {"first_name": "Priya", "last_name": "Sharma", "experience": 6, "specialties": ["Deep Tissue Massage", "Hot Stone Therapy"]},
            ],
            # Abu Dhabi branch therapists
            [
                {"first_name": "Anna", "last_name": "Kowalski", "experience": 10, "specialties": ["Facial Treatment", "Body Scrub"]},
                {"first_name": "Chen", "last_name": "Mei", "experience": 7, "specialties": ["Swedish Massage", "Thai Massage"]},
            ],
            # Riyadh branch therapists
            [
                {"first_name": "Yuki", "last_name": "Tanaka", "experience": 9, "specialties": ["Deep Tissue Massage", "Reflexology"]},
                {"first_name": "Elena", "last_name": "Popov", "experience": 5, "specialties": ["Aromatherapy", "Swedish Massage"]},
                {"first_name": "Kim", "last_name": "Soo-Young", "experience": 11, "specialties": ["Hot Stone Therapy", "Thai Massage"]},
            ],
            # Doha branch therapists
            [
                {"first_name": "Sophie", "last_name": "Martin", "experience": 8, "specialties": ["Facial Treatment", "Aromatherapy"]},
                {"first_name": "Ling", "last_name": "Zhang", "experience": 14, "specialties": ["Thai Massage", "Reflexology"]},
            ],
            # Kuwait branch therapists
            [
                {"first_name": "Isabella", "last_name": "Garcia", "experience": 6, "specialties": ["Swedish Massage", "Body Scrub"]},
                {"first_name": "Nguyen", "last_name": "Thi", "experience": 9, "specialties": ["Deep Tissue Massage", "Hot Stone Therapy"]},
            ],
        ]

        specialty_map = {s.name_en: s for s in specialties}
        total_therapists = 0

        for spa_center, therapist_list in zip(spa_centers, therapists_per_branch):
            for therapist_data in therapist_list:
                # Create user
                email = f"{therapist_data['first_name'].lower()}.{therapist_data['last_name'].lower()}@demo.spa.com"
                
                user, created = User.objects.update_or_create(
                    email=email,
                    defaults={
                        "first_name": therapist_data["first_name"],
                        "last_name": therapist_data["last_name"],
                        "user_type": UserType.EMPLOYEE,
                        "is_email_verified": True,
                        "is_active": True,
                    },
                )
                
                if created:
                    user.set_password("Demo@123")
                    user.save()

                # Create employee profile
                employee_profile, _ = EmployeeProfile.objects.update_or_create(
                    user=user,
                    defaults={
                        "role": EmployeeRole.THERAPIST,
                        "department": "Spa Services",
                        "branch": spa_center.name,
                        "country": spa_center.country.name,
                        "is_profile_complete": True,
                    },
                )

                # Create therapist profile
                therapist_profile, _ = TherapistProfile.objects.update_or_create(
                    employee_profile=employee_profile,
                    defaults={
                        "spa_center": spa_center,
                        "years_of_experience": therapist_data["experience"],
                        "bio": f"Experienced wellness therapist with {therapist_data['experience']} years of expertise.",
                        "bio_en": f"Experienced wellness therapist with {therapist_data['experience']} years of expertise.",
                        "bio_ar": f"معالج صحي ذو خبرة {therapist_data['experience']} سنوات من الخبرة.",
                        "is_available": True,
                    },
                )

                # Add specialties
                therapist_specialties = [
                    specialty_map[name]
                    for name in therapist_data["specialties"]
                    if name in specialty_map
                ]
                therapist_profile.specialties.set(therapist_specialties)

                # Add services based on specialties
                therapist_services = Service.objects.filter(
                    specialty__in=therapist_specialties
                )
                therapist_profile.services.set(therapist_services)

                total_therapists += 1

        self.stdout.write(f"  Created {total_therapists} therapists")

    def print_summary(self):
        """Print summary of seeded data."""
        discounted_services = Service.objects.filter(discount_price__isnull=False).count()
        home_services = Service.objects.filter(is_home_service=True).count()
        
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("📊 SEED DATA SUMMARY")
        self.stdout.write("=" * 50)
        self.stdout.write(f"  Countries:           {Country.objects.count()}")
        self.stdout.write(f"  Cities:              {City.objects.count()}")
        self.stdout.write(f"  Specialties:         {Specialty.objects.count()}")
        self.stdout.write(f"  Services:            {Service.objects.count()}")
        self.stdout.write(f"    - With Discount:   {discounted_services}")
        self.stdout.write(f"    - Home Service:    {home_services}")
        self.stdout.write(f"  Spa Centers:         {SpaCenter.objects.count()}")
        self.stdout.write(f"  Branch Managers:     {User.objects.filter(employee_profile__role=EmployeeRole.BRANCH_MANAGER).count()}")
        self.stdout.write(f"  Therapists:          {TherapistProfile.objects.count()}")
        self.stdout.write("=" * 50)
        self.stdout.write(f"\n🖼️  Image Mode: {'Local' if self.use_local_images else 'Cloud (Unsplash)'}")
        if self.use_local_images:
            self.stdout.write(f"  Base URL: {self.base_url}")
        self.stdout.write("\n📝 Demo Login Credentials:")
        self.stdout.write("  Email: manager.dubai@demo.spa.com")
        self.stdout.write("  Password: Demo@123")
        self.stdout.write("\n🔗 API Filter Examples:")
        self.stdout.write("  GET /api/v1/spa/services/?country=UAE")
        self.stdout.write("  GET /api/v1/spa/services/?country=SAU&is_home_service=true")
        self.stdout.write("  GET /api/v1/spa/branches/?country=UAE")
        self.stdout.write("  GET /api/v1/spa/cities/by-country/UAE/")
        self.stdout.write("=" * 50 + "\n")
