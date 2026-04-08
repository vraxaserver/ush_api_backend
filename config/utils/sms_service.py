"""
SMS sender using KWT-SMS.com API.
"""

import logging
import requests
import threading
from django.conf import settings
from config.utils.gcc_utils import validate_gcc_number

logger = logging.getLogger(__name__)


def send_sms(phone_number: str, message: str, sender: str = None) -> dict:
    """
    Send an SMS message to a GCC phone number via KWT-SMS.com API.

    Args:
        phone_number: Destination phone number (any common format).
        message: The text message to send.
        sender: Alphanumeric Sender ID (defaults to settings.KWTSMS_SENDER).

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

    # ── Remove '+' if present (KWT-SMS mobile format) ──
    mobile = formatted.replace("+", "")

    # ── Prepare payload ──
    payload = {
        "username": settings.KWTSMS_USERNAME,
        "password": settings.KWTSMS_PASSWORD,
        "sender":   sender or settings.KWTSMS_SENDER,
        "mobile":   mobile,
        "message":  message,
        "test":     settings.KWTSMS_TEST_MODE,
    }

    # ── Send via HTTP ──
    try:
        resp = requests.post(
            "https://www.kwtsms.com/API/send/",
            json=payload,
            headers={"Accept": "application/json"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("result") == "OK":
            message_id = data.get("msg-id")
            logger.info(f"SMS sent successfully to {mobile} | Msg ID: {message_id}")
            return {
                "success": True,
                "message_id": message_id,
                "destination": formatted,
                "country": country,
            }
        else:
            error_code = data.get("code")
            description = data.get("description", "Unknown error")
            logger.error(f"KWT-SMS Error {error_code}: {description}")
            return {
                "success": False,
                "error": f"Error {error_code}: {description}",
            }

    except Exception as exc:
        logger.error(f"Failed to send SMS to {mobile}: {exc}")
        return {
            "success": False,
            "error": str(exc),
        }


def send_sms_async(phone_number: str, message: str, sender: str = None):
    """
    Asynchronously send an SMS using threading.Thread.
    """
    thread = threading.Thread(
        target=send_sms,
        args=(phone_number, message, sender),
        daemon=True,
    )
    thread.start()
    logger.info(f"Spawned thread for SMS to {phone_number}")
    return True

