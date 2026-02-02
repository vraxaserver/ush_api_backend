"""
Promotions Models (Vouchers & Gift Cards).

Modular system for:
- Vouchers: Discount codes for services and products
- Gift Cards: Prepaid balance cards that can be purchased and redeemed
"""

import secrets
import string
import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def generate_voucher_code(length=8):
    """Generate a random voucher code."""
    chars = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


def generate_gift_card_code(length=16):
    """Generate a random gift card code (format: XXXX-XXXX-XXXX-XXXX)."""
    chars = string.ascii_uppercase + string.digits
    code = "".join(secrets.choice(chars) for _ in range(length))
    return "-".join([code[i:i+4] for i in range(0, length, 4)])


# =============================================================================
# Voucher Models
# =============================================================================

class Voucher(models.Model):
    """
    Voucher/Coupon code for discounts.
    
    Can be applied to:
    - All services and products
    - Specific categories
    - Specific services or products
    - Specific countries/cities
    """

    class DiscountType(models.TextChoices):
        PERCENTAGE = "percentage", _("Percentage")
        FIXED = "fixed", _("Fixed Amount")

    class ApplicableTo(models.TextChoices):
        ALL = "all", _("All Services & Products")
        SERVICES = "services", _("Services Only")
        PRODUCTS = "products", _("Products Only")
        SPECIFIC = "specific", _("Specific Items")

    class Status(models.TextChoices):
        ACTIVE = "active", _("Active")
        INACTIVE = "inactive", _("Inactive")
        EXPIRED = "expired", _("Expired")
        EXHAUSTED = "exhausted", _("Exhausted")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Voucher Code
    code = models.CharField(
        _("voucher code"),
        max_length=50,
        unique=True,
        db_index=True,
        help_text=_("Unique voucher code"),
    )
    name = models.CharField(
        _("name"),
        max_length=200,
        help_text=_("Internal name for this voucher"),
    )
    description = models.TextField(_("description"), blank=True)

    # Discount Configuration
    discount_type = models.CharField(
        _("discount type"),
        max_length=20,
        choices=DiscountType.choices,
        default=DiscountType.PERCENTAGE,
    )
    discount_value = models.DecimalField(
        _("discount value"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text=_("Percentage (0-100) or fixed amount"),
    )
    max_discount_amount = models.DecimalField(
        _("maximum discount"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Cap for percentage discounts (optional)"),
    )

    # Applicability
    applicable_to = models.CharField(
        _("applicable to"),
        max_length=20,
        choices=ApplicableTo.choices,
        default=ApplicableTo.ALL,
    )
    
    # Specific items (when applicable_to = 'specific')
    # Using CharField to store comma-separated UUIDs for flexibility
    specific_service_ids = models.TextField(
        _("specific service IDs"),
        blank=True,
        help_text=_("Comma-separated service UUIDs"),
    )
    specific_product_ids = models.TextField(
        _("specific product IDs"),
        blank=True,
        help_text=_("Comma-separated product UUIDs (BaseProduct)"),
    )
    specific_categories = models.TextField(
        _("specific categories"),
        blank=True,
        help_text=_("Comma-separated category names"),
    )

    # Location Restrictions
    country = models.ForeignKey(
        "spacenter.Country",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vouchers",
        verbose_name=_("country"),
        help_text=_("Leave blank for all countries"),
    )
    city = models.ForeignKey(
        "spacenter.City",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vouchers",
        verbose_name=_("city"),
        help_text=_("Leave blank for all cities"),
    )

    # Usage Limits
    minimum_purchase = models.DecimalField(
        _("minimum purchase"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Minimum order amount to use this voucher"),
    )
    max_uses = models.PositiveIntegerField(
        _("maximum uses"),
        null=True,
        blank=True,
        help_text=_("Total number of times this voucher can be used"),
    )
    max_uses_per_user = models.PositiveIntegerField(
        _("max uses per user"),
        default=1,
        help_text=_("How many times a single user can use this voucher"),
    )
    current_uses = models.PositiveIntegerField(
        _("current uses"),
        default=0,
        editable=False,
    )

    # Validity Period
    valid_from = models.DateTimeField(_("valid from"))
    valid_until = models.DateTimeField(_("valid until"))

    # First-time user only
    first_time_only = models.BooleanField(
        _("first-time users only"),
        default=False,
        help_text=_("Only for users who haven't made a purchase before"),
    )

    # Status
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_vouchers",
        verbose_name=_("created by"),
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("voucher")
        verbose_name_plural = _("vouchers")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["status"]),
            models.Index(fields=["valid_from", "valid_until"]),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def clean(self):
        """Validate voucher configuration."""
        if self.discount_type == self.DiscountType.PERCENTAGE:
            if self.discount_value > 100:
                raise ValidationError(
                    {"discount_value": _("Percentage discount cannot exceed 100%.")}
                )
        
        if self.valid_until and self.valid_from:
            if self.valid_until <= self.valid_from:
                raise ValidationError(
                    {"valid_until": _("End date must be after start date.")}
                )
        
        if self.city and self.country:
            if self.city.country != self.country:
                raise ValidationError(
                    {"city": _("City must belong to the selected country.")}
                )

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = generate_voucher_code()
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        """Check if voucher is currently valid."""
        now = timezone.now()
        if self.status != self.Status.ACTIVE:
            return False
        if now < self.valid_from or now > self.valid_until:
            return False
        if self.max_uses and self.current_uses >= self.max_uses:
            return False
        return True

    @property
    def remaining_uses(self):
        """Get remaining uses."""
        if self.max_uses is None:
            return None
        return max(0, self.max_uses - self.current_uses)

    def calculate_discount(self, amount):
        """Calculate discount for a given amount."""
        if self.discount_type == self.DiscountType.PERCENTAGE:
            discount = amount * (self.discount_value / 100)
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
        else:
            discount = min(self.discount_value, amount)
        return round(discount, 2)

    def can_be_used_by(self, user, purchase_amount=None):
        """
        Check if voucher can be used by a specific user.
        Returns (bool, error_message).
        """
        if not self.is_valid:
            return False, _("This voucher is no longer valid.")

        if purchase_amount and purchase_amount < self.minimum_purchase:
            return False, _(
                f"Minimum purchase of {self.minimum_purchase} required."
            )

        # Check per-user limit
        user_uses = self.usages.filter(user=user).count()
        if user_uses >= self.max_uses_per_user:
            return False, _("You have already used this voucher.")

        return True, None


class VoucherUsage(models.Model):
    """
    Track voucher usage.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    voucher = models.ForeignKey(
        Voucher,
        on_delete=models.CASCADE,
        related_name="usages",
        verbose_name=_("voucher"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="voucher_usages",
        verbose_name=_("user"),
    )
    
    # Order reference (generic - can be booking_id, order_id, etc.)
    order_reference = models.CharField(
        _("order reference"),
        max_length=100,
        blank=True,
        help_text=_("Reference to the order/booking"),
    )
    order_type = models.CharField(
        _("order type"),
        max_length=50,
        blank=True,
        help_text=_("Type of order: service_booking, product_order, etc."),
    )
    
    # Discount details
    original_amount = models.DecimalField(
        _("original amount"),
        max_digits=10,
        decimal_places=2,
    )
    discount_amount = models.DecimalField(
        _("discount amount"),
        max_digits=10,
        decimal_places=2,
    )
    final_amount = models.DecimalField(
        _("final amount"),
        max_digits=10,
        decimal_places=2,
    )

    used_at = models.DateTimeField(_("used at"), auto_now_add=True)

    class Meta:
        verbose_name = _("voucher usage")
        verbose_name_plural = _("voucher usages")
        ordering = ["-used_at"]

    def __str__(self):
        return f"{self.voucher.code} used by {self.user}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        
        # Update voucher usage count
        if is_new:
            self.voucher.current_uses += 1
            if self.voucher.max_uses and self.voucher.current_uses >= self.voucher.max_uses:
                self.voucher.status = Voucher.Status.EXHAUSTED
            self.voucher.save(update_fields=["current_uses", "status"])


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
