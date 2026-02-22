"""
Seed profiles: CustomerProfile, EmployeeProfile, and EmployeeSchedule.

Depends on: seed_users (accounts app must be seeded first).
"""

from datetime import date, time

from django.core.management.base import BaseCommand

from accounts.models import EmployeeRole, User, UserType
from profiles.models import CustomerProfile, EmployeeProfile, EmployeeSchedule


# ── Employee profiles keyed by email ───────────────────────────────
# Each branch manager maps to a country/branch.
EMPLOYEE_PROFILES = [
    # Country managers
    {"email": "country.manager.qa@ushspa.com",  "role": EmployeeRole.COUNTRY_MANAGER, "department": "Executive", "job_title": "Country Manager – Qatar",  "hire_date": date(2022,9,1),  "work_location": "HQ Doha",    "branch": "HQ",          "region": "Qatar",  "country": "Qatar"},
    {"email": "country.manager.kw@ushspa.com",  "role": EmployeeRole.COUNTRY_MANAGER, "department": "Executive", "job_title": "Country Manager – Kuwait", "hire_date": date(2023,1,10), "work_location": "HQ Kuwait",  "branch": "HQ",          "region": "Kuwait", "country": "Kuwait"},
    {"email": "country.manager.ae@ushspa.com",  "role": EmployeeRole.COUNTRY_MANAGER, "department": "Executive", "job_title": "Country Manager – UAE",    "hire_date": date(2023,3,1),  "work_location": "HQ Dubai",   "branch": "HQ",          "region": "UAE",    "country": "UAE"},
    # Qatar branch managers
    {"email": "manager.doha@ushspa.com",         "role": EmployeeRole.BRANCH_MANAGER, "department": "Management", "job_title": "Branch Manager – Doha",      "hire_date": date(2023,1,15), "work_location": "USH Spa – Doha",       "branch": "Doha",       "region": "Qatar", "country": "Qatar"},
    {"email": "manager.lusail@ushspa.com",       "role": EmployeeRole.BRANCH_MANAGER, "department": "Management", "job_title": "Branch Manager – Lusail",    "hire_date": date(2023,6,1),  "work_location": "USH Spa – Lusail",     "branch": "Lusail",     "region": "Qatar", "country": "Qatar"},
    {"email": "manager.wakrah@ushspa.com",       "role": EmployeeRole.BRANCH_MANAGER, "department": "Management", "job_title": "Branch Manager – Al Wakrah", "hire_date": date(2023,8,1),  "work_location": "USH Spa – Al Wakrah",  "branch": "Al Wakrah",  "region": "Qatar", "country": "Qatar"},
    {"email": "manager.khor@ushspa.com",         "role": EmployeeRole.BRANCH_MANAGER, "department": "Management", "job_title": "Branch Manager – Al Khor",   "hire_date": date(2024,1,10), "work_location": "USH Spa – Al Khor",    "branch": "Al Khor",    "region": "Qatar", "country": "Qatar"},
    {"email": "manager.rayyan@ushspa.com",       "role": EmployeeRole.BRANCH_MANAGER, "department": "Management", "job_title": "Branch Manager – Al Rayyan", "hire_date": date(2024,2,15), "work_location": "USH Spa – Al Rayyan",  "branch": "Al Rayyan",  "region": "Qatar", "country": "Qatar"},
    # Kuwait branch managers
    {"email": "manager.kuwaitcity@ushspa.com",   "role": EmployeeRole.BRANCH_MANAGER, "department": "Management", "job_title": "Branch Manager – Kuwait City", "hire_date": date(2023,4,1),  "work_location": "USH Spa – Kuwait City", "branch": "Kuwait City", "region": "Kuwait", "country": "Kuwait"},
    {"email": "manager.salmiya@ushspa.com",      "role": EmployeeRole.BRANCH_MANAGER, "department": "Management", "job_title": "Branch Manager – Salmiya",     "hire_date": date(2023,7,1),  "work_location": "USH Spa – Salmiya",     "branch": "Salmiya",     "region": "Kuwait", "country": "Kuwait"},
    {"email": "manager.hawalli@ushspa.com",      "role": EmployeeRole.BRANCH_MANAGER, "department": "Management", "job_title": "Branch Manager – Hawalli",     "hire_date": date(2023,10,1), "work_location": "USH Spa – Hawalli",     "branch": "Hawalli",     "region": "Kuwait", "country": "Kuwait"},
    {"email": "manager.jabriya@ushspa.com",      "role": EmployeeRole.BRANCH_MANAGER, "department": "Management", "job_title": "Branch Manager – Jabriya",     "hire_date": date(2024,1,1),  "work_location": "USH Spa – Jabriya",     "branch": "Jabriya",     "region": "Kuwait", "country": "Kuwait"},
    {"email": "manager.farwaniya@ushspa.com",    "role": EmployeeRole.BRANCH_MANAGER, "department": "Management", "job_title": "Branch Manager – Farwaniya",   "hire_date": date(2024,3,1),  "work_location": "USH Spa – Farwaniya",   "branch": "Farwaniya",   "region": "Kuwait", "country": "Kuwait"},
    # UAE branch managers
    {"email": "manager.dubai@ushspa.com",        "role": EmployeeRole.BRANCH_MANAGER, "department": "Management", "job_title": "Branch Manager – Dubai",       "hire_date": date(2023,5,1),  "work_location": "USH Spa – Dubai",       "branch": "Dubai",       "region": "UAE", "country": "UAE"},
    {"email": "manager.abudhabi@ushspa.com",     "role": EmployeeRole.BRANCH_MANAGER, "department": "Management", "job_title": "Branch Manager – Abu Dhabi",   "hire_date": date(2023,9,1),  "work_location": "USH Spa – Abu Dhabi",   "branch": "Abu Dhabi",   "region": "UAE", "country": "UAE"},
    {"email": "manager.sharjah@ushspa.com",      "role": EmployeeRole.BRANCH_MANAGER, "department": "Management", "job_title": "Branch Manager – Sharjah",     "hire_date": date(2023,11,1), "work_location": "USH Spa – Sharjah",     "branch": "Sharjah",     "region": "UAE", "country": "UAE"},
    {"email": "manager.ajman@ushspa.com",        "role": EmployeeRole.BRANCH_MANAGER, "department": "Management", "job_title": "Branch Manager – Ajman",       "hire_date": date(2024,2,1),  "work_location": "USH Spa – Ajman",       "branch": "Ajman",       "region": "UAE", "country": "UAE"},
    {"email": "manager.rak@ushspa.com",          "role": EmployeeRole.BRANCH_MANAGER, "department": "Management", "job_title": "Branch Manager – RAK",         "hire_date": date(2024,4,1),  "work_location": "USH Spa – Ras Al Khaimah","branch": "Ras Al Khaimah","region": "UAE", "country": "UAE"},
]

CUSTOMER_PROFILES = [
    {"email": "customer.ahmed@example.com",  "bio": "Regular spa visitor.", "address_line_1": "Building 45, Zone 61", "city": "Doha",  "state": "Ad Dawhah", "country": "Qatar", "postal_code": "00000", "preferred_language": "ar"},
    {"email": "customer.layla@example.com",  "bio": "Loves skincare.",      "address_line_1": "Villa 12, Al Waab St", "city": "Doha",  "state": "Ad Dawhah", "country": "Qatar", "postal_code": "00000", "preferred_language": "en"},
    {"email": "customer.omar@example.com",   "bio": "Fitness enthusiast.",  "address_line_1": "Tower 8, Lusail Blvd", "city": "Lusail","state": "Ad Dawhah", "country": "Qatar", "postal_code": "00000", "preferred_language": "en"},
    {"email": "customer.dana@example.com",   "bio": "Wellness advocate.",   "address_line_1": "Apt 302, Pearl Tower", "city": "Doha",  "state": "Ad Dawhah", "country": "Qatar", "postal_code": "00000", "preferred_language": "ar"},
    {"email": "customer.khalid@example.com", "bio": "Corporate client.",    "address_line_1": "Office 505, Tornado",  "city": "Doha",  "state": "Ad Dawhah", "country": "Qatar", "postal_code": "00000", "preferred_language": "en"},
]

SCHEDULE = [
    (0, time(9,0), time(18,0), True),   # Monday
    (1, time(9,0), time(18,0), True),
    (2, time(9,0), time(18,0), True),
    (3, time(9,0), time(18,0), True),
    (4, time(9,0), time(14,0), False),  # Friday off
    (5, time(10,0), time(19,0), True),
    (6, time(10,0), time(19,0), True),
]

COUNTRY_MAP = {"Qatar": "qa", "Kuwait": "kw", "UAE": "ae"}


class Command(BaseCommand):
    help = "Seed profiles (employee profiles, customer profiles, schedules)"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Clear existing profiles before seeding")

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing profiles...")
            EmployeeSchedule.objects.all().delete()
            EmployeeProfile.objects.all().delete()
            CustomerProfile.objects.all().delete()

        self._seed_employee_profiles()
        self._seed_customer_profiles()
        self._seed_schedules()
        self.stdout.write(self.style.SUCCESS("\n✅ Profiles seeding complete!"))

    def _seed_employee_profiles(self):
        self.stdout.write("\nSeeding employee profiles...")
        cm_profiles = {}  # country -> EmployeeProfile

        for data in EMPLOYEE_PROFILES:
            email = data["email"]
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  Skip (user not found): {email}"))
                continue

            profile, created = EmployeeProfile.objects.update_or_create(
                user=user,
                defaults={k: v for k, v in data.items() if k != "email"},
            )
            if data["role"] == EmployeeRole.COUNTRY_MANAGER:
                cm_profiles[data["country"]] = profile
            self.stdout.write(f"  {'Created' if created else 'Updated'}: {profile}")

        # Set branch managers → country manager reporting
        for data in EMPLOYEE_PROFILES:
            if data["role"] == EmployeeRole.BRANCH_MANAGER:
                cm = cm_profiles.get(data["country"])
                if cm:
                    EmployeeProfile.objects.filter(user__email=data["email"]).update(manager=cm)

    def _seed_customer_profiles(self):
        self.stdout.write("\nSeeding customer profiles...")
        for data in CUSTOMER_PROFILES:
            email = data.pop("email")
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  Skip: {email}"))
                data["email"] = email
                continue
            obj, created = CustomerProfile.objects.update_or_create(user=user, defaults=data)
            self.stdout.write(f"  {'Created' if created else 'Updated'}: {obj}")
            data["email"] = email

    def _seed_schedules(self):
        self.stdout.write("\nSeeding schedules for branch managers...")
        managers = EmployeeProfile.objects.filter(role=EmployeeRole.BRANCH_MANAGER)
        for mgr in managers:
            for day, start, end, working in SCHEDULE:
                EmployeeSchedule.objects.update_or_create(
                    employee=mgr, day_of_week=day,
                    defaults={"start_time": start, "end_time": end, "is_working": working},
                )
            self.stdout.write(f"  Set schedule: {mgr.user.get_full_name()}")
