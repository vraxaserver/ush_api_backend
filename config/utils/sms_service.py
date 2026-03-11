"""
SMS sender using AWS SNS.
"""

import boto3
from botocore.exceptions import ClientError

from config.settings import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SNS_REGION, validate_config
from config.utils.gcc_utils import validate_gcc_number


def _get_sns_client():
    """Create and return a boto3 SNS client."""
    validate_config()
    return boto3.client(
        "sns",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_SNS_REGION,
    )


def send_sms(phone_number: str, message: str, sender_id: str = "NOTIFY") -> dict:
    """
    Send an SMS message to a GCC phone number via AWS SNS.

    Args:
        phone_number: Destination phone number (any common format).
        message: The text message to send (max 160 chars for a single SMS).
        sender_id: Alphanumeric Sender ID displayed on the recipient's device
                   (up to 11 characters, supported in all GCC countries).

    Returns:
        A dict with 'success', 'message_id' (on success), or 'error' (on failure).
    """
    # ── Validate phone number ──
    is_valid, country, formatted = validate_gcc_number(phone_number)
    if not is_valid:
        if country:
            return {
                "success": False,
                "error": f"Invalid phone number length for {country}.",
            }
        return {
            "success": False,
            "error": "Phone number does not belong to a GCC country.",
        }

    # ── Send via SNS ──
    try:
        client = _get_sns_client()
        response = client.publish(
            PhoneNumber=formatted,
            Message=message,
            MessageAttributes={
                "AWS.SNS.SMS.SenderID": {
                    "DataType": "String",
                    "StringValue": sender_id,
                },
                "AWS.SNS.SMS.SMSType": {
                    "DataType": "String",
                    "StringValue": "Transactional",
                },
            },
        )
        return {
            "success": True,
            "message_id": response["MessageId"],
            "destination": formatted,
            "country": country,
        }
    except ClientError as exc:
        return {
            "success": False,
            "error": str(exc),
        }
