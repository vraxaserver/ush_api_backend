"""
Celery Tasks for Promotions App.

Handles async email and SMS sending for gift card transfers.
"""

import logging

from celery import shared_task
from django.conf import settings
from django.template.loader import render_to_string
from config.utils.sns_services import sms_service
from config.utils.ses_mailer import ses_mailer

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_gift_card_welcome_email(
    self,
    email,
    first_name,
    password,
    gift_card_code,
    gift_card_amount,
    gift_card_currency,
    sender_name,
    message="",
):
    """
    Send welcome email to new users who received a gift card transfer.

    Args:
        email: Recipient email address
        first_name: Recipient's first name
        password: Generated password for the account
        gift_card_code: Gift card code
        gift_card_amount: Gift card balance amount
        gift_card_currency: Gift card currency
        sender_name: Name of the person who sent the gift
        message: Optional personal message from sender

    Returns:
        bool: True if email sent successfully
    """
    try:
        subject = f"You've received a gift card from {sender_name}!"

        # Try to render template, fallback to inline HTML
        try:
            html_message = render_to_string(
                "emails/gift_card_transfer.html",
                {
                    "first_name": first_name,
                    "email": email,
                    "password": password,
                    "gift_card_code": gift_card_code,
                    "gift_card_amount": gift_card_amount,
                    "gift_card_currency": gift_card_currency,
                    "sender_name": sender_name,
                    "message": message,
                    "app_download_link": getattr(settings, "APP_DOWNLOAD_LINK", ""),
                },
            )
        except Exception:
            # Fallback to inline HTML
            app_link = getattr(settings, "APP_DOWNLOAD_LINK", "https://example.com/download")
            message_html = f"<p><em>\"{message}\"</em></p>" if message else ""
            html_message = f"""
            <h2>Congratulations, {first_name}!</h2>
            <p>You've received a gift card worth <strong>{gift_card_currency} {gift_card_amount}</strong> from {sender_name}.</p>
            {message_html}
            <p><strong>Gift Card Code:</strong> {gift_card_code}</p>
            <hr>
            <p>A new account has been created for you:</p>
            <ul>
                <li><strong>Email:</strong> {email}</li>
                <li><strong>Password:</strong> {password}</li>
            </ul>
            <p>Please change your password after your first login.</p>
            <p><a href="{app_link}">Download our app</a> to redeem your gift card!</p>
            """

        plain_message = (
            f"Congratulations, {first_name}! "
            f"You've received a gift card worth {gift_card_currency} {gift_card_amount} from {sender_name}. "
            f"Gift Card Code: {gift_card_code}. "
            f"Your login credentials - Email: {email}, Password: {password}. "
            f"Please change your password after your first login."
        )

        ses_mailer.send(
            subject=subject,
            sender=settings.DEFAULT_FROM_EMAIL,
            to=[email],
            html_body=html_message,
            text_body=plain_message,
        )

        logger.info(f"Gift card welcome email sent to {email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send gift card email to {email}: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_gift_card_welcome_sms(
    self,
    phone_number,
    first_name,
    password,
    gift_card_amount,
    gift_card_currency,
):
    """
    Send welcome SMS to new users who received a gift card transfer.

    Args:
        phone_number: Recipient phone number (E.164 format)
        first_name: Recipient's first name
        password: Generated password for the account
        gift_card_amount: Gift card balance amount
        gift_card_currency: Gift card currency

    Returns:
        bool: True if SMS sent successfully
    """
    try:
        app_link = getattr(settings, "APP_DOWNLOAD_LINK", "")
        
        message = (
            f"Hi {first_name}! You've received a gift card worth {gift_card_currency} {gift_card_amount}. "
            f"Your password: {password}. "
            f"Download our app to redeem: {app_link}"
        )

        result = sms_service.send_sms(phone_number, message)
        
        if result.get("success"):
            logger.info(f"Gift card welcome SMS sent to {phone_number}")
            return True
        else:
            logger.error(f"SMS send failed: {result.get('error')}")
            raise Exception(result.get("error", "SMS send failed"))

    except Exception as e:
        logger.error(f"Failed to send gift card SMS to {phone_number}: {e}")
        raise self.retry(exc=e, countdown=60)
