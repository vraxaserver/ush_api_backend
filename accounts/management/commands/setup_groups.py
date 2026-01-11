"""
Management command to setup initial groups and permissions.

Usage:
    python manage.py setup_groups
"""

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Setup employee groups and permissions."""

    help = "Setup initial employee groups and permissions"

    def handle(self, *args, **options):
        """Execute the command."""
        self.stdout.write("Setting up employee groups...")

        # Define groups and their permissions
        groups_config = {
            "Branch Managers": {
                "description": "Managers of individual branches",
                "permissions": [
                    # Customer permissions
                    "view_customerprofile",
                    # Employee permissions (view subordinates)
                    "view_employeeprofile",
                    "view_employeeschedule",
                    "change_employeeschedule",
                    # User permissions
                    "view_user",
                ],
            },
            "Country Managers": {
                "description": "Managers overseeing all branches in a country",
                "permissions": [
                    # Customer permissions
                    "view_customerprofile",
                    # Employee permissions
                    "view_employeeprofile",
                    "change_employeeprofile",
                    "view_employeeschedule",
                    "add_employeeschedule",
                    "change_employeeschedule",
                    "delete_employeeschedule",
                    # User permissions
                    "view_user",
                ],
            },
            "Therapists": {
                "description": "Service providers",
                "permissions": [
                    # Own schedule
                    "view_employeeschedule",
                    "change_employeeschedule",
                    # Customer profiles (limited)
                    "view_customerprofile",
                ],
            },
        }

        for group_name, config in groups_config.items():
            group, created = Group.objects.get_or_create(name=group_name)

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"Created group: {group_name}")
                )
            else:
                self.stdout.write(f"Group already exists: {group_name}")

            # Clear existing permissions and add new ones
            group.permissions.clear()

            for perm_codename in config["permissions"]:
                try:
                    perm = Permission.objects.get(codename=perm_codename)
                    group.permissions.add(perm)
                    self.stdout.write(f"  Added permission: {perm_codename}")
                except Permission.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  Permission not found: {perm_codename}"
                        )
                    )

        self.stdout.write(self.style.SUCCESS("Employee groups setup complete!"))
