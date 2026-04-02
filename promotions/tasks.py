"""
Task Functions for Promotions App.

Gift card SMS notifications are dispatched to AWS SQS (ush_gift_sms_queue)
for async processing by the SQS consumer.
"""

import logging

from django.conf import settings
from django.utils import timezone

from config.utils.sms_service import send_sms
from config.utils.sqs_service import enqueue_gift_sms

logger = logging.getLogger(__name__)


def send_gift_card_sms(gift_card_id):
    """
    Dispatch a gift card SMS notification to AWS SQS (ush_gift_sms_queue).

    The SQS consumer fetches the gift card and sends the SMS via SNS.

    Args:
        gift_card_id: UUID string of the GiftCard instance.

    Returns:
        dict: SQS dispatch result with 'success' and 'message_id' or 'error'.
    """
    logger.info(
        "Dispatching gift card SMS for %s to SQS (ush_gift_sms_queue)",
        gift_card_id,
    )

    result = enqueue_gift_sms(str(gift_card_id))

    if result.get("success"):
        logger.info(
            "Gift card SMS enqueued for %s | MessageId: %s",
            gift_card_id,
            result.get("message_id"),
        )
    else:
        logger.error(
            "Failed to enqueue gift card SMS for %s: %s",
            gift_card_id,
            result.get("error"),
        )

    return result
