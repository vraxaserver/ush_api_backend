"""
Celery Tasks for Promotions App.

Handles async SMS sending for gift card notifications.
"""

import logging

from celery import shared_task
from django.conf import settings
from django.utils import timezone
from config.utils.sms_service import send_sms

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_gift_card_sms(self, gift_card_id):
    """
    Send SMS to gift card recipient with their secret code and public page URL.

    Args:
        gift_card_id: UUID string of the GiftCard instance.

    The SMS includes:
    - A short message about the gifted service
    - The 6-digit secret code
    - The public page URL
    """
    from promotions.models import GiftCard

    try:
        gift_card = GiftCard.objects.select_related(
            "service", "spa_center", "sender",
        ).get(id=gift_card_id)

        if gift_card.status != GiftCard.GiftCardStatus.ACTIVE:
            logger.warning(
                "Gift card %s is not active (status: %s). Skipping SMS.",
                gift_card_id,
                gift_card.status,
            )
            return False

        # Build SMS message
        sender_name = gift_card.sender.get_full_name() or "Someone"
        public_url = gift_card.get_public_url()

        message = (
            f"🎁 {sender_name} has gifted you a spa service: "
            f"{gift_card.service.name} at {gift_card.spa_center.name}! "
            f"Your secret code: {gift_card.secret_code}. "
            f"View details & redeem: {public_url}"
        )

        # Send SMS
        phone_number = str(gift_card.recipient_phone)
        result = send_sms(phone_number, message)

        logger.info(
            "Gift card SMS sent to %s for gift card %s. Result: %s",
            phone_number,
            gift_card_id,
            result,
        )

        # Update SMS tracking
        gift_card.sms_sent = True
        gift_card.sms_sent_at = timezone.now()
        gift_card.save(update_fields=["sms_sent", "sms_sent_at", "updated_at"])

        return True

    except GiftCard.DoesNotExist:
        logger.error("Gift card %s not found. Cannot send SMS.", gift_card_id)
        return False

    except Exception as e:
        logger.error(
            "Failed to send gift card SMS for %s: %s",
            gift_card_id,
            str(e),
        )
        raise self.retry(exc=e, countdown=60)
