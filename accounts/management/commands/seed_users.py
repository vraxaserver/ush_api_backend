"""
Seed users: 1 admin, 5 customers.
"""

from django.core.management.base import BaseCommand

from accounts.models import User, UserType


# Admin
ADMIN_USERS = [
    {"email": "admin@ushspa.com", "first_name": "Super", "last_name": "Admin", "password": "Admin@12345", "is_staff": True, "is_superuser": True},
]


# Customers
CUSTOMERS = [
    {"email": "customer.ahmed@example.com",  "first_name": "Ahmed",  "last_name": "Hassan",   "password": "Customer@12345", "phone_number": "+97455001001"},
    {"email": "customer.layla@example.com",  "first_name": "Layla",  "last_name": "Khalil",   "password": "Customer@12345", "phone_number": "+97455001002"},
    {"email": "customer.omar@example.com",   "first_name": "Omar",   "last_name": "Mansoor",  "password": "Customer@12345", "phone_number": "+97455001003"},
    {"email": "customer.dana@example.com",   "first_name": "Dana",   "last_name": "Al Farsi", "password": "Customer@12345", "phone_number": "+97455001004"},
    {"email": "customer.khalid@example.com", "first_name": "Khalid", "last_name": "Nasser",   "password": "Customer@12345", "phone_number": "+97455001005"},
]


class Command(BaseCommand):
    help = "Seed users (admin, customers)"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Clear existing users before seeding")

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing non-superuser accounts...")
            User.objects.filter(is_superuser=False).delete()

        self._create_users(ADMIN_USERS, UserType.ADMIN, "Admin")
        self._create_users(CUSTOMERS, UserType.CUSTOMER, "Customer")

        self.stdout.write(self.style.SUCCESS("\n✅ Users seeding complete!"))

    def _create_users(self, users_data, user_type, label):
        self.stdout.write(f"\nSeeding {label}s...")
        for data in users_data:
            email = data["email"]
            password = data.pop("password")
            is_staff = data.pop("is_staff", user_type != UserType.CUSTOMER)
            is_superuser = data.pop("is_superuser", False)

            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    **data,
                    "user_type": user_type,
                    "is_staff": is_staff,
                    "is_superuser": is_superuser,
                    "is_email_verified": True,
                    "is_active": True,
                },
            )
            if created:
                user.set_password(password)
                user.save(update_fields=["password"])
                self.stdout.write(self.style.SUCCESS(f"  Created: {user.get_full_name()} ({email})"))
            else:
                self.stdout.write(f"  Exists: {user.get_full_name()} ({email})")

            data["password"] = password  # restore
            if "is_staff" not in data and user_type != UserType.CUSTOMER:
                pass  # already handled
