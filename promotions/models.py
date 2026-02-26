"""
Promotions Models (Gift Cards & Loyalty Program).

Modular system for:
- Gift Cards: Prepaid balance cards that can be purchased and redeemed
- Loyalty Program: Earn free bookings after repeated paid bookings
"""

import secrets
import string
import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


# =============================================================================
# Loyalty Program Models
# =============================================================================

# Default number of successful bookings required to earn a free booking
LOYALTY_BOOKINGS_REQUIRED = 5


class LoyaltyTracker(models.Model):
    """
    Tracks loyalty progress per customer per service.

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
        unique_together = [("customer", "service")]
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["customer", "service"]),
        ]

    def __str__(self):
        return (
            f"{self.customer} – {self.service.name}: "
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

    # Optional expiry for the reward
    expires_at = models.DateTimeField(
        _("expires at"),
        null=True,
        blank=True,
        help_text=_("Leave blank for no expiry"),
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
        return (
            f"Reward for {self.customer} – {self.service.name} "
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

