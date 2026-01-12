"""
Promotions (Vouchers & Gift Cards) Serializers.
"""

from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from .models import (
    GiftCard,
    GiftCardTemplate,
    GiftCardTransaction,
    Voucher,
    VoucherUsage,
)


# =============================================================================
# Voucher Serializers
# =============================================================================

class VoucherSerializer(serializers.ModelSerializer):
    """Serializer for Voucher model."""

    discount_display = serializers.SerializerMethodField()
    is_valid = serializers.BooleanField(read_only=True)
    remaining_uses = serializers.IntegerField(read_only=True)

    class Meta:
        model = Voucher
        fields = [
            "id",
            "code",
            "name",
            "description",
            "discount_type",
            "discount_value",
            "max_discount_amount",
            "discount_display",
            "applicable_to",
            "minimum_purchase",
            "max_uses_per_user",
            "valid_from",
            "valid_until",
            "first_time_only",
            "status",
            "is_valid",
            "remaining_uses",
        ]

    def get_discount_display(self, obj):
        """Get human-readable discount display."""
        if obj.discount_type == Voucher.DiscountType.PERCENTAGE:
            text = f"{obj.discount_value}% off"
            if obj.max_discount_amount:
                text += f" (max {obj.max_discount_amount})"
        else:
            text = f"{obj.discount_value} off"
        return text


class VoucherValidateSerializer(serializers.Serializer):
    """Serializer for validating a voucher code."""

    code = serializers.CharField(max_length=50)
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        help_text="Order amount to validate minimum purchase",
    )

    def validate_code(self, value):
        """Validate voucher code exists and is valid."""
        try:
            voucher = Voucher.objects.get(code__iexact=value)
        except Voucher.DoesNotExist:
            raise serializers.ValidationError("Invalid voucher code.")

        if not voucher.is_valid:
            if voucher.status == Voucher.Status.EXPIRED:
                raise serializers.ValidationError("This voucher has expired.")
            elif voucher.status == Voucher.Status.EXHAUSTED:
                raise serializers.ValidationError("This voucher has been fully used.")
            elif voucher.status == Voucher.Status.INACTIVE:
                raise serializers.ValidationError("This voucher is not active.")
            else:
                raise serializers.ValidationError("This voucher is not valid.")

        return value

    def validate(self, attrs):
        """Full validation including amount check."""
        code = attrs.get("code")
        amount = attrs.get("amount")

        voucher = Voucher.objects.get(code__iexact=code)

        if amount and amount < voucher.minimum_purchase:
            raise serializers.ValidationError({
                "amount": f"Minimum purchase of {voucher.minimum_purchase} required."
            })

        # Check user-specific limits if user is authenticated
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            can_use, error = voucher.can_be_used_by(request.user, amount)
            if not can_use:
                raise serializers.ValidationError({"code": error})

        attrs["voucher"] = voucher
        return attrs


class VoucherApplySerializer(serializers.Serializer):
    """Serializer for applying a voucher to an order."""

    code = serializers.CharField(max_length=50)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    order_reference = serializers.CharField(max_length=100, required=False, default="")
    order_type = serializers.CharField(max_length=50, required=False, default="")

    def validate(self, attrs):
        """Validate voucher can be applied."""
        code = attrs.get("code")
        amount = attrs.get("amount")

        try:
            voucher = Voucher.objects.get(code__iexact=code)
        except Voucher.DoesNotExist:
            raise serializers.ValidationError({"code": "Invalid voucher code."})

        request = self.context.get("request")
        if request and request.user.is_authenticated:
            can_use, error = voucher.can_be_used_by(request.user, amount)
            if not can_use:
                raise serializers.ValidationError({"code": error})
        else:
            raise serializers.ValidationError({"code": "Authentication required."})

        attrs["voucher"] = voucher
        attrs["user"] = request.user
        return attrs

    def create(self, validated_data):
        """Apply the voucher and create usage record."""
        voucher = validated_data["voucher"]
        user = validated_data["user"]
        amount = validated_data["amount"]
        order_reference = validated_data.get("order_reference", "")
        order_type = validated_data.get("order_type", "")

        discount = voucher.calculate_discount(amount)
        final_amount = amount - discount

        usage = VoucherUsage.objects.create(
            voucher=voucher,
            user=user,
            order_reference=order_reference,
            order_type=order_type,
            original_amount=amount,
            discount_amount=discount,
            final_amount=final_amount,
        )

        return usage


class VoucherUsageSerializer(serializers.ModelSerializer):
    """Serializer for VoucherUsage model."""

    voucher_code = serializers.CharField(source="voucher.code", read_only=True)

    class Meta:
        model = VoucherUsage
        fields = [
            "id",
            "voucher",
            "voucher_code",
            "order_reference",
            "order_type",
            "original_amount",
            "discount_amount",
            "final_amount",
            "used_at",
        ]
        read_only_fields = fields


# =============================================================================
# Gift Card Serializers
# =============================================================================

class GiftCardTemplateSerializer(serializers.ModelSerializer):
    """Serializer for GiftCardTemplate model."""

    class Meta:
        model = GiftCardTemplate
        fields = [
            "id",
            "name",
            "description",
            "image",
            "amount",
            "currency",
            "validity_days",
            "applicable_to_services",
            "applicable_to_products",
            "country",
            "is_active",
        ]


class GiftCardSerializer(serializers.ModelSerializer):
    """Serializer for GiftCard model."""

    template_name = serializers.CharField(
        source="template.name",
        read_only=True,
    )
    is_valid = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    used_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )
    balance_percentage = serializers.SerializerMethodField()

    class Meta:
        model = GiftCard
        fields = [
            "id",
            "code",
            "template",
            "template_name",
            "initial_amount",
            "current_balance",
            "currency",
            "used_amount",
            "balance_percentage",
            "status",
            "is_valid",
            "is_expired",
            "valid_from",
            "valid_until",
            "applicable_to_services",
            "applicable_to_products",
            "is_transferable",
            "recipient_name",
            "recipient_message",
            "purchased_at",
            "activated_at",
        ]

    def get_balance_percentage(self, obj):
        """Get remaining balance as percentage."""
        if obj.initial_amount:
            return round((obj.current_balance / obj.initial_amount) * 100, 1)
        return 0


class GiftCardDetailSerializer(GiftCardSerializer):
    """Detailed serializer including transactions."""

    transactions = serializers.SerializerMethodField()

    class Meta(GiftCardSerializer.Meta):
        fields = GiftCardSerializer.Meta.fields + ["transactions"]

    def get_transactions(self, obj):
        """Get recent transactions."""
        transactions = obj.transactions.order_by("-created_at")[:10]
        return GiftCardTransactionSerializer(transactions, many=True).data


class GiftCardPurchaseSerializer(serializers.Serializer):
    """Serializer for purchasing a gift card."""

    template_id = serializers.UUIDField()
    recipient_email = serializers.EmailField(required=False, allow_blank=True)
    recipient_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    recipient_message = serializers.CharField(required=False, allow_blank=True)
    payment_reference = serializers.CharField(max_length=100, required=False, default="")

    def validate_template_id(self, value):
        """Validate template exists and is active."""
        try:
            template = GiftCardTemplate.objects.get(id=value, is_active=True)
        except GiftCardTemplate.DoesNotExist:
            raise serializers.ValidationError("Invalid gift card template.")
        return value

    def create(self, validated_data):
        """Create a new gift card."""
        from datetime import timedelta

        template = GiftCardTemplate.objects.get(id=validated_data["template_id"])
        request = self.context.get("request")
        user = request.user if request and request.user.is_authenticated else None

        now = timezone.now()
        valid_until = now + timedelta(days=template.validity_days)

        gift_card = GiftCard.objects.create(
            template=template,
            initial_amount=template.amount,
            current_balance=template.amount,
            currency=template.currency,
            purchased_by=user,
            owner=user,
            recipient_email=validated_data.get("recipient_email", ""),
            recipient_name=validated_data.get("recipient_name", ""),
            recipient_message=validated_data.get("recipient_message", ""),
            country=template.country,
            applicable_to_services=template.applicable_to_services,
            applicable_to_products=template.applicable_to_products,
            valid_from=now,
            valid_until=valid_until,
            status=GiftCard.Status.ACTIVE,
            payment_reference=validated_data.get("payment_reference", ""),
            purchased_at=now,
            activated_at=now,
        )

        # Create purchase transaction
        GiftCardTransaction.objects.create(
            gift_card=gift_card,
            transaction_type=GiftCardTransaction.TransactionType.PURCHASE,
            amount=template.amount,
            balance_after=template.amount,
            user=user,
        )

        return gift_card


class GiftCardValidateSerializer(serializers.Serializer):
    """Serializer for validating a gift card."""

    code = serializers.CharField(max_length=50)
    pin = serializers.CharField(max_length=10, required=False, allow_blank=True)

    def validate(self, attrs):
        """Validate gift card code and PIN."""
        code = attrs.get("code")
        pin = attrs.get("pin", "")

        try:
            gift_card = GiftCard.objects.get(code__iexact=code)
        except GiftCard.DoesNotExist:
            raise serializers.ValidationError({"code": "Invalid gift card code."})

        if gift_card.pin and gift_card.pin != pin:
            raise serializers.ValidationError({"pin": "Invalid PIN."})

        if not gift_card.is_valid:
            if gift_card.is_expired:
                raise serializers.ValidationError({"code": "This gift card has expired."})
            elif gift_card.status == GiftCard.Status.FULLY_USED:
                raise serializers.ValidationError({"code": "This gift card has been fully used."})
            elif gift_card.status == GiftCard.Status.CANCELLED:
                raise serializers.ValidationError({"code": "This gift card has been cancelled."})
            else:
                raise serializers.ValidationError({"code": "This gift card is not valid."})

        attrs["gift_card"] = gift_card
        return attrs


class GiftCardRedeemSerializer(serializers.Serializer):
    """Serializer for redeeming a gift card."""

    code = serializers.CharField(max_length=50)
    pin = serializers.CharField(max_length=10, required=False, allow_blank=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    order_reference = serializers.CharField(max_length=100, required=False, default="")
    order_type = serializers.CharField(max_length=50, required=False, default="")

    def validate_amount(self, value):
        """Validate amount is positive."""
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive.")
        return value

    def validate(self, attrs):
        """Validate gift card and amount."""
        code = attrs.get("code")
        pin = attrs.get("pin", "")
        amount = attrs.get("amount")

        try:
            gift_card = GiftCard.objects.get(code__iexact=code)
        except GiftCard.DoesNotExist:
            raise serializers.ValidationError({"code": "Invalid gift card code."})

        if gift_card.pin and gift_card.pin != pin:
            raise serializers.ValidationError({"pin": "Invalid PIN."})

        if not gift_card.is_valid:
            raise serializers.ValidationError({"code": "This gift card is not valid."})

        if amount > gift_card.current_balance:
            raise serializers.ValidationError({
                "amount": f"Insufficient balance. Available: {gift_card.current_balance}"
            })

        attrs["gift_card"] = gift_card
        return attrs

    def create(self, validated_data):
        """Redeem the gift card."""
        gift_card = validated_data["gift_card"]
        amount = validated_data["amount"]
        order_reference = validated_data.get("order_reference", "")
        order_type = validated_data.get("order_type", "")

        request = self.context.get("request")
        user = request.user if request and request.user.is_authenticated else None

        success, redeemed, error = gift_card.redeem(
            amount=amount,
            user=user,
            order_reference=order_reference,
            order_type=order_type,
        )

        if not success:
            raise serializers.ValidationError({"amount": error})

        return {
            "gift_card": gift_card,
            "redeemed_amount": redeemed,
            "remaining_balance": gift_card.current_balance,
        }


class GiftCardTransferSerializer(serializers.Serializer):
    """Serializer for transferring a gift card."""

    code = serializers.CharField(max_length=50)
    new_owner_email = serializers.EmailField()

    def validate(self, attrs):
        """Validate gift card and new owner."""
        from django.contrib.auth import get_user_model
        User = get_user_model()

        code = attrs.get("code")
        new_owner_email = attrs.get("new_owner_email")

        try:
            gift_card = GiftCard.objects.get(code__iexact=code)
        except GiftCard.DoesNotExist:
            raise serializers.ValidationError({"code": "Invalid gift card code."})

        if not gift_card.is_transferable:
            raise serializers.ValidationError({"code": "This gift card cannot be transferred."})

        if not gift_card.is_valid:
            raise serializers.ValidationError({"code": "Cannot transfer an invalid gift card."})

        # Verify current owner
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            if gift_card.owner and gift_card.owner != request.user:
                raise serializers.ValidationError({"code": "You are not the owner of this gift card."})
        else:
            raise serializers.ValidationError({"code": "Authentication required."})

        # Find new owner
        try:
            new_owner = User.objects.get(email__iexact=new_owner_email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"new_owner_email": "User not found."})

        if new_owner == request.user:
            raise serializers.ValidationError({"new_owner_email": "Cannot transfer to yourself."})

        attrs["gift_card"] = gift_card
        attrs["new_owner"] = new_owner
        return attrs


class GiftCardTransactionSerializer(serializers.ModelSerializer):
    """Serializer for GiftCardTransaction model."""

    class Meta:
        model = GiftCardTransaction
        fields = [
            "id",
            "transaction_type",
            "amount",
            "balance_after",
            "order_reference",
            "order_type",
            "notes",
            "created_at",
        ]
        read_only_fields = fields


class GiftCardCheckBalanceSerializer(serializers.Serializer):
    """Serializer for checking gift card balance."""

    code = serializers.CharField(max_length=50)
    pin = serializers.CharField(max_length=10, required=False, allow_blank=True)

    def validate(self, attrs):
        """Validate gift card code."""
        code = attrs.get("code")
        pin = attrs.get("pin", "")

        try:
            gift_card = GiftCard.objects.get(code__iexact=code)
        except GiftCard.DoesNotExist:
            raise serializers.ValidationError({"code": "Invalid gift card code."})

        if gift_card.pin and gift_card.pin != pin:
            raise serializers.ValidationError({"pin": "Invalid PIN."})

        attrs["gift_card"] = gift_card
        return attrs
