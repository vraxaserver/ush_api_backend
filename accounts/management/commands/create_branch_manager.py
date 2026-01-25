"""
Management command to create a branch manager user.

Usage:
    python manage.py create_branch_manager --email=manager@example.com --password=managerpass123

With optional spa center assignment:
    python manage.py create_branch_manager --email=manager@example.com --password=managerpass123 --spa-center-slug=branch-1
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import EmployeeRole, UserType
from profiles.models import EmployeeProfile
from spacenter.models import SpaCenter

User = get_user_model()


class Command(BaseCommand):
    """Create a branch manager user."""

    help = "Create a branch manager user with the specified credentials"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--email",
            type=str,
            required=True,
            help="Email address for the branch manager",
        )
        parser.add_argument(
            "--password",
            type=str,
            required=True,
            help="Password for the branch manager",
        )
        parser.add_argument(
            "--first-name",
            type=str,
            default="Branch",
            help="First name (default: Branch)",
        )
        parser.add_argument(
            "--last-name",
            type=str,
            default="Manager",
            help="Last name (default: Manager)",
        )
        parser.add_argument(
            "--spa-center-slug",
            type=str,
            required=False,
            help="Slug of the spa center to assign (optional)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        """Execute the command."""
        email = options["email"]
        password = options["password"]
        first_name = options["first_name"]
        last_name = options["last_name"]
        spa_center_slug = options.get("spa_center_slug")

        # Check if user already exists
        if User.objects.filter(email=email).exists():
            raise CommandError(f"User with email {email} already exists")

        # Validate spa center if provided
        spa_center = None
        if spa_center_slug:
            try:
                spa_center = SpaCenter.objects.get(slug=spa_center_slug)
            except SpaCenter.DoesNotExist:
                raise CommandError(
                    f"Spa center with slug '{spa_center_slug}' does not exist"
                )
            
            # Check if spa center already has a manager
            if spa_center.branch_manager is not None:
                raise CommandError(
                    f"Spa center '{spa_center.name}' already has a branch manager assigned"
                )

        # Create branch manager user
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            user_type=UserType.EMPLOYEE,
        )

        # Create employee profile with branch manager role
        employee_profile = EmployeeProfile.objects.create(
            user=user,
            role=EmployeeRole.BRANCH_MANAGER,
        )

        # Assign to spa center if provided
        if spa_center:
            spa_center.branch_manager = user
            spa_center.save(update_fields=["branch_manager"])

        # Output success message
        success_message = (
            f"Branch manager created successfully:\n"
            f"  Email: {email}\n"
            f"  Name: {first_name} {last_name}\n"
            f"  User ID: {user.id}\n"
            f"  Employee ID: {employee_profile.employee_id}"
        )

        if spa_center:
            success_message += f"\n  Assigned to: {spa_center.name}"

        self.stdout.write(self.style.SUCCESS(success_message))
