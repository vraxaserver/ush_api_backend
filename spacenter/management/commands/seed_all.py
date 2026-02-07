"""
Seed All Data.

Master command that runs all seed commands in the correct order.

Usage:
    python manage.py seed_all
    python manage.py seed_all --clear
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from spacenter.models import (
    City,
    Country,
    Service,
    ServiceArrangement,
    ServiceImage,
    SpaCenter,
    SpaCenterOperatingHours,
    Specialty,
    TherapistProfile,
)
from bookings.models import Booking


class Command(BaseCommand):
    help = "Seed all demo data for the spa center application"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear all existing data before seeding",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n" + "=" * 60 +
            "\n🚀 SEEDING SPA CENTER APPLICATION DATA" +
            "\n" + "=" * 60
        ))

        if options["clear"]:
            # Use the robust clean_all_data command instead of individual clear flags
            call_command("clean_all_data")

        # Run seed commands in order (without clearing individually as we cleaned globally)
        self.stdout.write("\n" + "-" * 40)
        self.stdout.write("Step 1/8: Seeding Locations (Countries & Cities)")
        self.stdout.write("-" * 40)
        call_command("seed_locations")

        self.stdout.write("\n" + "-" * 40)
        self.stdout.write("Step 2/8: Seeding Specialties")
        self.stdout.write("-" * 40)
        call_command("seed_specialties")

        self.stdout.write("\n" + "-" * 40)
        self.stdout.write("Step 3/8: Seeding Services")
        self.stdout.write("-" * 40)
        call_command("seed_services")

        self.stdout.write("\n" + "-" * 40)
        self.stdout.write("Step 4/8: Seeding Spa Centers & Branch Managers")
        self.stdout.write("-" * 40)
        call_command("seed_branches")

        self.stdout.write("\n" + "-" * 40)
        self.stdout.write("Step 5/8: Seeding Therapists")
        self.stdout.write("-" * 40)
        call_command("seed_therapists")

        self.stdout.write("\n" + "-" * 40)
        self.stdout.write("Step 6/8: Seeding Products")
        self.stdout.write("-" * 40)
        call_command("seed_products")

        self.stdout.write("\n" + "-" * 40)
        self.stdout.write("Step 7/8: Seeding Customers")
        self.stdout.write("-" * 40)
        call_command("seed_customers")

        self.stdout.write("\n" + "-" * 40)
        self.stdout.write("Step 8/8: Seeding Bookings")
        self.stdout.write("-" * 40)
        call_command("seed_bookings")

        # Print final summary
        self.print_summary()

    def print_summary(self):
        """Print final summary of all seeded data."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("📊 FINAL SEED DATA SUMMARY")
        self.stdout.write("=" * 60)

        self.stdout.write(f"\n  🌍 Countries:        {Country.objects.count()}")
        self.stdout.write(f"  🏙️ Cities:           {City.objects.count()}")
        self.stdout.write(f"  ⭐ Specialties:      {Specialty.objects.count()}")

        total_services = Service.objects.count()
        home_services = Service.objects.filter(is_home_service=True).count()
        discounted = Service.objects.filter(discount_price__isnull=False).count()
        self.stdout.write(f"  💆 Services:         {total_services}")
        self.stdout.write(f"      - Home Services: {home_services}")
        self.stdout.write(f"      - Discounted:    {discounted}")

        self.stdout.write(f"  🏢 Spa Centers:      {SpaCenter.objects.count()}")
        self.stdout.write(f"  💪 Therapists:       {TherapistProfile.objects.count()}")
        self.stdout.write(f"  🖼️ Service Images:   {ServiceImage.objects.count()}")
        self.stdout.write(f"  🏠 Arrangements:     {ServiceArrangement.objects.count()}")
        self.stdout.write(f"  📅 Bookings:         {Booking.objects.count()}")

        # Per-city breakdown
        self.stdout.write("\n📍 Per-City Breakdown:")
        for city in City.objects.select_related("country").all()[:10]:
            branches = SpaCenter.objects.filter(city=city).count()
            services = Service.objects.filter(city=city).count()
            home = Service.objects.filter(city=city, is_home_service=True).count()
            self.stdout.write(
                f"  {city.name} ({city.country.code}): "
                f"{branches} branches, {services} services ({home} home)"
            )

        if City.objects.count() > 10:
            self.stdout.write(f"  ... and {City.objects.count() - 10} more cities")

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("📝 DEMO LOGIN CREDENTIALS")
        self.stdout.write("=" * 60)
        self.stdout.write("\n  Branch Manager:")
        self.stdout.write("    Email:    manager.dubai.0@demo.spa.com")
        self.stdout.write("    Password: Demo@123")
        self.stdout.write("\n  Therapist:")
        self.stdout.write("    Email:    therapist.1@demo.spa.com")
        self.stdout.write("    Password: Demo@123")
        self.stdout.write("\n  Customer:")
        self.stdout.write("    Email:    customer.1@demo.spa.com")
        self.stdout.write("    Password: Demo@123")
        self.stdout.write("    (VIP):    vip.customer@demo.spa.com")

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("🔗 API ENDPOINTS")
        self.stdout.write("=" * 60)
        self.stdout.write("\n  GET /api/v1/spa/services/?country=UAE")
        self.stdout.write("  GET /api/v1/spa/services/?country=UAE&city_name=Dubai")
        self.stdout.write("  GET /api/v1/spa/services/?country=SAU&is_home_service=true")
        self.stdout.write("  GET /api/v1/spa/services/?has_discount=true")
        self.stdout.write("  GET /api/v1/spa/branches/?country=QAT")
        self.stdout.write("  GET /api/v1/spa/cities/by-country/UAE/")
        self.stdout.write("  GET /api/v1/spa/therapists/?country=UAE")

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("✅ ALL SEED DATA CREATED SUCCESSFULLY!"))
        self.stdout.write("=" * 60 + "\n")
