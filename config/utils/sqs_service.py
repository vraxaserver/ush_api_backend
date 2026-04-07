"""
AWS SQS Task Dispatcher.

Sends task messages to SQS queues for async processing:
  - ush_gift_sms_queue  → gift card SMS notifications
  - ush_otp_sms_queue   → signup / OTP SMS verification
"""

import json
import logging

import boto3
from botocore.exceptions import ClientError
from decouple import config

logger = logging.getLogger(__name__)

# ── Queue names ──────────────────────────────────────────────────────────────
SMS_QUEUE = "ush_sms_queue"


def _get_sqs_client():
    """Return a boto3 SQS client using project AWS credentials."""
    return boto3.client(
        "sqs",
        aws_access_key_id=config("AWS_ACCESS_KEY_ID", default=""),
        aws_secret_access_key=config("AWS_SECRET_ACCESS_KEY", default=""),
        region_name=config("AWS_REGION_NAME", default="me-central-1"),
    )


def _get_queue_url(client, queue_name: str) -> str:
    """Resolve the SQS queue URL by name."""
    response = client.get_queue_url(QueueName=queue_name)
    return response["QueueUrl"]


def dispatch_to_sqs(queue_name: str, payload: dict) -> dict:
    """
    Send a JSON payload as a message to the named SQS queue.

    Args:
        queue_name: The SQS queue name (e.g. SMS_QUEUE).
        payload:    Dict that will be serialised to JSON as the message body.

    Returns:
        dict with 'success' bool and either 'message_id' or 'error'.
    """
    try:
        client = _get_sqs_client()
        queue_url = _get_queue_url(client, queue_name)

        response = client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(payload),
        )

        message_id = response.get("MessageId", "")
        logger.info(
            "SQS message sent to %s | MessageId: %s | payload keys: %s",
            queue_name,
            message_id,
            list(payload.keys()),
        )
        return {"success": True, "message_id": message_id}

    except ClientError as exc:
        logger.error("SQS ClientError dispatching to %s: %s", queue_name, exc)
        return {"success": False, "error": str(exc)}
    except Exception as exc:
        logger.error("Unexpected error dispatching to %s: %s", queue_name, exc)
        return {"success": False, "error": str(exc)}


# ── Convenience helpers ──────────────────────────────────────────────────────

def enqueue_otp_sms(phone_number: str, message: str) -> dict:
    """
    Enqueue an OTP / verification SMS to ush_sms_queue.

    Args:
        phone_number: E.164 formatted phone number.
        message:      SMS text to send.
    """
    return dispatch_to_sqs(
        SMS_QUEUE,
        {
            "task": "send_otp_sms",
            "sms_type": "otp",
            "phone_number": phone_number,
            "message": message,
        },
    )


def enqueue_gift_sms(gift_card_id: str) -> dict:
    """
    Enqueue a gift card SMS notification to ush_sms_queue.

    Args:
        gift_card_id: UUID string of the GiftCard instance.
    """
    return dispatch_to_sqs(
        SMS_QUEUE,
        {
            "task": "send_gift_card_sms",
            "sms_type": "gift_card",
            "gift_card_id": gift_card_id,
        },
    )
