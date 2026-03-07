"""
Promotions Models (Gift Cards & Loyalty Program).

Modular system for:
- Gift Cards: Gift a service to someone via phone number with secret code redemption
- Loyalty Program: Earn free bookings after repeated paid bookings
"""

import random
import secrets
import string
import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField


# =============================================================================
# Loyalty Program Models
# =============================================================================

# Default number of successful bookings required to earn a free booking
LOYALTY_BOOKINGS_REQUIRED = 5

# Default number of days before a loyalty reward expires
LOYALTY_REWARD_EXPIRY_DAYS = 10


def default_reward_expiry():
    """Return the default expiry datetime for a loyalty reward (10 days from now)."""
    return timezone.now() + timezone.timedelta(days=LOYALTY_REWARD_EXPIRY_DAYS)


class LoyaltyTracker(models.Model):
    """
    Tracks loyalty progress per customer per service per arrangement.

    Incremented on every successful (paid) booking for an eligible service.
    When `booking_count` reaches `bookings_required` (default 5),
    a LoyaltyReward is issued and the counter resets to 0.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="loyalty_trackers",
        verbose_name=_("customer"),
    )
    service = models.ForeignKey(
        "spacenter.Service",
        on_delete=models.CASCADE,
        related_name="loyalty_trackers",
        verbose_name=_("service"),
    )
    service_arrangement = models.ForeignKey(
        "spacenter.ServiceArrangement",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="loyalty_trackers",
        verbose_name=_("service arrangement"),
        help_text=_("Room/setup configuration for this loyalty tracker"),
    )

    # Rolling counter – resets to 0 after reward is issued
    booking_count = models.PositiveIntegerField(
        _("booking count"),
        default=0,
        help_text=_("Number of paid bookings since last reward or start"),
    )

    # Configurable per-tracker (defaults to global constant)
    bookings_required = models.PositiveIntegerField(
        _("bookings required"),
        default=LOYALTY_BOOKINGS_REQUIRED,
        help_text=_("Number of paid bookings needed to earn a free booking"),
    )

    # Lifetime statistics
    total_bookings = models.PositiveIntegerField(
        _("total bookings"),
        default=0,
        help_text=_("Lifetime count of qualifying paid bookings"),
    )
    total_rewards_earned = models.PositiveIntegerField(
        _("total rewards earned"),
        default=0,
        help_text=_("Lifetime count of loyalty rewards earned"),
    )

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("loyalty tracker")
        verbose_name_plural = _("loyalty trackers")
        unique_together = [("customer", "service", "service_arrangement")]
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["customer", "service", "service_arrangement"]),
        ]

    def __str__(self):
        label = self.service.name
        if self.service_arrangement:
            label += f" ({self.service_arrangement.arrangement_label})"
        return (
            f"{self.customer} – {label}: "
            f"{self.booking_count}/{self.bookings_required}"
        )

    @property
    def progress_percentage(self):
        """Return progress towards the next reward as a percentage."""
        if self.bookings_required == 0:
            return 100
        return round((self.booking_count / self.bookings_required) * 100, 1)

    @property
    def bookings_remaining(self):
        """Return how many more bookings are needed for the next reward."""
        return max(0, self.bookings_required - self.booking_count)

    def record_booking(self, booking=None):
        """
        Record a successful paid booking and issue a reward if threshold is met.

        Args:
            booking: Optional Booking instance to link in the reward.

        Returns:
            LoyaltyReward instance if a reward was issued, else None.
        """
        self.booking_count += 1
        self.total_bookings += 1

        reward = None
        if self.booking_count >= self.bookings_required:
            reward = LoyaltyReward.objects.create(
                customer=self.customer,
                service=self.service,
                service_arrangement=self.service_arrangement,
                earned_from_booking=booking,
            )
            self.booking_count = 0
            self.total_rewards_earned += 1

        self.save(update_fields=[
            "booking_count",
            "total_bookings",
            "total_rewards_earned",
            "updated_at",
        ])
        return reward


class LoyaltyReward(models.Model):
    """
    A one-time free booking reward earned through the loyalty program.

    Issued automatically when a customer completes the required number of
    paid bookings for a loyalty-eligible service.
    """

    class RewardStatus(models.TextChoices):
        AVAILABLE = "available", _("Available")
        REDEEMED = "redeemed", _("Redeemed")
        EXPIRED = "expired", _("Expired")
        CANCELLED = "cancelled", _("Cancelled")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="loyalty_rewards",
        verbose_name=_("customer"),
    )
    service = models.ForeignKey(
        "spacenter.Service",
        on_delete=models.CASCADE,
        related_name="loyalty_rewards",
        verbose_name=_("service"),
    )
    service_arrangement = models.ForeignKey(
        "spacenter.ServiceArrangement",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="loyalty_rewards",
        verbose_name=_("service arrangement"),
        help_text=_("Room/setup configuration for this loyalty reward"),
    )

    status = models.CharField(
        _("status"),
        max_length=20,
        choices=RewardStatus.choices,
        default=RewardStatus.AVAILABLE,
    )

    # Booking that triggered the reward
    earned_from_booking = models.ForeignKey(
        "bookings.Booking",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="earned_loyalty_rewards",
        verbose_name=_("earned from booking"),
    )

    # Booking where the reward was redeemed (the free booking)
    redeemed_in_booking = models.ForeignKey(
        "bookings.Booking",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="redeemed_loyalty_rewards",
        verbose_name=_("redeemed in booking"),
    )

    redeemed_at = models.DateTimeField(
        _("redeemed at"),
        null=True,
        blank=True,
    )

    # Expiry – defaults to 10 days after creation
    expires_at = models.DateTimeField(
        _("expires at"),
        default=default_reward_expiry,
        help_text=_(
            "Reward expires after this date and cannot be redeemed. "
            "Defaults to 10 days after creation. Admin can adjust."
        ),
    )

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("loyalty reward")
        verbose_name_plural = _("loyalty rewards")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["customer", "status"]),
            models.Index(fields=["service", "status"]),
        ]

    def __str__(self):
        label = self.service.name
        if self.service_arrangement:
            label += f" ({self.service_arrangement.arrangement_label})"
        return (
            f"Reward for {self.customer} – {label} "
            f"({self.get_status_display()})"
        )

    @property
    def is_available(self):
        """Check if the reward can still be redeemed."""
        if self.status != self.RewardStatus.AVAILABLE:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True

    def redeem(self, booking=None):
        """
        Mark the reward as redeemed.

        Args:
            booking: Optional Booking instance (the free booking).

        Returns:
            (success, error_message) tuple.
        """
        if not self.is_available:
            return False, _("This reward is no longer available.")

        self.status = self.RewardStatus.REDEEMED
        self.redeemed_at = timezone.now()
        self.redeemed_in_booking = booking
        self.save(update_fields=["status", "redeemed_at", "redeemed_in_booking", "updated_at"])
        return True, None


# =============================================================================
# Gift Card Models
# =============================================================================

def generate_secret_code():
    """Generate a random 6-digit secret code for gift card redemption."""
    return "".join(random.choices(string.digits, k=6))


def generate_public_token():
    """Generate a UUID-based public token for gift card public page access."""
    return uuid.uuid4().hex[:16]


class GiftCard(models.Model):
    """
    Gift Card – Gift a service to someone via their phone number.

    Flow:
    1. Authenticated user selects a service and recipient phone number.
    2. Payment is processed (Stripe).
    3. On successful payment, an SMS is sent to the recipient with:
       - A 6-digit secret code
       - A public page URL where service & location details are shown
    4. Recipient can visit the public page and:
       - Check validity of the gift card
       - Redeem the gift card using their 6-digit secret code
    """

    class GiftCardStatus(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", _("Pending Payment")
        ACTIVE = "active", _("Active")
        REDEEMED = "redeemed", _("Redeemed")
        EXPIRED = "expired", _("Expired")
        CANCELLED = "cancelled", _("Cancelled")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Sender (must be an authenticated user)
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_gift_cards",
        verbose_name=_("sender"),
    )

    # Recipient (identified by phone number only – may or may not be a system user)
    recipient_phone = PhoneNumberField(
        _("recipient phone number"),
        help_text=_("Phone number of the gift recipient (E.164 format)"),
    )
    recipient_name = models.CharField(
        _("recipient name"),
        max_length=150,
        blank=True,
        help_text=_("Optional display name for the recipient"),
    )
    gift_message = models.TextField(
        _("gift message"),
        blank=True,
        help_text=_("Optional personal message from the sender"),
    )

    # Gifted service
    service = models.ForeignKey(
        "spacenter.Service",
        on_delete=models.PROTECT,
        related_name="gift_cards",
        verbose_name=_("gifted service"),
    )
    spa_center = models.ForeignKey(
        "spacenter.SpaCenter",
        on_delete=models.PROTECT,
        related_name="gift_cards",
        verbose_name=_("spa center"),
    )

    # Price snapshot (at time of purchase)
    amount = models.DecimalField(
        _("amount"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_("Price paid for the gifted service"),
    )
    currency = models.CharField(
        _("currency"),
        max_length=3,
        default="QAR",
    )

    # Service arrangement (room/setup configuration) — REQUIRED
    service_arrangement = models.ForeignKey(
        "spacenter.ServiceArrangement",
        on_delete=models.PROTECT,
        related_name="gift_cards",
        verbose_name=_("service arrangement"),
        help_text=_("Room/setup configuration for the gifted service"),
    )

    # Extra minutes and total duration
    extra_minutes = models.PositiveIntegerField(
        _("extra minutes"),
        default=0,
        help_text=_("Extra minutes added to the service duration"),
    )
    total_duration = models.PositiveIntegerField(
        _("total duration (minutes)"),
        default=0,
        help_text=_("Total duration in minutes (service duration + extra minutes)"),
    )

    # Secret code for redemption (6 digits)
    secret_code = models.CharField(
        _("secret code"),
        max_length=6,
        default=generate_secret_code,
        help_text=_("6-digit secret code sent to recipient via SMS"),
    )

    # Public access token (for the public page URL – non-guessable)
    public_token = models.CharField(
        _("public token"),
        max_length=32,
        default=generate_public_token,
        unique=True,
        db_index=True,
        help_text=_("Token used in the public gift card page URL"),
    )

    # Status tracking
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=GiftCardStatus.choices,
        default=GiftCardStatus.PENDING_PAYMENT,
        db_index=True,
    )

    # Redemption tracking
    redeemed_at = models.DateTimeField(
        _("redeemed at"),
        null=True,
        blank=True,
    )
    redeemed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="redeemed_gift_cards",
        verbose_name=_("redeemed by"),
        help_text=_("System user who redeemed the gift card (if they exist)"),
    )
    redeemed_booking = models.ForeignKey(
        "bookings.Booking",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gift_card_redemptions",
        verbose_name=_("redeemed in booking"),
    )

    # Expiry
    expires_at = models.DateTimeField(
        _("expires at"),
        null=True,
        blank=True,
        help_text=_("Leave blank for no expiry"),
    )

    # SMS tracking
    sms_sent = models.BooleanField(
        _("SMS sent"),
        default=False,
        help_text=_("Whether the SMS with secret code has been sent"),
    )
    sms_sent_at = models.DateTimeField(
        _("SMS sent at"),
        null=True,
        blank=True,
    )

    # Failed redemption attempt tracking (security)
    failed_attempts = models.PositiveIntegerField(
        _("failed redemption attempts"),
        default=0,
    )
    max_attempts = models.PositiveIntegerField(
        _("max redemption attempts"),
        default=5,
    )

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("gift card")
        verbose_name_plural = _("gift cards")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["sender", "status"]),
            models.Index(fields=["recipient_phone", "status"]),
            models.Index(fields=["public_token"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return (
            f"Gift: {self.service.name} → {self.recipient_phone} "
            f"({self.get_status_display()})"
        )

    @property
    def is_redeemable(self):
        """Check if the gift card can be redeemed."""
        if self.status != self.GiftCardStatus.ACTIVE:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        if self.failed_attempts >= self.max_attempts:
            return False
        return True

    @property
    def is_expired(self):
        """Check if the gift card has expired."""
        if self.expires_at and timezone.now() > self.expires_at:
            return True
        return False

    @property
    def is_locked(self):
        """Check if too many failed attempts have locked the gift card."""
        return self.failed_attempts >= self.max_attempts

    def get_public_url(self):
        """Return the public page URL for this gift card."""
        base_url = getattr(settings, "SITE_BASE_URL", "http://localhost:8000")
        return f"{base_url}/gift-cards/public/{self.public_token}/"

    def record_failed_attempt(self):
        """Record a failed redemption attempt."""
        self.failed_attempts += 1
        self.save(update_fields=["failed_attempts", "updated_at"])

    def activate(self):
        """Activate the gift card after successful payment."""
        self.status = self.GiftCardStatus.ACTIVE
        self.save(update_fields=["status", "updated_at"])

    def redeem(self, secret_code, redeemed_by_user=None):
        """
        Attempt to redeem the gift card with a secret code.

        Args:
            secret_code: The 6-digit code to verify.
            redeemed_by_user: Optional User instance who is redeeming.

        Returns:
            (success, error_message) tuple.
        """
        if not self.is_redeemable:
            if self.is_expired:
                return False, _("This gift card has expired.")
            if self.is_locked:
                return False, _("Too many failed attempts. This gift card is locked.")
            return False, _("This gift card is not available for redemption.")

        if self.secret_code != secret_code:
            self.record_failed_attempt()
            remaining = self.max_attempts - self.failed_attempts
            if remaining <= 0:
                return False, _(
                    "Invalid code. This gift card is now locked due to too many failed attempts."
                )
            return False, _(
                f"Invalid code. {remaining} attempt(s) remaining."
            )

        # Successful redemption
        self.status = self.GiftCardStatus.REDEEMED
        self.redeemed_at = timezone.now()
        self.redeemed_by = redeemed_by_user
        self.save(update_fields=[
            "status", "redeemed_at", "redeemed_by", "updated_at",
        ])
        return True, None
