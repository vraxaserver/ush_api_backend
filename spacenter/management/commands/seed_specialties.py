"""
Seed Specialties.

Creates spa specialties with icon images.

Usage:
    python manage.py seed_specialties
    python manage.py seed_specialties --clear
"""

from django.db import transaction
from django.utils.text import slugify

from spacenter.models import Specialty

from .seed_base import BaseSeedCommand, CLOUD_IMAGES


class Command(BaseSeedCommand):
    help = "Seed specialties with icon images"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing specialty data before seeding",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.clear_data()

        with transaction.atomic():
            self.stdout.write("⭐ Seeding specialties with icons...")
            specialties = self.create_specialties()

            self.stdout.write(self.style.SUCCESS(
                f"\n✅ Specialties seeded: {len(specialties)}"
            ))
            self.print_image_stats()

    def clear_data(self):
        """Clear existing specialty data."""
        self.stdout.write(self.style.WARNING("⚠️ Clearing specialties..."))
        Specialty.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("✓ Specialties cleared"))

    def create_specialties(self):
        """Create specialties with icon images."""
        specialties_data = [
            {
                "name_en": "Swedish Massage",
                "name_ar": "التدليك السويدي",
                "description_en": "Classic relaxation massage using long, flowing strokes to ease tension and improve circulation.",
                "description_ar": "تدليك استرخاء كلاسيكي باستخدام حركات طويلة ومتدفقة لتخفيف التوتر وتحسين الدورة الدموية.",
                "image_key": "swedish_massage",
            },
            {
                "name_en": "Deep Tissue Massage",
                "name_ar": "تدليك الأنسجة العميقة",
                "description_en": "Intensive therapeutic massage targeting deep muscle layers to release chronic tension.",
                "description_ar": "تدليك علاجي مكثف يستهدف طبقات العضلات العميقة لإطلاق التوتر المزمن.",
                "image_key": "deep_tissue",
            },
            {
                "name_en": "Thai Massage",
                "name_ar": "التدليك التايلاندي",
                "description_en": "Traditional Thai healing combining acupressure, stretching, and yoga-like postures.",
                "description_ar": "الشفاء التايلاندي التقليدي الذي يجمع بين العلاج بالضغط والتمدد ووضعيات اليوغا.",
                "image_key": "thai_massage",
            },
            {
                "name_en": "Hot Stone Therapy",
                "name_ar": "العلاج بالأحجار الساخنة",
                "description_en": "Heated basalt stones placed on body points for deep relaxation and muscle relief.",
                "description_ar": "أحجار بازلت ساخنة توضع على نقاط الجسم للاسترخاء العميق وتخفيف العضلات.",
                "image_key": "hot_stone",
            },
            {
                "name_en": "Aromatherapy",
                "name_ar": "العلاج بالروائح العطرية",
                "description_en": "Therapeutic massage using essential oils for physical and emotional wellbeing.",
                "description_ar": "تدليك علاجي باستخدام الزيوت العطرية للرفاهية الجسدية والعاطفية.",
                "image_key": "aromatherapy",
            },
            {
                "name_en": "Facial Treatment",
                "name_ar": "علاج الوجه",
                "description_en": "Professional skincare treatments for cleansing, rejuvenation, and anti-aging.",
                "description_ar": "علاجات العناية بالبشرة الاحترافية للتنظيف والتجديد ومكافحة الشيخوخة.",
                "image_key": "facial",
            },
            {
                "name_en": "Body Scrub",
                "name_ar": "تقشير الجسم",
                "description_en": "Exfoliating treatment to remove dead skin cells and reveal smooth, glowing skin.",
                "description_ar": "علاج تقشيري لإزالة خلايا الجلد الميتة والكشف عن بشرة ناعمة ومتوهجة.",
                "image_key": "body_scrub",
            },
            {
                "name_en": "Reflexology",
                "name_ar": "العلاج الانعكاسي",
                "description_en": "Pressure point therapy on feet and hands to promote healing and relaxation.",
                "description_ar": "علاج نقاط الضغط على القدمين واليدين لتعزيز الشفاء والاسترخاء.",
                "image_key": "reflexology",
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

            # Download and save icon image
            if not specialty.icon:
                icon_url = self.get_image_url("specialties", data["image_key"])
                if icon_url:
                    icon_content = self.download_image(
                        icon_url,
                        f"specialty_{slugify(data['name_en'])}.jpg"
                    )
                    if icon_content:
                        specialty.icon.save(
                            f"specialty_{slugify(data['name_en'])}.jpg",
                            icon_content,
                            save=True
                        )
                        self.stdout.write(f"    ✓ {data['name_en']} icon downloaded")

            specialties.append(specialty)

        self.stdout.write(f"  Created {len(specialties)} specialties")
        return specialties
