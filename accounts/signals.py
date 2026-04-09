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
    from profiles.models import CustomerProfile

    try:
        if instance.user_type == UserType.CUSTOMER:
            CustomerProfile.objects.get_or_create(user=instance)
            logger.info(f"Created customer profile for {instance}")

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
            
            # Dispatch verification email (SES) / OTP via SQS
            send_email_verification(instance.email, code)
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
            
            # Dispatch OTP SMS to SQS (ush_otp_sms_queue)
            send_sms_verification(str(instance.phone_number), code)
            logger.info(f"Verification code created and SMS queued for {instance.phone_number}")

    except Exception as e:
        logger.error(f"Error sending verification for {instance}: {e}")


