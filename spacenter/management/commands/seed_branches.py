"""
Seed Branches (Spa Centers and Branch Managers).

Creates spa centers with images and branch manager accounts.
Requires: seed_locations, seed_services to be run first.

Usage:
    python manage.py seed_branches
    python manage.py seed_branches --clear
"""

import random
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.text import slugify

from accounts.models import EmployeeRole, UserType
from profiles.models import EmployeeProfile
from spacenter.models import City, Service, SpaCenter, SpaCenterOperatingHours

from .seed_base import BaseSeedCommand, CLOUD_IMAGES

User = get_user_model()


# Branch name components
BRANCH_PREFIXES = [
    "Serenity Spa",
    "Wellness Haven",
    "Tranquil Touch",
    "Harmony Spa",
    "Bliss Retreat",
    "Zen Wellness",
    "Royal Spa",
    "Oasis Spa",
]

BRANCH_SUFFIXES = [
    "Mall",
    "Downtown",
    "Marina",
    "Beach",
    "Plaza",
    "Tower",
    "Resort",
    "Hotel",
    "Village",
    "Center",
]

# Manager names
MANAGER_FIRST_NAMES = [
    "Ahmed", "Mohammed", "Fatima", "Sara", "Omar", "Layla",
    "Hassan", "Mariam", "Ali", "Noor", "Khalid", "Hana",
    "Youssef", "Aisha", "Ibrahim", "Maryam", "Rashid", "Zainab",
]

MANAGER_LAST_NAMES = [
    "Al-Hassan", "Al-Rashid", "Al-Maktoum", "Al-Nahyan", "Al-Thani",
    "Al-Sabah", "Al-Khalifa", "Al-Said", "Khan", "Patel",
    "Singh", "Ahmed", "Mohammed", "Abdullah", "Rahman",
]


class Command(BaseSeedCommand):
    help = "Seed spa centers with images and branch managers"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.manager_counter = 0

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing branch data before seeding",
        )

    def handle(self, *args, **options):
        # Check prerequisites
        if not City.objects.exists():
            self.stdout.write(self.style.ERROR(
                "❌ No cities found. Run 'python manage.py seed_locations' first."
            ))
            return

        if options["clear"]:
            self.clear_data()

        with transaction.atomic():
            self.stdout.write("🏢 Seeding spa centers with images...")
            spa_centers = self.create_spa_centers()

            self.stdout.write(self.style.SUCCESS(
                f"\n✅ Branches seeded: {len(spa_centers)} spa centers"
            ))
            self.print_image_stats()
            self.print_credentials()

    def clear_data(self):
        """Clear existing branch data."""
        self.stdout.write(self.style.WARNING("⚠️ Clearing branches..."))
        SpaCenterOperatingHours.objects.all().delete()
        SpaCenter.objects.all().delete()
        User.objects.filter(email__endswith="@demo.spa.com", user_type=UserType.EMPLOYEE).filter(
            employee_profile__role=EmployeeRole.BRANCH_MANAGER
        ).delete()
        self.stdout.write(self.style.SUCCESS("✓ Branches cleared"))

    def create_spa_centers(self):
        """Create 3-5 spa centers per city with images."""
        cities = City.objects.select_related("country").all()
        all_spa_centers = []
        spa_image_keys = list(CLOUD_IMAGES.get("spa_centers", {}).keys())

        for city in cities:
            num_branches = random.randint(3, 5)
            city_services = list(Service.objects.filter(city=city))

            for i in range(num_branches):
                prefix = random.choice(BRANCH_PREFIXES)
                suffix = random.choice(BRANCH_SUFFIXES)
                branch_name = f"{prefix} {city.name} {suffix}"

                # Create branch manager
                manager = self.create_branch_manager(city, i)

                slug = slugify(branch_name)[:50]
                lat = Decimal(str(round(random.uniform(24.0, 26.0), 6)))
                lon = Decimal(str(round(random.uniform(50.0, 56.0), 6)))

                spa_center, created = SpaCenter.objects.update_or_create(
                    slug=slug,
                    defaults={
                        "name": branch_name,
                        "name_en": branch_name,
                        "name_ar": f"{prefix} {city.name_ar} {suffix}",
                        "description": f"Premium spa experience at {branch_name}. Enjoy world-class treatments in a serene environment.",
                        "description_en": f"Premium spa experience at {branch_name}. Enjoy world-class treatments in a serene environment.",
                        "description_ar": f"تجربة سبا فاخرة في {city.name_ar}. استمتع بعلاجات عالمية المستوى في بيئة هادئة.",
                        "country": city.country,
                        "city": city,
                        "address": f"{random.randint(1, 100)} {suffix} Street, {city.name}",
                        "address_en": f"{random.randint(1, 100)} {suffix} Street, {city.name}",
                        "address_ar": f"شارع {suffix} رقم {random.randint(1, 100)}، {city.name_ar}",
                        "latitude": lat,
                        "longitude": lon,
                        "phone": f"{city.country.phone_code} {random.randint(100, 999)} {random.randint(1000, 9999)}",
                        "email": f"{slug[:20]}@demo.spa.com",
                        "branch_manager": manager,
                        "default_opening_time": "09:00",
                        "default_closing_time": "22:00",
                        "is_active": True,
                        "on_service": True,
                        "sort_order": i,
                    },
                )

                # Download and save spa center image
                if not spa_center.image:
                    image_key = random.choice(spa_image_keys) if spa_image_keys else None
                    if image_key:
                        image_url = self.get_image_url("spa_centers", image_key)
                        if image_url:
                            image_content = self.download_image(
                                image_url,
                                f"spa_{slug}.jpg"
                            )
                            if image_content:
                                spa_center.image.save(
                                    f"spa_{slug}.jpg",
                                    image_content,
                                    save=True
                                )

                # Assign services to spa center
                if city_services:
                    spa_center.services.set(city_services)

                # Create operating hours
                self.create_operating_hours(spa_center)

                all_spa_centers.append(spa_center)

            self.stdout.write(f"    {city.name} ({city.country.code}): {num_branches} spa centers")

        return all_spa_centers

    def create_branch_manager(self, city, index):
        """Create a branch manager user with avatar."""
        self.manager_counter += 1
        email = f"manager.{slugify(city.name)}.{index}@demo.spa.com"
        first_name = random.choice(MANAGER_FIRST_NAMES)
        last_name = random.choice(MANAGER_LAST_NAMES)

        user, created = User.objects.update_or_create(
            email=email,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
                "phone_number": f"{city.country.phone_code}50{random.randint(1000000, 9999999)}",
                "user_type": UserType.EMPLOYEE,
                "is_email_verified": True,
                "is_active": True,
            },
        )

        if created:
            user.set_password("Demo@123")
            user.save()

        # Create or update employee profile with avatar
        employee_profile, _ = EmployeeProfile.objects.update_or_create(
            user=user,
            defaults={
                "role": EmployeeRole.BRANCH_MANAGER,
                "department": "Management",
                "job_title": "Branch Manager",
                "branch": city.name,
                "country": city.country.name,
            },
        )

        # Download and save avatar
        if not employee_profile.avatar:
            # Alternate between male and female avatars
            gender = "male" if self.manager_counter % 2 == 0 else "female"
            avatar_key = f"{gender}_{(self.manager_counter % 5) + 1}"
            avatar_url = self.get_image_url("avatars", avatar_key)
            if avatar_url:
                avatar_content = self.download_image(
                    avatar_url,
                    f"avatar_manager_{user.id}.jpg"
                )
                if avatar_content:
                    employee_profile.avatar.save(
                        f"avatar_manager_{user.id}.jpg",
                        avatar_content,
                        save=True
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

    def print_credentials(self):
        """Print demo login credentials."""
        self.stdout.write("\n📝 Demo Branch Manager Credentials:")
        self.stdout.write("  Email: manager.dubai.0@demo.spa.com")
        self.stdout.write("  Password: Demo@123")
