"""
Signals for Auth Microservice.

Handles automatic profile creation and related tasks.
"""

import logging
import random
import string

from django.conf import settings
from django.contrib.auth.models import Group
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta

from .models import User, UserType, VerificationCode

logger = logging.getLogger(__name__)


def generate_verification_code(length=6):
    """Generate a random numeric verification code."""
    return "".join(random.choices(string.digits, k=length))


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Create appropriate profile when user is created.

    - Customer users get CustomerProfile
    - Employee users get EmployeeProfile
    """
    if not created:
        return

    # Import here to avoid circular imports
    from profiles.models import CustomerProfile, EmployeeProfile

    try:
        if instance.user_type == UserType.CUSTOMER:
            CustomerProfile.objects.get_or_create(user=instance)
            logger.info(f"Created customer profile for {instance}")

        elif instance.user_type == UserType.EMPLOYEE:
            # Get role if set during creation
            role = getattr(instance, "_employee_role", None)
            EmployeeProfile.objects.get_or_create(
                user=instance,
                defaults={"role": role or "therapist"},
            )
            logger.info(f"Created employee profile for {instance}")

            # Add to appropriate group
            if role:
                assign_employee_group(instance, role)

    except Exception as e:
        logger.error(f"Error creating profile for {instance}: {e}")


@receiver(post_save, sender=User)
def send_verification_on_registration(sender, instance, created, **kwargs):
    """
    Send verification code email/SMS to new users.
    
    Creates a verification code and sends it to the user's email or phone.
    """
    if not created:
        return

    # Only send verification for customers who registered themselves
    if instance.user_type != UserType.CUSTOMER:
        return

    try:
        from .tasks import send_email_verification, send_sms_verification

        # Get verification code settings
        code_length = getattr(settings, "VERIFICATION_CODE_LENGTH", 6)
        expiry_minutes = getattr(settings, "VERIFICATION_CODE_EXPIRY_MINUTES", 10)

        # Send email verification if email is provided
        if instance.email and not instance.is_email_verified:
            # Generate verification code
            code = generate_verification_code(code_length)
            
            # Create verification code record
            VerificationCode.objects.create(
                user=instance,
                code=code,
                verification_type=VerificationCode.VerificationType.EMAIL,
                expires_at=timezone.now() + timedelta(minutes=expiry_minutes),
            )
            
            # Send verification email asynchronously
            send_email_verification.delay(instance.email, code)
            logger.info(f"Verification code created and email queued for {instance.email}")

        # Send SMS verification if phone is provided (and no email)
        elif instance.phone_number and not instance.is_phone_verified:
            # Generate verification code
            code = generate_verification_code(code_length)
            
            # Create verification code record
            VerificationCode.objects.create(
                user=instance,
                code=code,
                verification_type=VerificationCode.VerificationType.PHONE,
                expires_at=timezone.now() + timedelta(minutes=expiry_minutes),
            )
            
            # Send verification SMS asynchronously
            send_sms_verification.delay(str(instance.phone_number), code)
            logger.info(f"Verification code created and SMS queued for {instance.phone_number}")

    except Exception as e:
        logger.error(f"Error sending verification for {instance}: {e}")


def assign_employee_group(user, role):
    """
    Assign employee to appropriate Django group based on role.

    Args:
        user: User instance
        role: Employee role (branch_manager, country_manager, therapist)
    """
    role_group_mapping = {
        "branch_manager": "Branch Managers",
        "country_manager": "Country Managers",
        "therapist": "Therapists",
    }

    group_name = role_group_mapping.get(role)
    if group_name:
        group, _ = Group.objects.get_or_create(name=group_name)
        user.groups.add(group)
        logger.info(f"Added {user} to group {group_name}")


def setup_employee_groups():
    """
    Create default employee groups with permissions.

    Call this during initial setup or via management command.
    """
    from django.contrib.auth.models import Group, Permission
    from django.contrib.contenttypes.models import ContentType

    groups_permissions = {
        "Branch Managers": [
            # Add specific permissions for branch managers
        ],
        "Country Managers": [
            # Add specific permissions for country managers
        ],
        "Therapists": [
            # Add specific permissions for therapists
        ],
    }

    for group_name, permissions in groups_permissions.items():
        group, created = Group.objects.get_or_create(name=group_name)
        if created:
            logger.info(f"Created group: {group_name}")

        # Add permissions to group
        for perm_codename in permissions:
            try:
                perm = Permission.objects.get(codename=perm_codename)
                group.permissions.add(perm)
            except Permission.DoesNotExist:
                logger.warning(f"Permission not found: {perm_codename}")
