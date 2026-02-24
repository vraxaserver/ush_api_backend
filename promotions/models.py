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


def generate_gift_card_code(length=16):
    """Generate a random gift card code (format: XXXX-XXXX-XXXX-XXXX)."""
    chars = string.ascii_uppercase + string.digits
    code = "".join(secrets.choice(chars) for _ in range(length))
    return "-".join([code[i:i+4] for i in range(0, length, 4)])


# =============================================================================
# Gift Card Models
# =============================================================================

class GiftCardTemplate(models.Model):
    """
    Gift card templates/denominations.
    
    Defines available gift card options for purchase.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(_("name"), max_length=200)
    description = models.TextField(_("description"), blank=True)
    image = models.ImageField(
        _("image"),
        upload_to="gift_cards/templates/",
        null=True,
        blank=True,
    )

    # Value
    amount = models.DecimalField(
        _("amount"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("1.00"))],
    )
    currency = models.CharField(
        _("currency"),
        max_length=10,
        default="QAR",
    )

    # Validity
    validity_days = models.PositiveIntegerField(
        _("validity days"),
        default=365,
        help_text=_("Number of days the gift card is valid after purchase"),
    )

    # Applicability
    applicable_to_services = models.BooleanField(
        _("applicable to services"),
        default=True,
    )
    applicable_to_products = models.BooleanField(
        _("applicable to products"),
        default=True,
    )

    # Location restrictions
    country = models.ForeignKey(
        "spacenter.Country",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gift_card_templates",
        verbose_name=_("country"),
        help_text=_("Leave blank for all countries"),
    )

    is_active = models.BooleanField(_("active"), default=True)
    sort_order = models.PositiveIntegerField(_("sort order"), default=0)
    
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("gift card template")
        verbose_name_plural = _("gift card templates")
        ordering = ["sort_order", "amount"]

    def __str__(self):
        return f"{self.name} - {self.currency} {self.amount}"


class GiftCard(models.Model):
    """
    Individual gift card instance.
    
    Created when a gift card is purchased.
    """

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending Activation")
        ACTIVE = "active", _("Active")
        PARTIALLY_USED = "partially_used", _("Partially Used")
        FULLY_USED = "fully_used", _("Fully Used")
        EXPIRED = "expired", _("Expired")
        CANCELLED = "cancelled", _("Cancelled")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Card Details
    code = models.CharField(
        _("gift card code"),
        max_length=50,
        unique=True,
        db_index=True,
    )
    pin = models.CharField(
        _("PIN"),
        max_length=10,
        blank=True,
        help_text=_("Optional security PIN"),
    )
    
    template = models.ForeignKey(
        GiftCardTemplate,
        on_delete=models.PROTECT,
        related_name="gift_cards",
        verbose_name=_("template"),
        null=True,
        blank=True,
    )

    # Value
    initial_amount = models.DecimalField(
        _("initial amount"),
        max_digits=10,
        decimal_places=2,
    )
    current_balance = models.DecimalField(
        _("current balance"),
        max_digits=10,
        decimal_places=2,
    )
    currency = models.CharField(
        _("currency"),
        max_length=10,
        default="QAR",
    )

    # Ownership
    purchased_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purchased_gift_cards",
        verbose_name=_("purchased by"),
    )
    recipient_email = models.EmailField(
        _("recipient email"),
        blank=True,
        help_text=_("Email to send the gift card to"),
    )
    recipient_name = models.CharField(
        _("recipient name"),
        max_length=200,
        blank=True,
    )
    recipient_message = models.TextField(
        _("gift message"),
        blank=True,
        help_text=_("Personal message from purchaser"),
    )
    recipient_phone = models.CharField(
        _("recipient phone"),
        max_length=20,
        blank=True,
        help_text=_("Phone number of recipient"),
    )
    
    # Current owner (can be transferred)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_gift_cards",
        verbose_name=_("current owner"),
    )

    # Location restrictions (inherited from template or custom)
    country = models.ForeignKey(
        "spacenter.Country",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gift_cards",
        verbose_name=_("country"),
    )

    # Applicability
    applicable_to_services = models.BooleanField(
        _("applicable to services"),
        default=True,
    )
    applicable_to_products = models.BooleanField(
        _("applicable to products"),
        default=True,
    )

    # Validity
    valid_from = models.DateTimeField(_("valid from"))
    valid_until = models.DateTimeField(_("valid until"))

    # Status
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    # Payment reference
    payment_reference = models.CharField(
        _("payment reference"),
        max_length=100,
        blank=True,
    )
    
    # Flags
    is_transferable = models.BooleanField(
        _("transferable"),
        default=True,
        help_text=_("Can this gift card be transferred to another user"),
    )

    # Timestamps
    purchased_at = models.DateTimeField(_("purchased at"), null=True, blank=True)
    activated_at = models.DateTimeField(_("activated at"), null=True, blank=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("gift card")
        verbose_name_plural = _("gift cards")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["status"]),
            models.Index(fields=["owner"]),
            models.Index(fields=["valid_until"]),
        ]

    def __str__(self):
        return f"{self.code} - {self.currency} {self.current_balance}"

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = generate_gift_card_code()
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        """Check if gift card is currently valid."""
        now = timezone.now()
        if self.status not in [self.Status.ACTIVE, self.Status.PARTIALLY_USED]:
            return False
        if now < self.valid_from or now > self.valid_until:
            return False
        if self.current_balance <= 0:
            return False
        return True

    @property
    def is_expired(self):
        """Check if gift card has expired."""
        return timezone.now() > self.valid_until

    @property
    def used_amount(self):
        """Get total used amount."""
        return self.initial_amount - self.current_balance

    def activate(self):
        """Activate the gift card."""
        if self.status == self.Status.PENDING:
            self.status = self.Status.ACTIVE
            self.activated_at = timezone.now()
            self.save(update_fields=["status", "activated_at"])

    def redeem(self, amount, user, order_reference="", order_type=""):
        """
        Redeem amount from gift card.
        Returns (success, redeemed_amount, error_message).
        """
        if not self.is_valid:
            return False, Decimal("0"), _("Gift card is not valid.")

        if amount <= 0:
            return False, Decimal("0"), _("Invalid redemption amount.")

        redeemable = min(amount, self.current_balance)
        
        # Create transaction
        GiftCardTransaction.objects.create(
            gift_card=self,
            transaction_type=GiftCardTransaction.TransactionType.REDEMPTION,
            amount=-redeemable,
            balance_after=self.current_balance - redeemable,
            user=user,
            order_reference=order_reference,
            order_type=order_type,
        )

        # Update balance
        self.current_balance -= redeemable
        if self.current_balance <= 0:
            self.status = self.Status.FULLY_USED
        else:
            self.status = self.Status.PARTIALLY_USED
        self.save(update_fields=["current_balance", "status"])

        return True, redeemable, None

    def refund(self, amount, user, order_reference="", reason=""):
        """
        Refund amount to gift card.
        """
        if amount <= 0:
            return False, _("Invalid refund amount.")

        # Create transaction
        GiftCardTransaction.objects.create(
            gift_card=self,
            transaction_type=GiftCardTransaction.TransactionType.REFUND,
            amount=amount,
            balance_after=self.current_balance + amount,
            user=user,
            order_reference=order_reference,
            notes=reason,
        )

        # Update balance
        self.current_balance += amount
        if self.current_balance > 0 and self.status == self.Status.FULLY_USED:
            self.status = self.Status.PARTIALLY_USED
        self.save(update_fields=["current_balance", "status"])

        return True, None

    def transfer_to(self, new_owner):
        """Transfer gift card to a new owner."""
        if not self.is_transferable:
            return False, _("This gift card cannot be transferred.")
        
        if not self.is_valid:
            return False, _("Cannot transfer an invalid gift card.")

        old_owner = self.owner
        self.owner = new_owner
        self.save(update_fields=["owner"])

        # Log transfer
        GiftCardTransaction.objects.create(
            gift_card=self,
            transaction_type=GiftCardTransaction.TransactionType.TRANSFER,
            amount=Decimal("0"),
            balance_after=self.current_balance,
            user=new_owner,
            notes=f"Transferred from {old_owner}",
        )

        return True, None


class GiftCardTransaction(models.Model):
    """
    Gift card transaction history.
    """

    class TransactionType(models.TextChoices):
        PURCHASE = "purchase", _("Purchase")
        ACTIVATION = "activation", _("Activation")
        REDEMPTION = "redemption", _("Redemption")
        REFUND = "refund", _("Refund")
        TRANSFER = "transfer", _("Transfer")
        EXPIRY = "expiry", _("Expiry")
        ADJUSTMENT = "adjustment", _("Admin Adjustment")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    gift_card = models.ForeignKey(
        GiftCard,
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name=_("gift card"),
    )
    
    transaction_type = models.CharField(
        _("transaction type"),
        max_length=20,
        choices=TransactionType.choices,
    )
    
    amount = models.DecimalField(
        _("amount"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Positive for credit, negative for debit"),
    )
    balance_after = models.DecimalField(
        _("balance after"),
        max_digits=10,
        decimal_places=2,
    )

    # Reference
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gift_card_transactions",
        verbose_name=_("user"),
    )
    order_reference = models.CharField(
        _("order reference"),
        max_length=100,
        blank=True,
    )
    order_type = models.CharField(
        _("order type"),
        max_length=50,
        blank=True,
    )
    notes = models.TextField(_("notes"), blank=True)

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("gift card transaction")
        verbose_name_plural = _("gift card transactions")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.gift_card.code} - {self.transaction_type}: {self.amount}"


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

