"""
Management command to create an admin user.

Usage:
    python manage.py create_admin --email=admin@example.com --password=adminpass123
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

User = get_user_model()


class Command(BaseCommand):
    """Create an admin user."""

    help = "Create an admin user with the specified credentials"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--email",
            type=str,
            required=True,
            help="Email address for the admin user",
        )
        parser.add_argument(
            "--password",
            type=str,
            required=True,
            help="Password for the admin user",
        )
        parser.add_argument(
            "--first-name",
            type=str,
            default="Admin",
            help="First name (default: Admin)",
        )
        parser.add_argument(
            "--last-name",
            type=str,
            default="User",
            help="Last name (default: User)",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        email = options["email"]
        password = options["password"]
        first_name = options["first_name"]
        last_name = options["last_name"]

        # Check if user already exists
        if User.objects.filter(email=email).exists():
            raise CommandError(f"User with email {email} already exists")

        # Create admin user
        user = User.objects.create_superuser(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Admin user created successfully:\n"
                f"  Email: {email}\n"
                f"  Name: {first_name} {last_name}\n"
                f"  ID: {user.id}"
            )
        )
