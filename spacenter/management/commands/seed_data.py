"""
Seed Data Management Command.

Creates demo data for testing the spa center application including:
- Countries and Cities
- Specialties and Services (with city/country assignment)
- Spa Centers/Branches (3-5 per city)
- Branch Managers and Therapists
- Each city has 2-3 home services

Usage:
    python manage.py seed_data
    python manage.py seed_data --clear  # Clear existing data first
    python manage.py seed_data --use-local-images  # Use localhost images
"""

import random
import uuid
from decimal import Decimal
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
}

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
}

# Currency mapping by country
CURRENCY_BY_COUNTRY = {
    "UAE": "AED",
    "SAU": "SAR",
    "QAT": "QAR",
    "KWT": "KWD",
    "BHR": "BHD",
    "OMN": "OMR",
}

# Service templates
SERVICE_TEMPLATES = [
    {
        "name_en": "Classic Swedish Massage",
        "name_ar": "التدليك السويدي الكلاسيكي",
        "description_en": "A gentle, relaxing full-body massage using smooth, gliding strokes.",
        "description_ar": "تدليك لطيف ومريح لكامل الجسم باستخدام حركات انزلاقية ناعمة.",
        "specialty_name": "Swedish Massage",
        "duration_minutes": 60,
        "base_price": Decimal("250.00"),
        "discount_price": Decimal("199.00"),
        "is_home_service": True,
        "price_for_home_service": Decimal("350.00"),
        "ideal_for_en": "Relaxation, Stress Relief",
        "ideal_for_ar": "الاسترخاء، تخفيف التوتر",
        "image_key": "swedish_massage",
        "benefits": [
            {"key": "Relaxation", "value": "Promotes deep relaxation"},
            {"key": "Circulation", "value": "Improves blood flow"},
        ],
    },
    {
        "name_en": "Deep Tissue Therapy",
        "name_ar": "علاج الأنسجة العميقة",
        "description_en": "Intensive massage focusing on deeper layers of muscle tissue.",
        "description_ar": "تدليك مكثف يركز على الطبقات العميقة من الأنسجة العضلية.",
        "specialty_name": "Deep Tissue Massage",
        "duration_minutes": 90,
        "base_price": Decimal("350.00"),
        "discount_price": None,
        "is_home_service": True,
        "price_for_home_service": Decimal("450.00"),
        "ideal_for_en": "Chronic Pain, Athletes",
        "ideal_for_ar": "الألم المزمن، الرياضيين",
        "image_key": "deep_tissue",
        "benefits": [
            {"key": "Pain Relief", "value": "Targets chronic muscle pain"},
            {"key": "Recovery", "value": "Speeds up muscle recovery"},
        ],
    },
    {
        "name_en": "Traditional Thai Massage",
        "name_ar": "التدليك التايلاندي التقليدي",
        "description_en": "Ancient healing combining acupressure and assisted yoga postures.",
        "description_ar": "نظام شفاء قديم يجمع بين العلاج بالضغط ووضعيات اليوغا.",
        "specialty_name": "Thai Massage",
        "duration_minutes": 120,
        "base_price": Decimal("400.00"),
        "discount_price": Decimal("320.00"),
        "is_home_service": False,
        "price_for_home_service": None,
        "ideal_for_en": "Flexibility, Energy Balance",
        "ideal_for_ar": "المرونة، توازن الطاقة",
        "image_key": "thai_massage",
        "benefits": [
            {"key": "Flexibility", "value": "Increases range of motion"},
            {"key": "Energy", "value": "Balances energy flow"},
        ],
    },
    {
        "name_en": "Hot Stone Relaxation",
        "name_ar": "استرخاء الأحجار الساخنة",
        "description_en": "Heated stones placed on key points for deep relaxation.",
        "description_ar": "أحجار ساخنة توضع على نقاط رئيسية للاسترخاء العميق.",
        "specialty_name": "Hot Stone Therapy",
        "duration_minutes": 75,
        "base_price": Decimal("380.00"),
        "discount_price": None,
        "is_home_service": False,
        "price_for_home_service": None,
        "ideal_for_en": "Deep Relaxation",
        "ideal_for_ar": "الاسترخاء العميق",
        "image_key": "hot_stone",
        "benefits": [
            {"key": "Heat Therapy", "value": "Heat penetrates deep into muscles"},
            {"key": "Relaxation", "value": "Promotes profound relaxation"},
        ],
    },
    {
        "name_en": "Aromatherapy Journey",
        "name_ar": "رحلة العلاج بالروائح",
        "description_en": "Massage with carefully selected essential oils.",
        "description_ar": "تدليك بالزيوت العطرية المختارة بعناية.",
        "specialty_name": "Aromatherapy",
        "duration_minutes": 60,
        "base_price": Decimal("300.00"),
        "discount_price": Decimal("249.00"),
        "is_home_service": True,
        "price_for_home_service": Decimal("400.00"),
        "ideal_for_en": "Stress Relief, Mood Enhancement",
        "ideal_for_ar": "تخفيف التوتر، تحسين المزاج",
        "image_key": "aromatherapy",
        "benefits": [
            {"key": "Mood", "value": "Essential oils elevate mood"},
            {"key": "Sleep", "value": "Promotes better sleep"},
        ],
    },
    {
        "name_en": "Luxury Facial Treatment",
        "name_ar": "علاج الوجه الفاخر",
        "description_en": "Premium facial with deep cleansing and hydration.",
        "description_ar": "علاج فاخر للوجه مع تنظيف عميق وترطيب.",
        "specialty_name": "Facial Treatment",
        "duration_minutes": 60,
        "base_price": Decimal("280.00"),
        "discount_price": None,
        "is_home_service": False,
        "price_for_home_service": None,
        "ideal_for_en": "Skin Rejuvenation",
        "ideal_for_ar": "تجديد البشرة",
        "image_key": "facial",
        "benefits": [
            {"key": "Cleansing", "value": "Deep pore cleansing"},
            {"key": "Hydration", "value": "Intense moisturization"},
        ],
    },
    {
        "name_en": "Dead Sea Salt Scrub",
        "name_ar": "تقشير ملح البحر الميت",
        "description_en": "Exfoliating treatment using mineral-rich Dead Sea salt.",
        "description_ar": "علاج تقشير باستخدام ملح البحر الميت الغني بالمعادن.",
        "specialty_name": "Body Scrub",
        "duration_minutes": 45,
        "base_price": Decimal("220.00"),
        "discount_price": Decimal("175.00"),
        "is_home_service": False,
        "price_for_home_service": None,
        "ideal_for_en": "Skin Renewal, Detox",
        "ideal_for_ar": "تجديد البشرة، إزالة السموم",
        "image_key": "body_scrub",
        "benefits": [
            {"key": "Exfoliation", "value": "Removes dead skin cells"},
            {"key": "Minerals", "value": "Infuses skin with minerals"},
        ],
    },
    {
        "name_en": "Foot Reflexology",
        "name_ar": "العلاج الانعكاسي للقدم",
        "description_en": "Pressure point therapy on feet for overall wellness.",
        "description_ar": "علاج بنقاط الضغط على القدمين للصحة العامة.",
        "specialty_name": "Reflexology",
        "duration_minutes": 45,
        "base_price": Decimal("180.00"),
        "discount_price": None,
        "is_home_service": True,
        "price_for_home_service": Decimal("250.00"),
        "ideal_for_en": "Stress Relief, Wellness",
        "ideal_for_ar": "تخفيف التوتر، الصحة",
        "image_key": "reflexology",
        "benefits": [
            {"key": "Balance", "value": "Restores body's balance"},
            {"key": "Relaxation", "value": "Deeply relaxing"},
        ],
    },
    {
        "name_en": "Couples Massage Package",
        "name_ar": "باقة تدليك للأزواج",
        "description_en": "Romantic side-by-side massage for couples.",
        "description_ar": "تدليك رومانسي جنباً إلى جنب للأزواج.",
        "specialty_name": "Swedish Massage",
        "duration_minutes": 90,
        "base_price": Decimal("600.00"),
        "discount_price": Decimal("499.00"),
        "is_home_service": False,
        "price_for_home_service": None,
        "ideal_for_en": "Couples, Special Occasions",
        "ideal_for_ar": "الأزواج، المناسبات الخاصة",
        "image_key": "couples",
        "benefits": [
            {"key": "Bonding", "value": "Shared relaxation"},
            {"key": "Romance", "value": "Perfect for anniversaries"},
        ],
    },
    {
        "name_en": "Sports Recovery Massage",
        "name_ar": "تدليك التعافي الرياضي",
        "description_en": "Specialized massage for athletes and active individuals.",
        "description_ar": "تدليك متخصص للرياضيين والأشخاص النشطين.",
        "specialty_name": "Deep Tissue Massage",
        "duration_minutes": 60,
        "base_price": Decimal("320.00"),
        "discount_price": None,
        "is_home_service": True,
        "price_for_home_service": Decimal("420.00"),
        "ideal_for_en": "Athletes, Active Individuals",
        "ideal_for_ar": "الرياضيين، الأشخاص النشطين",
        "image_key": "sports",
        "benefits": [
            {"key": "Recovery", "value": "Accelerates muscle recovery"},
            {"key": "Prevention", "value": "Helps prevent injuries"},
        ],
    },
]

# Branch name prefixes
BRANCH_PREFIXES = [
    "Serenity Spa",
    "Wellness Haven",
    "Tranquil Touch",
    "Harmony Spa",
    "Bliss Retreat",
]

# Branch name suffixes based on location type
BRANCH_SUFFIXES = [
    "Mall",
    "Downtown",
    "Marina",
    "Beach",
    "Plaza",
    "Tower",
    "Resort",
    "Hotel",
]

# Therapist names
THERAPIST_FIRST_NAMES = [
    "Maria", "Li", "Priya", "Anna", "Chen", "Yuki", "Elena", "Kim",
    "Sophie", "Ling", "Isabella", "Nguyen", "Fatima", "Sara", "Aisha",
    "Maryam", "Noor", "Layla", "Hana", "Jasmine", "Rosa", "Mei",
]

THERAPIST_LAST_NAMES = [
    "Santos", "Wei", "Sharma", "Kowalski", "Mei", "Tanaka", "Popov",
    "Soo-Young", "Martin", "Zhang", "Garcia", "Thi", "Al-Hassan", "Kim",
    "Park", "Nakamura", "Patel", "Nguyen", "Chen", "Lee", "Wang",
]


class Command(BaseCommand):
    help = "Seed database with demo data for spa center application"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_local_images = False
        self.base_url = ""
        self.manager_counter = 0
        self.therapist_counter = 0

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

            self.stdout.write("💆 Creating services per city...")
            services_by_city = self.create_services_per_city(cities, specialties)

            self.stdout.write("🏢 Creating spa centers (3-5 per city)...")
            spa_centers = self.create_spa_centers_per_city(cities, services_by_city)

            self.stdout.write("💪 Creating therapists...")
            self.create_therapists(spa_centers, specialties)

            self.stdout.write(self.style.SUCCESS("\n✅ Demo data seeded successfully!"))
            self.print_summary()

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
        User.objects.filter(email__endswith="@demo.spa.com").delete()

        self.stdout.write(self.style.SUCCESS("✓ Existing data cleared"))

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

    def create_countries(self):
        """Create demo countries."""
        countries_data = [
            {"name_en": "United Arab Emirates", "name_ar": "الإمارات العربية المتحدة", "code": "UAE", "phone_code": "+971"},
            {"name_en": "Saudi Arabia", "name_ar": "المملكة العربية السعودية", "code": "SAU", "phone_code": "+966"},
            {"name_en": "Qatar", "name_ar": "قطر", "code": "QAT", "phone_code": "+974"},
            {"name_en": "Kuwait", "name_ar": "الكويت", "code": "KWT", "phone_code": "+965"},
            {"name_en": "Bahrain", "name_ar": "البحرين", "code": "BHR", "phone_code": "+973"},
            {"name_en": "Oman", "name_ar": "عُمان", "code": "OMN", "phone_code": "+968"},
        ]

        countries = []
        for idx, data in enumerate(countries_data):
            country, _ = Country.objects.update_or_create(
                code=data["code"],
                defaults={
                    "name": data["name_en"],
                    "name_en": data["name_en"],
                    "name_ar": data["name_ar"],
                    "phone_code": data["phone_code"],
                    "sort_order": idx,
                    "is_active": True,
                },
            )
            countries.append(country)

        self.stdout.write(f"  Created {len(countries)} countries")
        return countries

    def create_cities(self, countries):
        """Create demo cities for each country."""
        cities_data = {
            "UAE": [
                {"name_en": "Dubai", "name_ar": "دبي", "state_en": "Dubai", "state_ar": "دبي"},
                {"name_en": "Abu Dhabi", "name_ar": "أبوظبي", "state_en": "Abu Dhabi", "state_ar": "أبوظبي"},
                {"name_en": "Sharjah", "name_ar": "الشارقة", "state_en": "Sharjah", "state_ar": "الشارقة"},
            ],
            "SAU": [
                {"name_en": "Riyadh", "name_ar": "الرياض", "state_en": "Riyadh", "state_ar": "الرياض"},
                {"name_en": "Jeddah", "name_ar": "جدة", "state_en": "Makkah", "state_ar": "مكة المكرمة"},
                {"name_en": "Dammam", "name_ar": "الدمام", "state_en": "Eastern", "state_ar": "الشرقية"},
            ],
            "QAT": [
                {"name_en": "Doha", "name_ar": "الدوحة", "state_en": "Doha", "state_ar": "الدوحة"},
                {"name_en": "Al Wakrah", "name_ar": "الوكرة", "state_en": "Al Wakrah", "state_ar": "الوكرة"},
            ],
            "KWT": [
                {"name_en": "Kuwait City", "name_ar": "مدينة الكويت", "state_en": "Al Asimah", "state_ar": "العاصمة"},
                {"name_en": "Hawalli", "name_ar": "حولي", "state_en": "Hawalli", "state_ar": "حولي"},
            ],
            "BHR": [
                {"name_en": "Manama", "name_ar": "المنامة", "state_en": "Capital", "state_ar": "العاصمة"},
                {"name_en": "Riffa", "name_ar": "الرفاع", "state_en": "Southern", "state_ar": "الجنوبية"},
            ],
            "OMN": [
                {"name_en": "Muscat", "name_ar": "مسقط", "state_en": "Muscat", "state_ar": "مسقط"},
                {"name_en": "Salalah", "name_ar": "صلالة", "state_en": "Dhofar", "state_ar": "ظفار"},
            ],
        }

        cities = []
        country_map = {c.code: c for c in countries}

        for country_code, city_list in cities_data.items():
            country = country_map.get(country_code)
            if not country:
                continue

            for idx, data in enumerate(city_list):
                city, _ = City.objects.update_or_create(
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
        """Create demo specialties."""
        specialties_data = [
            {"name_en": "Swedish Massage", "name_ar": "التدليك السويدي", "description_en": "Classic relaxation massage"},
            {"name_en": "Deep Tissue Massage", "name_ar": "تدليك الأنسجة العميقة", "description_en": "Intensive muscle therapy"},
            {"name_en": "Thai Massage", "name_ar": "التدليك التايلاندي", "description_en": "Traditional Thai techniques"},
            {"name_en": "Hot Stone Therapy", "name_ar": "العلاج بالأحجار الساخنة", "description_en": "Heated stone therapy"},
            {"name_en": "Aromatherapy", "name_ar": "العلاج بالروائح العطرية", "description_en": "Essential oil massage"},
            {"name_en": "Facial Treatment", "name_ar": "علاج الوجه", "description_en": "Skincare treatments"},
            {"name_en": "Body Scrub", "name_ar": "تقشير الجسم", "description_en": "Exfoliating treatments"},
            {"name_en": "Reflexology", "name_ar": "العلاج الانعكاسي", "description_en": "Pressure point therapy"},
        ]

        specialties = []
        for idx, data in enumerate(specialties_data):
            specialty, _ = Specialty.objects.update_or_create(
                name_en=data["name_en"],
                defaults={
                    "name": data["name_en"],
                    "name_ar": data["name_ar"],
                    "description": data["description_en"],
                    "description_en": data["description_en"],
                    "sort_order": idx,
                    "is_active": True,
                },
            )
            specialties.append(specialty)

        self.stdout.write(f"  Created {len(specialties)} specialties")
        return specialties

    def create_services_per_city(self, cities, specialties):
        """Create services for each city. Each city gets all service types with 2-3 home services."""
        specialty_map = {s.name_en: s for s in specialties}
        services_by_city = {}

        for city in cities:
            city_services = []
            country = city.country
            currency = CURRENCY_BY_COUNTRY.get(country.code, "AED")

            # Shuffle templates to vary which services are home services per city
            templates = SERVICE_TEMPLATES.copy()
            random.shuffle(templates)

            # Ensure 2-3 home services per city
            home_service_count = 0
            max_home_services = random.randint(2, 3)

            for idx, template in enumerate(templates):
                # Determine if this should be a home service
                original_is_home = template["is_home_service"]
                
                # Force some services to be home services if we haven't reached quota
                if home_service_count < max_home_services and not original_is_home:
                    is_home_service = True
                    price_for_home = template["base_price"] + Decimal("100.00")
                elif original_is_home and home_service_count < max_home_services:
                    is_home_service = True
                    price_for_home = template["price_for_home_service"]
                    home_service_count += 1
                else:
                    is_home_service = original_is_home and home_service_count < max_home_services
                    price_for_home = template["price_for_home_service"] if is_home_service else None
                    if is_home_service:
                        home_service_count += 1

                specialty = specialty_map.get(template["specialty_name"])
                if not specialty:
                    continue

                # Create unique service name for this city
                service_name_en = f"{template['name_en']} - {city.name}"
                service_name_ar = f"{template['name_ar']} - {city.name_ar}"

                service, created = Service.objects.update_or_create(
                    name_en=service_name_en,
                    city=city,
                    defaults={
                        "name": service_name_en,
                        "name_ar": service_name_ar,
                        "description": template["description_en"],
                        "description_en": template["description_en"],
                        "description_ar": template["description_ar"],
                        "specialty": specialty,
                        "country": country,
                        "duration_minutes": template["duration_minutes"],
                        "currency": currency,
                        "base_price": template["base_price"],
                        "discount_price": template["discount_price"],
                        "is_home_service": is_home_service,
                        "price_for_home_service": price_for_home,
                        "ideal_for": template["ideal_for_en"],
                        "ideal_for_en": template["ideal_for_en"],
                        "ideal_for_ar": template["ideal_for_ar"],
                        "benefits": template["benefits"],
                        "sort_order": idx,
                        "is_active": True,
                    },
                )
                city_services.append(service)

                # Create image for service
                if not service.images.exists():
                    self.create_service_image(service, template["image_key"])

            services_by_city[city.id] = city_services
            home_count = sum(1 for s in city_services if s.is_home_service)
            self.stdout.write(f"    {city.name}: {len(city_services)} services ({home_count} home services)")

        total_services = sum(len(s) for s in services_by_city.values())
        self.stdout.write(f"  Created {total_services} total services")
        return services_by_city

    def create_service_image(self, service, image_key):
        """Create a service image."""
        image_url = self.get_image_url("services", image_key)
        filename = f"{slugify(service.name)}_{service.id}.jpg"

        if self.use_local_images:
            ServiceImage.objects.create(
                service=service,
                image=f"services/images/{filename}",
                alt_text=f"{service.name} image",
                is_primary=True,
                sort_order=0,
            )
        else:
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
                ServiceImage.objects.create(
                    service=service,
                    image=f"services/images/{filename}",
                    alt_text=f"{service.name} image",
                    is_primary=True,
                    sort_order=0,
                )

    def create_spa_centers_per_city(self, cities, services_by_city):
        """Create 3-5 spa centers per city."""
        all_spa_centers = []

        for city in cities:
            num_branches = random.randint(3, 5)
            city_services = services_by_city.get(city.id, [])

            for i in range(num_branches):
                prefix = random.choice(BRANCH_PREFIXES)
                suffix = random.choice(BRANCH_SUFFIXES)
                branch_name = f"{prefix} {city.name} {suffix}"

                # Create branch manager
                manager = self.create_branch_manager(city, i)

                slug = slugify(branch_name)[:50]
                lat = Decimal(str(round(random.uniform(24.0, 26.0), 4)))
                lon = Decimal(str(round(random.uniform(50.0, 56.0), 4)))

                spa_center, _ = SpaCenter.objects.update_or_create(
                    slug=slug,
                    defaults={
                        "name": branch_name,
                        "name_en": branch_name,
                        "name_ar": f"{prefix} {city.name_ar} {suffix}",
                        "description": f"Premium spa experience at {branch_name}",
                        "description_en": f"Premium spa experience at {branch_name}",
                        "country": city.country,
                        "city": city,
                        "address": f"{random.randint(1, 100)} {suffix} Street, {city.name}",
                        "address_en": f"{random.randint(1, 100)} {suffix} Street, {city.name}",
                        "latitude": lat,
                        "longitude": lon,
                        "phone": f"{city.country.phone_code} {random.randint(100, 999)} {random.randint(1000, 9999)}",
                        "email": f"{slugify(branch_name)[:20]}@demo.spa.com",
                        "branch_manager": manager,
                        "default_opening_time": "09:00",
                        "default_closing_time": "22:00",
                        "is_active": True,
                        "on_service": True,
                        "sort_order": i,
                    },
                )

                # Assign services to spa center
                spa_center.services.set(city_services)

                # Create operating hours
                self.create_operating_hours(spa_center)

                all_spa_centers.append(spa_center)

            self.stdout.write(f"    {city.name}: {num_branches} spa centers")

        self.stdout.write(f"  Created {len(all_spa_centers)} total spa centers")
        return all_spa_centers

    def create_branch_manager(self, city, index):
        """Create a branch manager user."""
        self.manager_counter += 1
        email = f"manager.{slugify(city.name)}.{index}@demo.spa.com"

        user, created = User.objects.update_or_create(
            email=email,
            defaults={
                "first_name": random.choice(THERAPIST_FIRST_NAMES),
                "last_name": random.choice(THERAPIST_LAST_NAMES),
                "phone_number": f"{city.country.phone_code}50{random.randint(1000000, 9999999)}",
                "user_type": UserType.EMPLOYEE,
                "is_email_verified": True,
                "is_active": True,
            },
        )

        if created:
            user.set_password("Demo@123")
            user.save()

        EmployeeProfile.objects.update_or_create(
            user=user,
            defaults={
                "role": EmployeeRole.BRANCH_MANAGER,
                "department": "Management",
                "is_profile_complete": True,
            },
        )

        return user

    def create_operating_hours(self, spa_center):
        """Create operating hours for a spa center."""
        for day in range(7):
            is_friday = day == 4
            SpaCenterOperatingHours.objects.update_or_create(
                spa_center=spa_center,
                day_of_week=day,
                defaults={
                    "opening_time": "14:00" if is_friday else "09:00",
                    "closing_time": "22:00",
                    "is_closed": False,
                },
            )

    def create_therapists(self, spa_centers, specialties):
        """Create 2-4 therapists per spa center."""
        total_therapists = 0

        for spa_center in spa_centers:
            num_therapists = random.randint(2, 4)

            for i in range(num_therapists):
                self.therapist_counter += 1
                first_name = random.choice(THERAPIST_FIRST_NAMES)
                last_name = random.choice(THERAPIST_LAST_NAMES)
                email = f"therapist.{self.therapist_counter}@demo.spa.com"

                user, created = User.objects.update_or_create(
                    email=email,
                    defaults={
                        "first_name": first_name,
                        "last_name": last_name,
                        "user_type": UserType.EMPLOYEE,
                        "is_email_verified": True,
                        "is_active": True,
                    },
                )

                if created:
                    user.set_password("Demo@123")
                    user.save()

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

                years_exp = random.randint(2, 15)
                therapist_profile, _ = TherapistProfile.objects.update_or_create(
                    employee_profile=employee_profile,
                    defaults={
                        "spa_center": spa_center,
                        "years_of_experience": years_exp,
                        "bio": f"Experienced therapist with {years_exp} years of expertise.",
                        "bio_en": f"Experienced therapist with {years_exp} years of expertise.",
                        "is_available": True,
                    },
                )

                # Assign 2-3 random specialties
                therapist_specialties = random.sample(specialties, min(random.randint(2, 3), len(specialties)))
                therapist_profile.specialties.set(therapist_specialties)

                # Assign services based on specialties
                therapist_services = Service.objects.filter(
                    specialty__in=therapist_specialties,
                    city=spa_center.city,
                )
                therapist_profile.services.set(therapist_services)

                total_therapists += 1

        self.stdout.write(f"  Created {total_therapists} therapists")

    def print_summary(self):
        """Print summary of seeded data."""
        discounted_services = Service.objects.filter(discount_price__isnull=False).count()
        home_services = Service.objects.filter(is_home_service=True).count()

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("📊 SEED DATA SUMMARY")
        self.stdout.write("=" * 60)
        self.stdout.write(f"  Countries:           {Country.objects.count()}")
        self.stdout.write(f"  Cities:              {City.objects.count()}")
        self.stdout.write(f"  Specialties:         {Specialty.objects.count()}")
        self.stdout.write(f"  Services:            {Service.objects.count()}")
        self.stdout.write(f"    - With Discount:   {discounted_services}")
        self.stdout.write(f"    - Home Services:   {home_services}")
        self.stdout.write(f"  Spa Centers:         {SpaCenter.objects.count()}")
        self.stdout.write(f"  Branch Managers:     {User.objects.filter(employee_profile__role=EmployeeRole.BRANCH_MANAGER).count()}")
        self.stdout.write(f"  Therapists:          {TherapistProfile.objects.count()}")
        self.stdout.write("=" * 60)

        # Print per-city breakdown
        self.stdout.write("\n📍 Per-City Breakdown:")
        for city in City.objects.all():
            branches = SpaCenter.objects.filter(city=city).count()
            services = Service.objects.filter(city=city).count()
            home = Service.objects.filter(city=city, is_home_service=True).count()
            self.stdout.write(f"  {city.name} ({city.country.code}): {branches} branches, {services} services ({home} home)")

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(f"🖼️  Image Mode: {'Local' if self.use_local_images else 'Cloud (Unsplash)'}")
        self.stdout.write("\n📝 Demo Login Credentials:")
        self.stdout.write("  Email: manager.dubai.0@demo.spa.com")
        self.stdout.write("  Password: Demo@123")
        self.stdout.write("\n🔗 API Filter Examples:")
        self.stdout.write("  GET /api/v1/spa/services/?country=UAE")
        self.stdout.write("  GET /api/v1/spa/services/?country=UAE&city_name=Dubai")
        self.stdout.write("  GET /api/v1/spa/services/?country=SAU&is_home_service=true")
        self.stdout.write("  GET /api/v1/spa/branches/?country=QAT")
        self.stdout.write("=" * 60 + "\n")
