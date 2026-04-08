"""
Task Functions for Promotions App.
"""

import logging
from django.utils import timezone
from promotions.models import GiftCard
from config.utils.sms_service import send_sms_async

logger = logging.getLogger(__name__)


def send_gift_card_sms(gift_card_id):
    """
    Fetch the gift card and send a notification SMS to the recipient.
    This replaces the SQS consumer logic.
    """
    try:
        gift_card = GiftCard.objects.get(id=gift_card_id)
        phone_number = str(gift_card.recipient_phone)
        secret_code = gift_card.secret_code
        public_url = gift_card.get_public_url()
        sender_name = gift_card.sender.get_full_name() or gift_card.sender.email
        service_name = gift_card.service.name

        recipient_hint = f" {gift_card.recipient_name}" if gift_card.recipient_name else ""
        
        message = (
            f"Hi{recipient_hint}, {sender_name} sent you a {service_name} gift! "
            f"Your secret code is: {secret_code}. "
            f"View details and redeem: {public_url}"
        )

        logger.info(f"Sending gift card SMS for {gift_card_id} to {phone_number}")
        
        # Send asynchronously
        send_sms_async(phone_number, message)
        
        # Update gift card status (optimistic tracking)
        gift_card.sms_sent = True
        gift_card.sms_sent_at = timezone.now()
        gift_card.save(update_fields=["sms_sent", "sms_sent_at", "updated_at"])
        
        return {"success": True}

    except GiftCard.DoesNotExist:
        logger.error(f"GiftCard {gift_card_id} not found for SMS sending.")
        return {"success": False, "error": "Gift card not found"}
    except Exception as e:
        logger.error(f"Error sending gift card SMS for {gift_card_id}: {e}")
        return {"success": False, "error": str(e)}
