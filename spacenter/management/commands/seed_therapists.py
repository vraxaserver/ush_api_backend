"""
Seed Therapists.

Creates therapist profiles with avatars.
Requires: seed_branches to be run first.

Usage:
    python manage.py seed_therapists
    python manage.py seed_therapists --clear
"""

import random

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.text import slugify

from accounts.models import EmployeeRole, UserType
from profiles.models import EmployeeProfile
from spacenter.models import Service, SpaCenter, Specialty, TherapistProfile

from .seed_base import BaseSeedCommand, CLOUD_IMAGES

User = get_user_model()


# Therapist names (diverse international names)
THERAPIST_FIRST_NAMES = [
    "Maria", "Li", "Priya", "Anna", "Chen", "Yuki", "Elena", "Kim",
    "Sophie", "Ling", "Isabella", "Nguyen", "Fatima", "Sara", "Aisha",
    "Maryam", "Noor", "Layla", "Hana", "Jasmine", "Rosa", "Mei",
    "Grace", "Emily", "Sophia", "Olivia", "Emma", "Ava", "Mia", "Luna",
]

THERAPIST_LAST_NAMES = [
    "Santos", "Wei", "Sharma", "Kowalski", "Mei", "Tanaka", "Popov",
    "Park", "Martin", "Zhang", "Garcia", "Thi", "Al-Hassan", "Kim",
    "Lee", "Nakamura", "Patel", "Nguyen", "Chen", "Wang", "Singh",
    "Johnson", "Williams", "Brown", "Davis", "Miller", "Wilson",
]


class Command(BaseSeedCommand):
    help = "Seed therapists with avatars"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.therapist_counter = 0

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing therapist data before seeding",
        )

    def handle(self, *args, **options):
        # Check prerequisites
        if not SpaCenter.objects.exists():
            self.stdout.write(self.style.ERROR(
                "❌ No spa centers found. Run 'python manage.py seed_branches' first."
            ))
            return

        if options["clear"]:
            self.clear_data()

        with transaction.atomic():
            self.stdout.write("💪 Seeding therapists with avatars...")
            therapists = self.create_therapists()

            self.stdout.write(self.style.SUCCESS(
                f"\n✅ Therapists seeded: {len(therapists)}"
            ))
            self.print_image_stats()
            self.print_credentials()

    def clear_data(self):
        """Clear existing therapist data."""
        self.stdout.write(self.style.WARNING("⚠️ Clearing therapists..."))
        TherapistProfile.objects.all().delete()
        User.objects.filter(
            email__startswith="therapist.",
            email__endswith="@demo.spa.com"
        ).delete()
        self.stdout.write(self.style.SUCCESS("✓ Therapists cleared"))

    def create_therapists(self):
        """Create 2-4 therapists per spa center with avatars."""
        spa_centers = SpaCenter.objects.select_related("city", "country").all()
        specialties = list(Specialty.objects.all())
        all_therapists = []
        avatar_keys = list(CLOUD_IMAGES.get("avatars", {}).keys())

        for spa_center in spa_centers:
            num_therapists = random.randint(2, 4)

            for i in range(num_therapists):
                therapist = self.create_therapist(
                    spa_center,
                    specialties,
                    avatar_keys
                )
                if therapist:
                    all_therapists.append(therapist)

        # Group by spa center for display
        by_city = {}
        for t in all_therapists:
            city = t.spa_center.city.name if t.spa_center else "Unknown"
            by_city[city] = by_city.get(city, 0) + 1

        for city, count in sorted(by_city.items()):
            self.stdout.write(f"    {city}: {count} therapists")

        return all_therapists

    def create_therapist(self, spa_center, specialties, avatar_keys):
        """Create a single therapist with avatar."""
        self.therapist_counter += 1
        first_name = random.choice(THERAPIST_FIRST_NAMES)
        last_name = random.choice(THERAPIST_LAST_NAMES)
        email = f"therapist.{self.therapist_counter}@demo.spa.com"

        # Create user
        user, created = User.objects.update_or_create(
            email=email,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
                "phone_number": f"{spa_center.country.phone_code}55{random.randint(1000000, 9999999)}",
                "user_type": UserType.EMPLOYEE,
                "is_email_verified": True,
                "is_active": True,
            },
        )

        if created:
            user.set_password("Demo@123")
            user.save()

        # Create employee profile
        years_exp = random.randint(2, 15)
        employee_profile, _ = EmployeeProfile.objects.update_or_create(
            user=user,
            defaults={
                "role": EmployeeRole.THERAPIST,
                "department": "Spa Services",
                "job_title": "Spa Therapist",
                "branch": spa_center.name,
                "country": spa_center.country.name,
                "bio": f"Experienced massage therapist with {years_exp} years of expertise in various techniques.",
            },
        )

        # Download and save avatar (mostly female for spa industry)
        if not employee_profile.avatar and avatar_keys:
            # 80% female, 20% male for spa therapists
            gender = "female" if random.random() < 0.8 else "male"
            matching_keys = [k for k in avatar_keys if k.startswith(gender)]
            if matching_keys:
                avatar_key = random.choice(matching_keys)
                avatar_url = self.get_image_url("avatars", avatar_key)
                if avatar_url:
                    avatar_content = self.download_image(
                        avatar_url,
                        f"avatar_therapist_{user.id}.jpg"
                    )
                    if avatar_content:
                        employee_profile.avatar.save(
                            f"avatar_therapist_{user.id}.jpg",
                            avatar_content,
                            save=True
                        )

        # Create therapist profile
        therapist_profile, _ = TherapistProfile.objects.update_or_create(
            employee_profile=employee_profile,
            defaults={
                "spa_center": spa_center,
                "years_of_experience": years_exp,
                "bio": f"Skilled therapist with {years_exp} years of experience in wellness and relaxation techniques.",
                "bio_en": f"Skilled therapist with {years_exp} years of experience in wellness and relaxation techniques.",
                "bio_ar": f"معالج ماهر مع {years_exp} سنوات من الخبرة في تقنيات العافية والاسترخاء.",
                "is_available": True,
            },
        )

        # Assign 2-3 random specialties
        if specialties:
            therapist_specialties = random.sample(
                specialties,
                min(random.randint(2, 3), len(specialties))
            )
            therapist_profile.specialties.set(therapist_specialties)

            # Assign services based on specialties
            therapist_services = Service.objects.filter(
                specialty__in=therapist_specialties,
                city=spa_center.city,
            )
            therapist_profile.services.set(therapist_services)

        return therapist_profile

    def print_credentials(self):
        """Print demo login credentials."""
        self.stdout.write("\n📝 Demo Therapist Credentials:")
        self.stdout.write("  Email: therapist.1@demo.spa.com")
        self.stdout.write("  Password: Demo@123")
