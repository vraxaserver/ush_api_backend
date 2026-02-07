
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model

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
    AddOnService,
    SpaProduct,
    ProductCategory,
)
from bookings.models import Booking, TimeSlot, ProductOrder, OrderItem
from promotions.models import (
    Voucher,
    VoucherUsage,
    GiftCard,
    GiftCardTransaction,
    GiftCardTemplate,
)

User = get_user_model()

class Command(BaseCommand):
    help = "Clean all data from the database safely"

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("⚠️ STARTING GLOBAL DATA CLEANUP..."))
        
        with transaction.atomic():
            # 1. Booking & Orders (Leaf nodes)
            self.clean_model(OrderItem, "Order Items")
            self.clean_model(ProductOrder, "Product Orders")
            
            # Delete bookings (which cascade to TimeSlots usually, but let's be explicit)
            self.clean_model(Booking, "Bookings")
            self.clean_model(TimeSlot, "Time Slots")
            
            # 2. Arrangements
            self.clean_model(ServiceArrangement, "Service Arrangements")
            
            # 3. Promotions
            self.clean_model(VoucherUsage, "Voucher Usages")
            self.clean_model(GiftCardTransaction, "Gift Card Transactions")
            self.clean_model(GiftCard, "Gift Cards")
            self.clean_model(GiftCardTemplate, "Gift Card Templates")
            self.clean_model(Voucher, "Vouchers")
            
            # 4. Products
            self.clean_model(SpaProduct, "Spa Products")
            self.clean_model(ProductCategory, "Product Categories")
            
            # 5. Staff & Profiles
            self.clean_model(TherapistProfile, "Therapist Profiles")
            # Branch managers are users, handled later
            
            # 6. Spa Centers & Operating Hours
            self.clean_model(SpaCenterOperatingHours, "Operating Hours")
            self.clean_model(SpaCenter, "Spa Centers")
            
            # 7. Services & Add-ons
            self.clean_model(AddOnService, "Add-on Services")
            self.clean_model(ServiceImage, "Service Images")
            self.clean_model(Service, "Services")
            self.clean_model(Specialty, "Specialties")
            
            # 8. Locations
            self.clean_model(City, "Cities")
            self.clean_model(Country, "Countries")
            
            # 9. Users (Optional, keep superusers)
            self.clean_users()

        self.stdout.write(self.style.SUCCESS("✅ ALL DATA CLEANED SUCCESSFULLY!"))

    def clean_model(self, model_class, name):
        """Helper to count and delete instances of a model."""
        try:
            count = model_class.objects.count()
            if count > 0:
                self.stdout.write(f"  🗑️ Deleting {count} {name}...")
                model_class.objects.all().delete()
                self.stdout.write(f"    ✓ Deleted {name}")
            else:
                self.stdout.write(f"    - No {name} to delete")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"    ❌ Error deleting {name}: {e}"))
            # Don't raise, try to continue or let transaction rollback if critical
            # Re-raise to trigger rollback
            raise e

    def clean_users(self):
        """Delete non-superuser accounts."""
        self.stdout.write("  🗑️ Cleaning Users...")
        # Keep superusers
        users_to_delete = User.objects.filter(is_superuser=False)
        count = users_to_delete.count()
        if count > 0:
            users_to_delete.delete()
            self.stdout.write(f"    ✓ Deleted {count} users")
        else:
            self.stdout.write("    - No users to delete")
