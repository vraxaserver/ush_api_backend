"""
GCC phone-number utilities.

Validates and formats phone numbers for the six GCC countries:
  Saudi Arabia (+966), UAE (+971), Kuwait (+965),
  Qatar (+974), Bahrain (+973), Oman (+968)
"""

import re
from typing import Optional

# Country code → (country name, expected total digits including country code)
GCC_COUNTRIES: dict[str, tuple[str, int]] = {
    "966": ("Saudi Arabia", 12),   # +966 5x xxx xxxx  → 12 digits
    "971": ("UAE", 12),            # +971 5x xxx xxxx  → 12 digits
    "965": ("Kuwait", 11),         # +965 xxxx xxxx    → 11 digits
    "974": ("Qatar", 11),          # +974 xxxx xxxx    → 11 digits
    "973": ("Bahrain", 11),        # +973 xxxx xxxx    → 11 digits
    "968": ("Oman", 11),           # +968 xxxx xxxx    → 11 digits
}

_DIGITS_RE = re.compile(r"\D")  # non-digit characters


def format_phone_number(phone: str) -> str:
    """
    Normalise a phone number to E.164 format (+<digits>).

    Accepts inputs like:
      "00966501234567", "+966501234567", "966501234567", "0501234567" (ambiguous)
    """
    raw = _DIGITS_RE.sub("", phone)  # strip everything except digits

    # Remove leading "00" international prefix
    if raw.startswith("00"):
        raw = raw[2:]

    # If it already starts with a GCC country code, prepend '+'
    for code in GCC_COUNTRIES:
        if raw.startswith(code):
            return f"+{raw}"

    # Fallback: return as-is with '+' — the validator will catch bad numbers
    return f"+{raw}"


def validate_gcc_number(phone: str) -> tuple[bool, Optional[str], Optional[str]]:
    """
    Validate that a phone number belongs to a GCC country.

    Args:
        phone: Phone number in any common format.

    Returns:
        (is_valid, country_name | None, formatted_number | None)
    """
    formatted = format_phone_number(phone)
    digits = formatted.lstrip("+")

    for code, (country, expected_len) in GCC_COUNTRIES.items():
        if digits.startswith(code):
            if len(digits) == expected_len:
                return True, country, formatted
            else:
                return (
                    False,
                    country,
                    None,
                )

    return False, None, None


def list_gcc_countries() -> str:
    """Return a human-readable list of supported GCC countries."""
    lines = []
    for code, (name, _) in GCC_COUNTRIES.items():
        lines.append(f"  +{code}  {name}")
    return "\n".join(lines)

