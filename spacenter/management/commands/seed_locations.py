"""
Seed Locations (Countries and Cities).

Creates countries with flags and cities for Gulf region.

Usage:
    python manage.py seed_locations
    python manage.py seed_locations --clear
"""

from django.db import transaction
from django.utils.text import slugify

from spacenter.models import City, Country

from .seed_base import BaseSeedCommand, CLOUD_IMAGES


class Command(BaseSeedCommand):
    help = "Seed countries and cities with flag images"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing location data before seeding",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.clear_data()

        with transaction.atomic():
            self.stdout.write("🌍 Seeding countries with flags...")
            countries = self.create_countries()

            self.stdout.write("🏙️ Seeding cities...")
            cities = self.create_cities(countries)

            self.stdout.write(self.style.SUCCESS(
                f"\n✅ Locations seeded: {len(countries)} countries, {len(cities)} cities"
            ))
            self.print_image_stats()

    def clear_data(self):
        """Clear existing location data."""
        self.stdout.write(self.style.WARNING("⚠️ Clearing locations..."))
        City.objects.all().delete()
        Country.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("✓ Locations cleared"))

    def create_countries(self):
        """Create countries with flag images."""
        countries_data = [
            {
                "name_en": "United Arab Emirates",
                "name_ar": "الإمارات العربية المتحدة",
                "code": "UAE",
                "phone_code": "+971",
            },
            {
                "name_en": "Saudi Arabia",
                "name_ar": "المملكة العربية السعودية",
                "code": "SAU",
                "phone_code": "+966",
            },
            {
                "name_en": "Qatar",
                "name_ar": "قطر",
                "code": "QAT",
                "phone_code": "+974",
            },
            {
                "name_en": "Kuwait",
                "name_ar": "الكويت",
                "code": "KWT",
                "phone_code": "+965",
            },
            {
                "name_en": "Bahrain",
                "name_ar": "البحرين",
                "code": "BHR",
                "phone_code": "+973",
            },
            {
                "name_en": "Oman",
                "name_ar": "عُمان",
                "code": "OMN",
                "phone_code": "+968",
            },
        ]

        countries = []
        for idx, data in enumerate(countries_data):
            country, created = Country.objects.update_or_create(
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

            # Download and save flag image
            if not country.flag:
                flag_url = self.get_image_url("flags", data["code"])
                if flag_url:
                    flag_content = self.download_image(
                        flag_url,
                        f"flag_{data['code'].lower()}.png"
                    )
                    if flag_content:
                        country.flag.save(
                            f"flag_{data['code'].lower()}.png",
                            flag_content,
                            save=True
                        )
                        self.stdout.write(f"    ✓ {data['name_en']} flag downloaded")

            countries.append(country)

        self.stdout.write(f"  Created {len(countries)} countries")
        return countries

    def create_cities(self, countries):
        """Create cities for each country."""
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
                {"name_en": "Dammam", "name_ar": "الدمام", "state_en": "Eastern", "state_ar": "الشرقية"},
                {"name_en": "Khobar", "name_ar": "الخبر", "state_en": "Eastern", "state_ar": "الشرقية"},
            ],
            "QAT": [
                {"name_en": "Doha", "name_ar": "الدوحة", "state_en": "Doha", "state_ar": "الدوحة"},
                {"name_en": "Al Wakrah", "name_ar": "الوكرة", "state_en": "Al Wakrah", "state_ar": "الوكرة"},
                {"name_en": "Lusail", "name_ar": "لوسيل", "state_en": "Lusail", "state_ar": "لوسيل"},
            ],
            "KWT": [
                {"name_en": "Kuwait City", "name_ar": "مدينة الكويت", "state_en": "Al Asimah", "state_ar": "العاصمة"},
                {"name_en": "Hawalli", "name_ar": "حولي", "state_en": "Hawalli", "state_ar": "حولي"},
                {"name_en": "Salmiya", "name_ar": "السالمية", "state_en": "Hawalli", "state_ar": "حولي"},
            ],
            "BHR": [
                {"name_en": "Manama", "name_ar": "المنامة", "state_en": "Capital", "state_ar": "العاصمة"},
                {"name_en": "Riffa", "name_ar": "الرفاع", "state_en": "Southern", "state_ar": "الجنوبية"},
                {"name_en": "Muharraq", "name_ar": "المحرق", "state_en": "Muharraq", "state_ar": "المحرق"},
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
