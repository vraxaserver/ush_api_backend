"""
Async Task Functions for Auth Microservice.

Email tasks run directly (SES is already async enough at this scale).
OTP SMS tasks are dispatched to AWS SQS (ush_sms_queue) for
decoupled, async processing.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from config.utils.ses_mailer import ses_mailer
from config.utils.sms_service import send_sms, send_sms_async


logger = logging.getLogger(__name__)


# ============================================================================
# Email Tasks (sent directly – SES handles delivery async)
# ============================================================================

def send_email_verification(email, code, is_password_reset=False):
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

        context = {
            "code": code,
            "expiry_minutes": getattr(settings, "VERIFICATION_CODE_EXPIRY_MINUTES", 10),
        }

        try:
            html_message = render_to_string(template, context)
        except Exception:
            html_message = f"""
            <h2>{subject}</h2>
            <p>Your verification code is: <strong>{code}</strong></p>
            <p>This code will expire in {context['expiry_minutes']} minutes.</p>
            <p>If you didn't request this, please ignore this email.</p>
            """

        plain_message = (
            f"Your verification code is: {code}. "
            f"This code will expire in {context['expiry_minutes']} minutes."
        )

        ses_mailer.send(
            subject=subject,
            sender=settings.DEFAULT_FROM_EMAIL,
            to=[email],
            html_body=html_message,
            text_body=plain_message,
        )

        logger.info(f"Verification email sent to {email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {email}: {e}")
        return False


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

        ses_mailer.send(
            subject=subject,
            sender=settings.DEFAULT_FROM_EMAIL,
            to=[email],
            html_body=html_message,
            text_body=plain_message,
        )

        logger.info(f"Welcome email sent to {email}")

    except Exception as e:
        logger.error(f"Failed to send welcome email to {email}: {e}")


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

        plain_message = (
            f"Welcome, {first_name}! Your employee account has been created. "
            f"Email: {email}, Temporary Password: {temporary_password}"
        )

        ses_mailer.send(
            subject=subject,
            sender=settings.DEFAULT_FROM_EMAIL,
            to=[email],
            html_body=html_message,
            text_body=plain_message,
        )

        logger.info(f"Employee creation email sent to {email}")

    except Exception as e:
        logger.error(f"Failed to send employee creation email to {email}: {e}")


# ============================================================================
# SMS Tasks (dispatched to AWS SQS ush_otp_sms_queue)
# ============================================================================

def send_sms_verification(phone_number, code):
    """
    Dispatch an OTP SMS verification message to AWS SQS (ush_sms_queue).

    The SQS consumer is responsible for actually sending the SMS via SNS.

    Args:
        phone_number: Recipient phone number (E.164 format, e.g., +1234567890)
        code: Verification code

    Returns:
        dict: SQS dispatch result with 'success' and 'message_id' or 'error'.
    """
    expiry_minutes = getattr(settings, "VERIFICATION_CODE_EXPIRY_MINUTES", 10)
    message = f"Your verification code is: {code}. It expires in {expiry_minutes} minutes."

    logger.info("Sending OTP SMS for %s using send_sms_async", phone_number)
    send_sms_async(phone_number, message)
    return {"success": True}


# ============================================================================
# Maintenance (run directly, e.g. via management command or cron)
# ============================================================================

def cleanup_expired_verification_codes():
    """
    Clean up expired verification codes.

    Should be invoked via a management command or AWS EventBridge cron.
    """
    from django.utils import timezone
    from accounts.models import VerificationCode

    count, _ = VerificationCode.objects.filter(
        expires_at__lt=timezone.now()
    ).delete()

    logger.info(f"Cleaned up {count} expired verification codes")
    return count
