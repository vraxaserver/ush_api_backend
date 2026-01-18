
from django.contrib.auth import get_user_model
from spacenter.management.commands.seed_base import BaseSeedCommand

User = get_user_model()


class Command(BaseSeedCommand):
    help = "Seed customer users"

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Seeding Customers..."))

        customers = [
            {
                "email": "customer.1@demo.spa.com",
                "first_name": "Sarah",
                "last_name": "Johnson",
                "phone_number": "+971500000001",
                "is_email_verified": True,
                "is_phone_verified": True,
            },
            {
                "email": "customer.2@demo.spa.com",
                "first_name": "Mohammed",
                "last_name": "Ali",
                "phone_number": "+971500000002",
                "is_email_verified": True,
                "is_phone_verified": False,
            },
            {
                "email": "vip.customer@demo.spa.com",
                "first_name": "Jessica",
                "last_name": "Parker",
                "phone_number": "+971500000003",
                "is_email_verified": True,
                "is_phone_verified": True,
            },
        ]

        created_count = 0
        for data in customers:
            email = data["email"]
            if not User.objects.filter(email=email).exists():
                User.objects.create_user(
                    email=email,
                    password="Demo@123",
                    first_name=data["first_name"],
                    last_name=data["last_name"],
                    phone_number=data["phone_number"],
                    user_type="customer",
                    is_email_verified=data["is_email_verified"],
                    is_phone_verified=data["is_phone_verified"],
                )
                self.stdout.write(f"  Created customer: {email}")
                created_count += 1
            else:
                self.stdout.write(f"  Customer already exists: {email}")

        self.stdout.write(
            self.style.SUCCESS(f"Successfully seeded {created_count} customers")
        )
