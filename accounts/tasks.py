"""
Celery Tasks for Auth Microservice.

Handles async email and SMS sending for verification.
"""

import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_email_verification(self, email, code, is_password_reset=False):
    """
    Send verification code via email.

    Args:
        email: Recipient email address
        code: Verification code
        is_password_reset: Whether this is for password reset

    Returns:
        bool: True if email sent successfully
    """
    try:
        if is_password_reset:
            subject = "Password Reset Code"
            template = "emails/password_reset.html"
        else:
            subject = "Email Verification Code"
            template = "emails/email_verification.html"

        # Render email template
        context = {
            "code": code,
            "expiry_minutes": getattr(settings, "VERIFICATION_CODE_EXPIRY_MINUTES", 10),
        }

        try:
            html_message = render_to_string(template, context)
        except Exception:
            # Fallback to plain text if template not found
            html_message = f"""
            <h2>{subject}</h2>
            <p>Your verification code is: <strong>{code}</strong></p>
            <p>This code will expire in {context['expiry_minutes']} minutes.</p>
            <p>If you didn't request this, please ignore this email.</p>
            """

        plain_message = f"Your verification code is: {code}. This code will expire in {context['expiry_minutes']} minutes."

        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(f"Verification email sent to {email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {email}: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_sms_verification(self, phone_number, code):
    """
    Send verification code via SMS using AWS SNS.

    Args:
        phone_number: Recipient phone number (E.164 format, e.g., +1234567890)
        code: Verification code

    Returns:
        bool: True if SMS sent successfully
    """
    try:
        import boto3
        from botocore.exceptions import ClientError

        # Check if AWS is configured
        aws_access_key = getattr(settings, "AWS_ACCESS_KEY_ID", "")
        aws_secret_key = getattr(settings, "AWS_SECRET_ACCESS_KEY", "")
        aws_region = getattr(settings, "AWS_SNS_REGION_NAME", "us-east-1")

        if not all([aws_access_key, aws_secret_key]):
            logger.warning("AWS SNS not configured. SMS not sent.")
            # In development, just log the code
            logger.info(f"SMS Verification Code for {phone_number}: {code}")
            return True

        # Create SNS client
        sns_client = boto3.client(
            "sns",
            region_name=aws_region,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
        )

        # Send SMS
        expiry_minutes = getattr(settings, "VERIFICATION_CODE_EXPIRY_MINUTES", 10)
        message = f"Your verification code is: {code}. It expires in {expiry_minutes} minutes."

        response = sns_client.publish(
            PhoneNumber=phone_number,
            Message=message,
            MessageAttributes={
                "AWS.SNS.SMS.SenderID": {
                    "DataType": "String",
                    "StringValue": getattr(settings, "AWS_SNS_SENDER_ID", "AuthSvc"),
                },
                "AWS.SNS.SMS.SMSType": {
                    "DataType": "String",
                    "StringValue": "Transactional",  # Use Transactional for OTP
                },
            },
        )

        logger.info(f"SMS sent to {phone_number}, MessageId: {response['MessageId']}")
        return True

    except ClientError as e:
        logger.error(f"AWS SNS error sending to {phone_number}: {e}")
        raise self.retry(exc=e, countdown=60)
    except Exception as e:
        logger.error(f"Failed to send SMS to {phone_number}: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task
def send_welcome_email(email, first_name):
    """
    Send welcome email to new users.

    Args:
        email: User's email address
        first_name: User's first name
    """
    try:
        subject = "Welcome to Our Platform!"

        try:
            html_message = render_to_string(
                "emails/welcome.html",
                {"first_name": first_name},
            )
        except Exception:
            html_message = f"""
            <h2>Welcome, {first_name}!</h2>
            <p>Thank you for registering with us.</p>
            <p>We're excited to have you on board!</p>
            """

        plain_message = f"Welcome, {first_name}! Thank you for registering with us."

        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=True,
        )

        logger.info(f"Welcome email sent to {email}")

    except Exception as e:
        logger.error(f"Failed to send welcome email to {email}: {e}")


@shared_task
def send_employee_created_email(email, first_name, temporary_password):
    """
    Send email to newly created employees with their credentials.

    Args:
        email: Employee's email address
        first_name: Employee's first name
        temporary_password: Temporary password for first login
    """
    try:
        subject = "Your Employee Account Has Been Created"

        try:
            html_message = render_to_string(
                "emails/employee_created.html",
                {
                    "first_name": first_name,
                    "email": email,
                    "temporary_password": temporary_password,
                },
            )
        except Exception:
            html_message = f"""
            <h2>Welcome to the Team, {first_name}!</h2>
            <p>Your employee account has been created.</p>
            <p><strong>Login Details:</strong></p>
            <ul>
                <li>Email: {email}</li>
                <li>Temporary Password: {temporary_password}</li>
            </ul>
            <p>Please change your password after your first login.</p>
            """

        plain_message = f"Welcome, {first_name}! Your employee account has been created. Email: {email}, Temporary Password: {temporary_password}"

        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(f"Employee creation email sent to {email}")

    except Exception as e:
        logger.error(f"Failed to send employee creation email to {email}: {e}")


@shared_task
def cleanup_expired_verification_codes():
    """
    Periodic task to clean up expired verification codes.

    Should be scheduled to run daily.
    """
    from django.utils import timezone
    from accounts.models import VerificationCode

    count, _ = VerificationCode.objects.filter(
        expires_at__lt=timezone.now()
    ).delete()

    logger.info(f"Cleaned up {count} expired verification codes")
    return count
