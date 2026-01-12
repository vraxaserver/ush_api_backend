"""
Seed Services.

Creates spa services with images for each city.
Requires: seed_locations, seed_specialties to be run first.

Usage:
    python manage.py seed_services
    python manage.py seed_services --clear
"""

import random
from decimal import Decimal

from django.db import transaction
from django.utils.text import slugify

from spacenter.models import City, Country, Service, ServiceImage, Specialty

from .seed_base import BaseSeedCommand, CLOUD_IMAGES


# Currency mapping by country code
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
        "description_en": "A gentle, relaxing full-body massage using smooth, gliding strokes to ease muscle tension and improve circulation.",
        "description_ar": "تدليك لطيف ومريح لكامل الجسم باستخدام حركات انزلاقية ناعمة لتخفيف توتر العضلات وتحسين الدورة الدموية.",
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
            {"key": "Relaxation", "value": "Promotes deep relaxation and reduces stress"},
            {"key": "Circulation", "value": "Improves blood flow throughout the body"},
            {"key": "Flexibility", "value": "Increases muscle flexibility"},
        ],
    },
    {
        "name_en": "Deep Tissue Therapy",
        "name_ar": "علاج الأنسجة العميقة",
        "description_en": "Intensive massage focusing on deeper layers of muscle tissue to release chronic patterns of tension.",
        "description_ar": "تدليك مكثف يركز على الطبقات العميقة من الأنسجة العضلية لتحرير أنماط التوتر المزمنة.",
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
        "base_price": Decimal("400.00"),
        "discount_price": Decimal("320.00"),
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
        "base_price": Decimal("380.00"),
        "discount_price": None,
        "is_home_service": False,
        "price_for_home_service": None,
        "ideal_for_en": "Deep Relaxation, Muscle Tension",
        "ideal_for_ar": "الاسترخاء العميق، توتر العضلات",
        "image_key": "hot_stone",
        "benefits": [
            {"key": "Heat Therapy", "value": "Heat penetrates deep into muscles"},
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
        "base_price": Decimal("300.00"),
        "discount_price": Decimal("249.00"),
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
        "base_price": Decimal("280.00"),
        "discount_price": None,
        "is_home_service": False,
        "price_for_home_service": None,
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
        "base_price": Decimal("220.00"),
        "discount_price": Decimal("175.00"),
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
        "description_en": "Therapeutic foot massage applying pressure to specific points that correspond to body organs.",
        "description_ar": "تدليك علاجي للقدم بالضغط على نقاط محددة تتوافق مع أعضاء الجسم.",
        "specialty_name": "Reflexology",
        "duration_minutes": 45,
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
        "base_price": Decimal("600.00"),
        "discount_price": Decimal("499.00"),
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


class Command(BaseSeedCommand):
    help = "Seed services with images for each city"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing service data before seeding",
        )

    def handle(self, *args, **options):
        # Check prerequisites
        if not Country.objects.exists():
            self.stdout.write(self.style.ERROR(
                "❌ No countries found. Run 'python manage.py seed_locations' first."
            ))
            return

        if not Specialty.objects.exists():
            self.stdout.write(self.style.ERROR(
                "❌ No specialties found. Run 'python manage.py seed_specialties' first."
            ))
            return

        if options["clear"]:
            self.clear_data()

        with transaction.atomic():
            self.stdout.write("💆 Seeding services per city...")
            services = self.create_services()

            self.stdout.write(self.style.SUCCESS(
                f"\n✅ Services seeded: {len(services)}"
            ))
            self.print_image_stats()

    def clear_data(self):
        """Clear existing service data."""
        self.stdout.write(self.style.WARNING("⚠️ Clearing services..."))
        ServiceImage.objects.all().delete()
        Service.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("✓ Services cleared"))

    def create_services(self):
        """Create services for each city with images."""
        cities = City.objects.select_related("country").all()
        specialties = {s.name_en: s for s in Specialty.objects.all()}
        all_services = []

        for city in cities:
            country = city.country
            currency = CURRENCY_BY_COUNTRY.get(country.code, "AED")

            # Shuffle templates to vary home services per city
            templates = SERVICE_TEMPLATES.copy()
            random.shuffle(templates)

            # Ensure 2-3 home services per city
            home_service_count = 0
            max_home_services = random.randint(2, 3)

            for idx, template in enumerate(templates):
                specialty = specialties.get(template["specialty_name"])
                if not specialty:
                    continue

                # Determine home service status
                original_is_home = template["is_home_service"]
                if home_service_count < max_home_services:
                    is_home_service = True
                    if original_is_home:
                        price_for_home = template["price_for_home_service"]
                    else:
                        price_for_home = template["base_price"] + Decimal("100.00")
                    home_service_count += 1
                else:
                    is_home_service = False
                    price_for_home = None

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

                # Create service image
                if not service.images.exists():
                    self.create_service_image(service, template["image_key"])

                all_services.append(service)

            home_count = sum(1 for s in all_services[-10:] if s.is_home_service)
            self.stdout.write(f"    {city.name} ({country.code}): 10 services ({home_count} home)")

        return all_services

    def create_service_image(self, service, image_key):
        """Download and create service image."""
        image_url = self.get_image_url("services", image_key)
        if not image_url:
            return

        filename = f"service_{slugify(service.name)[:30]}_{service.id}.jpg"
        image_content = self.download_image(image_url, filename)

        if image_content:
            service_image = ServiceImage(
                service=service,
                alt_text=f"{service.name} image",
                is_primary=True,
                sort_order=0,
            )
            service_image.image.save(filename, image_content, save=True)
