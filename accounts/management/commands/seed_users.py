"""
Seed users: 1 admin, 15 branch managers, 3 country managers, 5 customers.

Generates enough employees for 15 branches across 3 countries.
"""

from django.core.management.base import BaseCommand

from accounts.models import User, UserType


# Admin
ADMIN_USERS = [
    {"email": "admin@ushspa.com", "first_name": "Super", "last_name": "Admin", "password": "Admin@12345", "is_staff": True, "is_superuser": True},
]

# Country managers (1 per country)
COUNTRY_MANAGERS = [
    {"email": "country.manager.qa@ushspa.com",  "first_name": "Abdullah",  "last_name": "Al Thani",  "password": "Manager@12345"},
    {"email": "country.manager.kw@ushspa.com",  "first_name": "Fahad",     "last_name": "Al Sabah",  "password": "Manager@12345"},
    {"email": "country.manager.ae@ushspa.com",  "first_name": "Sultan",    "last_name": "Al Maktoum","password": "Manager@12345"},
]

# Branch managers (5 per country = 15)
BRANCH_MANAGERS = [
    # Qatar
    {"email": "manager.doha@ushspa.com",       "first_name": "Hamad",    "last_name": "Al Marri",    "password": "Manager@12345"},
    {"email": "manager.lusail@ushspa.com",     "first_name": "Nasser",   "last_name": "Al Hajri",    "password": "Manager@12345"},
    {"email": "manager.wakrah@ushspa.com",     "first_name": "Saeed",    "last_name": "Al Kuwari",   "password": "Manager@12345"},
    {"email": "manager.khor@ushspa.com",       "first_name": "Yousef",   "last_name": "Al Mohannadi","password": "Manager@12345"},
    {"email": "manager.rayyan@ushspa.com",     "first_name": "Jassim",   "last_name": "Al Sulaiti",  "password": "Manager@12345"},
    # Kuwait
    {"email": "manager.kuwaitcity@ushspa.com", "first_name": "Bader",    "last_name": "Al Rashidi",  "password": "Manager@12345"},
    {"email": "manager.salmiya@ushspa.com",    "first_name": "Mohammad", "last_name": "Al Ajmi",     "password": "Manager@12345"},
    {"email": "manager.hawalli@ushspa.com",    "first_name": "Faisal",   "last_name": "Al Enezi",    "password": "Manager@12345"},
    {"email": "manager.jabriya@ushspa.com",    "first_name": "Ali",      "last_name": "Al Shammari", "password": "Manager@12345"},
    {"email": "manager.farwaniya@ushspa.com",  "first_name": "Turki",    "last_name": "Al Mutairi",  "password": "Manager@12345"},
    # UAE
    {"email": "manager.dubai@ushspa.com",      "first_name": "Omar",     "last_name": "Al Mansoori", "password": "Manager@12345"},
    {"email": "manager.abudhabi@ushspa.com",   "first_name": "Khaled",   "last_name": "Al Nuaimi",   "password": "Manager@12345"},
    {"email": "manager.sharjah@ushspa.com",    "first_name": "Rashed",   "last_name": "Al Shamsi",   "password": "Manager@12345"},
    {"email": "manager.ajman@ushspa.com",      "first_name": "Tareq",    "last_name": "Al Zaabi",    "password": "Manager@12345"},
    {"email": "manager.rak@ushspa.com",        "first_name": "Majid",    "last_name": "Al Khateri",  "password": "Manager@12345"},
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
    help = "Seed users (admin, branch managers, country managers, customers)"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Clear existing users before seeding")

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing non-superuser accounts...")
            User.objects.filter(is_superuser=False).delete()

        self._create_users(ADMIN_USERS, UserType.ADMIN, "Admin")
        self._create_users(COUNTRY_MANAGERS, UserType.EMPLOYEE, "Country Manager")
        self._create_users(BRANCH_MANAGERS, UserType.EMPLOYEE, "Branch Manager")
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
