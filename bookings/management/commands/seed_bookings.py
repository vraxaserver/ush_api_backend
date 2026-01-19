"""
Seed Bookings Data.

Creates service arrangements, time slots, and sample bookings for testing.
Requires: seed_branches to be run first (spa centers and services needed).

Usage:
    python manage.py seed_bookings
    python manage.py seed_bookings --clear
"""

import random
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from bookings.models import Booking, ServiceArrangement, TimeSlot
from spacenter.models import AddOnService, Service, SpaCenter, TherapistProfile

User = get_user_model()


# =============================================================================
# Seed Data Configuration
# =============================================================================

ARRANGEMENT_CONFIGS = [
    {
        "type": "single_room",
        "labels": ["Private Room A", "Private Room B", "Private Suite 1", "Comfort Room"],
        "cleanup": 15,
    },
    {
        "type": "couple_room",
        "labels": ["Couple Suite", "Romance Room", "Duo Retreat", "Partner Space"],
        "cleanup": 20,
    },
    {
        "type": "vip_suite",
        "labels": ["VIP Suite", "Executive Suite", "Luxury Retreat", "Royal Chamber"],
        "cleanup": 25,
    },
    {
        "type": "open_area",
        "labels": ["Open Spa Area", "Garden View", "Poolside", "Zen Garden"],
        "cleanup": 10,
    },
]

# Sample booking times (hour of day)
BOOKING_HOURS = [9, 10, 11, 14, 15, 16, 17, 18, 19]


class Command:
    """Base command class for compatibility."""

    def __init__(self):
        from django.core.management.base import BaseCommand
        self.stdout = BaseCommand().stdout
        self.style = BaseCommand().style


from django.core.management.base import BaseCommand as DjangoBaseCommand


class Command(DjangoBaseCommand):
    help = "Seed service arrangements, time slots, and sample bookings"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing booking data before seeding",
        )
        parser.add_argument(
            "--bookings-count",
            type=int,
            default=20,
            help="Number of sample bookings to create (default: 20)",
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
            # Step 1: Create service arrangements
            self.stdout.write("🏠 Seeding service arrangements...")
            arrangements = self.create_service_arrangements()
            self.stdout.write(self.style.SUCCESS(
                f"    ✓ Created {len(arrangements)} service arrangements"
            ))

            # Step 2: Create sample bookings with time slots
            bookings_count = options.get("bookings_count", 20)
            self.stdout.write(f"📅 Seeding {bookings_count} sample bookings...")
            bookings = self.create_sample_bookings(arrangements, bookings_count)
            self.stdout.write(self.style.SUCCESS(
                f"    ✓ Created {len(bookings)} sample bookings"
            ))

            # Print summary
            self.print_summary(arrangements, bookings)

    def clear_data(self):
        """Clear existing booking data."""
        self.stdout.write(self.style.WARNING("⚠️ Clearing booking data..."))
        Booking.objects.all().delete()
        TimeSlot.objects.all().delete()
        ServiceArrangement.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("✓ Booking data cleared"))

    def create_service_arrangements(self):
        """Create service arrangements for each spa center and service."""
        all_arrangements = []
        spa_centers = SpaCenter.objects.prefetch_related("services").all()

        for spa_center in spa_centers:
            services = spa_center.services.filter(is_active=True)
            
            for service in services:
                # Create 1-3 arrangements per service
                num_arrangements = random.randint(1, 3)
                config = random.choice(ARRANGEMENT_CONFIGS)
                
                for i in range(num_arrangements):
                    room_no = f"R{random.randint(100, 999)}"
                    label = random.choice(config["labels"])
                    
                    arrangement, created = ServiceArrangement.objects.get_or_create(
                        spa_center=spa_center,
                        service=service,
                        room_no=room_no,
                        defaults={
                            "arrangement_type": config["type"],
                            "arrangement_label": f"{label} - {service.name[:20]}",
                            "cleanup_duration": config["cleanup"],
                            "is_active": True,
                        },
                    )
                    
                    if created:
                        all_arrangements.append(arrangement)

            self.stdout.write(f"    {spa_center.name}: {len(services)} services configured")

        return all_arrangements

    def create_sample_bookings(self, arrangements, count):
        """Create sample bookings with time slots."""
        if not arrangements:
            self.stdout.write(self.style.WARNING("    No arrangements available for bookings"))
            return []

        all_bookings = []
        customers = list(User.objects.filter(user_type="customer")[:10])
        
        if not customers:
            self.stdout.write(self.style.WARNING(
                "    No customers found. Run 'python manage.py seed_customers' first."
            ))
            return []

        therapists = list(TherapistProfile.objects.filter(is_available=True)[:10])
        add_ons = list(AddOnService.objects.filter(is_active=True))

        # Generate bookings for the next 30 days
        today = timezone.now().date()

        for i in range(count):
            try:
                # Random arrangement
                arrangement = random.choice(arrangements)
                service = arrangement.service
                spa_center = arrangement.spa_center
                
                # Random date in next 30 days
                booking_date = today + timedelta(days=random.randint(1, 30))
                
                # Random booking hour
                booking_hour = random.choice(BOOKING_HOURS)
                start_time = time(hour=booking_hour, minute=0)
                
                # Calculate end time
                addon_duration = 0
                selected_addons = []
                if add_ons and random.random() > 0.5:
                    selected_addons = random.sample(add_ons, min(random.randint(1, 2), len(add_ons)))
                    addon_duration = sum(a.duration_minutes for a in selected_addons)
                
                end_time = Booking.calculate_end_time(
                    start_time,
                    service.duration_minutes,
                    addon_duration,
                    arrangement.cleanup_duration
                )
                
                # Check for overlapping slots
                if TimeSlot.objects.filter(
                    arrangement=arrangement,
                    date=booking_date,
                    start_time__lt=end_time,
                    end_time__gt=start_time,
                ).exists():
                    continue  # Skip if slot is taken
                
                # Create time slot
                time_slot = TimeSlot.objects.create(
                    arrangement=arrangement,
                    date=booking_date,
                    start_time=start_time,
                    end_time=end_time,
                )
                
                # Calculate price
                total_price = service.current_price
                if selected_addons:
                    total_price += sum(a.price for a in selected_addons)
                
                # Random customer
                customer = random.choice(customers)
                
                # Random therapist (optional)
                therapist = None
                if therapists and random.random() > 0.3:
                    therapist = random.choice(therapists)
                
                # Random status
                status = random.choice([
                    Booking.BookingStatus.REQUESTED,
                    Booking.BookingStatus.CONFIRMED,
                    Booking.BookingStatus.PAYMENT_SUCCESS,
                    Booking.BookingStatus.COMPLETED,
                ])
                
                # Create booking
                booking = Booking.objects.create(
                    customer=customer,
                    spa_center=spa_center,
                    service_arrangement=arrangement,
                    time_slot=time_slot,
                    therapist=therapist,
                    total_price=total_price,
                    customer_message=random.choice([
                        "",
                        "Please prepare the room early.",
                        "I prefer unscented oils.",
                        "This is my first visit.",
                        "Please ensure low lighting.",
                    ]),
                    status=status,
                )
                
                # Add add-on services
                if selected_addons:
                    booking.add_on_services.set(selected_addons)
                
                all_bookings.append(booking)
                
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"    Skipped booking: {e}"))
                continue

        return all_bookings

    def print_summary(self, arrangements, bookings):
        """Print summary of seeded data."""
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("📊 BOOKING SEED DATA SUMMARY")
        self.stdout.write("=" * 50)
        
        self.stdout.write(f"\n  🏠 Service Arrangements: {ServiceArrangement.objects.count()}")
        
        # Breakdown by type
        for arr_type, label in ServiceArrangement.ArrangementType.choices:
            count = ServiceArrangement.objects.filter(arrangement_type=arr_type).count()
            if count > 0:
                self.stdout.write(f"      - {label}: {count}")
        
        self.stdout.write(f"\n  📅 Time Slots: {TimeSlot.objects.count()}")
        self.stdout.write(f"  📝 Bookings: {Booking.objects.count()}")
        
        # Breakdown by status
        for status, label in Booking.BookingStatus.choices:
            count = Booking.objects.filter(status=status).count()
            if count > 0:
                self.stdout.write(f"      - {label}: {count}")
        
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("🔗 TEST API ENDPOINTS")
        self.stdout.write("=" * 50)
        
        # Get a sample service ID for the example
        sample_service = Service.objects.first()
        if sample_service:
            self.stdout.write(f"\n  GET /api/v1/bookings/services/{sample_service.id}/arrangements/")
            self.stdout.write(f"  GET /api/v1/bookings/services/{sample_service.id}/availability/")
        
        self.stdout.write("  GET /api/v1/bookings/upcoming-bookings/ (requires auth)")
        self.stdout.write("  POST /api/v1/bookings/ (requires auth)")
        
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("✅ BOOKING SEED DATA CREATED SUCCESSFULLY!"))
        self.stdout.write("=" * 50 + "\n")
