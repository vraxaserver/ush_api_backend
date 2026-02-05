"""
Management command to setup initial groups and permissions.

Usage:
    python manage.py setup_groups
"""

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Setup employee groups and permissions."""

    help = "Setup initial employee groups and permissions"

    def handle(self, *args, **options):
        """Execute the command."""
        self.stdout.write("Setting up user groups...")

        # Define groups and their permissions
        groups_config = {
            "Admin": {
                "description": "Full access to all apps except superuser privileges",
                "permissions": self._get_admin_permissions(),
            },
            "Manager": {
                "description": "Scoped access to assigned spa center data",
                "permissions": self._get_manager_permissions(),
            },
            "Branch Managers": {
                "description": "Managers of individual branches (legacy)",
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
                    # Use filter().first() to handle duplicate permission codenames
                    perm = Permission.objects.filter(codename=perm_codename).first()
                    if perm:
                        group.permissions.add(perm)
                        self.stdout.write(f"  Added permission: {perm_codename}")
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  Permission not found: {perm_codename}"
                            )
                        )
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  Error adding permission {perm_codename}: {e}"
                        )
                    )

        self.stdout.write(self.style.SUCCESS("User groups setup complete!"))
        
        # Sync existing users to groups
        self.stdout.write("Syncing existing users to groups...")
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Admin users
        admin_group = Group.objects.get(name="Admin")
        admin_users = User.objects.filter(user_type="admin")
        for user in admin_users:
            if admin_group not in user.groups.all():
                user.groups.add(admin_group)
                self.stdout.write(f"  Added {user.email} to Admin group")
                
        # Manager users (Branch Managers)
        manager_group = Group.objects.get(name="Manager")
        # Find employees with managed_spa_center
        # Note: We need to check the reverse relationship 'managed_spa_center'
        # Since it's a OneToOneField from SpaCenter to User
        from spacenter.models import SpaCenter
        branch_managers = User.objects.filter(
            user_type="employee", 
            managed_spa_center__isnull=False
        )
        for user in branch_managers:
            if manager_group not in user.groups.all():
                user.groups.add(manager_group)
                self.stdout.write(f"  Added {user.email} to Manager group")
                
        self.stdout.write(self.style.SUCCESS("User sync complete!"))

    def _get_admin_permissions(self):
        """Get all permissions for Admin group (full access)."""
        permissions = []
        
        # Apps that Admin should have full access to
        admin_apps = [
            'accounts',
            'profiles', 
            'spacenter',
            'bookings',
            'promotions',
            'payments',
        ]
        
        # Get all permissions for these apps
        for app_label in admin_apps:
            try:
                content_types = ContentType.objects.filter(app_label=app_label)
                for ct in content_types:
                    perms = Permission.objects.filter(content_type=ct)
                    for perm in perms:
                        permissions.append(perm.codename)
            except Exception:
                pass
        
        # Add specific model permissions if dynamic lookup fails
        static_admin_permissions = [
            # Accounts app
            "view_user", "add_user", "change_user", "delete_user",
            "view_verificationcode", "add_verificationcode", "change_verificationcode", "delete_verificationcode",
            "view_socialauthprovider",
            
            # Profiles app
            "view_customerprofile", "add_customerprofile", "change_customerprofile", "delete_customerprofile",
            "view_employeeprofile", "add_employeeprofile", "change_employeeprofile", "delete_employeeprofile",
            "view_employeeschedule", "add_employeeschedule", "change_employeeschedule", "delete_employeeschedule",
            "view_slide", "add_slide", "change_slide", "delete_slide",
            
            # Spacenter app
            "view_country", "add_country", "change_country", "delete_country",
            "view_city", "add_city", "change_city", "delete_city",
            "view_specialty", "add_specialty", "change_specialty", "delete_specialty",
            "view_service", "change_service",
            "view_serviceimage", "add_serviceimage", "change_serviceimage", "delete_serviceimage",
            "view_addonservice", "add_addonservice", "change_addonservice", "delete_addonservice",
            "view_spacenter", "add_spacenter", "change_spacenter", "delete_spacenter",
            "view_spacenteroperatinghours", "add_spacenteroperatinghours", "change_spacenteroperatinghours", "delete_spacenteroperatinghours",
            "view_therapistprofile", "add_therapistprofile", "change_therapistprofile", "delete_therapistprofile",
            "view_productcategory", "add_productcategory", "change_productcategory", "delete_productcategory",
            "view_baseproduct", "add_baseproduct", "change_baseproduct", "delete_baseproduct",
            "view_spaproduct", "add_spaproduct", "change_spaproduct", "delete_spaproduct",
            
            # Bookings app
            "view_booking", "add_booking", "change_booking", "delete_booking",
            "view_servicearrangement", "add_servicearrangement", "change_servicearrangement", "delete_servicearrangement",
            "view_timeslot", "add_timeslot", "change_timeslot", "delete_timeslot",
            
            # Promotions app
            "view_voucher", "add_voucher", "change_voucher", "delete_voucher",
            "view_voucherusage", "add_voucherusage", "change_voucherusage", "delete_voucherusage",
            "view_giftcardtemplate", "add_giftcardtemplate", "change_giftcardtemplate", "delete_giftcardtemplate",
            "view_giftcard", "add_giftcard", "change_giftcard", "delete_giftcard",
            "view_giftcardtransaction", "add_giftcardtransaction", "change_giftcardtransaction", "delete_giftcardtransaction",
            
            # Payments app
            "view_stripecustomer", "add_stripecustomer", "change_stripecustomer", "delete_stripecustomer",
            "view_payment", "add_payment", "change_payment", "delete_payment",
        ]
        
        # Merge and dedupe
        return list(set(permissions + static_admin_permissions))

    def _get_manager_permissions(self):
        """Get permissions for Manager group (scoped to spa center)."""
        return [
            # Spacenter - view and manage their spa center's data
            "view_spacenter", "change_spacenter",
            "view_spacenteroperatinghours", "add_spacenteroperatinghours", "change_spacenteroperatinghours", "delete_spacenteroperatinghours",
            "view_service",  # Read-only access to services
            
            # Removed serviceimage permissions
            "view_addonservice",
            "view_therapistprofile", "add_therapistprofile", "change_therapistprofile",
            "view_spaproduct", "change_spaproduct",  # Removed add_spaproduct
            # Removed productcategory and baseproduct permissions
            
            # Bookings - manage bookings for their spa center
            "view_booking", "add_booking", "change_booking",
            "view_servicearrangement", "add_servicearrangement", "change_servicearrangement",
            "view_timeslot",
            
            # Profiles - view employees at their spa center
            "view_employeeprofile", "change_employeeprofile",
            "view_employeeschedule", "add_employeeschedule", "change_employeeschedule", "delete_employeeschedule",
            "view_customerprofile",
            
            # Payments - view payments for their spa center
            "view_payment",
            
            # Promotions - view vouchers and gift cards
            "view_voucher", "view_voucherusage",
            "view_giftcard", "view_giftcardtransaction",
            "view_giftcardtemplate",
        ]
