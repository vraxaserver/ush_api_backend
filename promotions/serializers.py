"""
Promotions (Gift Cards & Loyalty Program) Serializers.
"""

from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from .models import (
    GiftCard,
    GiftCardTemplate,
    GiftCardTransaction,
    LoyaltyReward,
    LoyaltyTracker,
)


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
            "recipient_email",
            "recipient_phone",
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
    """Serializer for purchasing a gift card. Only template_id is required."""

    template_id = serializers.UUIDField()
    recipient_message = serializers.CharField(required=False, allow_blank=True)

    def validate_template_id(self, value):
        """Validate template exists and is active."""
        try:
            template = GiftCardTemplate.objects.get(id=value, is_active=True)
        except GiftCardTemplate.DoesNotExist:
            raise serializers.ValidationError("Invalid gift card template.")
        return value

    def create(self, validated_data):
        """Create a new gift card with owner as recipient."""
        from datetime import timedelta

        template = GiftCardTemplate.objects.get(id=validated_data["template_id"])
        request = self.context.get("request")
        user = request.user if request and request.user.is_authenticated else None

        now = timezone.now()
        valid_until = now + timedelta(days=template.validity_days)

        # Set recipient info from owner user
        recipient_name = ""
        recipient_email = ""
        recipient_phone = ""
        if user:
            recipient_name = user.get_full_name() or user.username
            recipient_email = user.email or ""
            recipient_phone = getattr(user, "phone_number", "") or ""
            if hasattr(recipient_phone, "as_e164"):
                recipient_phone = recipient_phone.as_e164

        gift_card = GiftCard.objects.create(
            template=template,
            initial_amount=template.amount,
            current_balance=template.amount,
            currency=template.currency,
            purchased_by=user,
            owner=user,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            recipient_phone=str(recipient_phone) if recipient_phone else "",
            recipient_message=validated_data.get("recipient_message", ""),
            country=template.country,
            applicable_to_services=template.applicable_to_services,
            applicable_to_products=template.applicable_to_products,
            valid_from=now,
            valid_until=valid_until,
            status=GiftCard.Status.ACTIVE,
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
    """Serializer for validating a gift card with applicability checks."""

    code = serializers.CharField(max_length=50)
    pin = serializers.CharField(max_length=10, required=False, allow_blank=True)
    is_for_service = serializers.BooleanField(required=False, default=False)
    is_for_product = serializers.BooleanField(required=False, default=False)
    country_id = serializers.UUIDField(required=False, allow_null=True)

    def validate(self, attrs):
        """Validate gift card code, PIN, and applicability."""
        code = attrs.get("code")
        pin = attrs.get("pin", "")
        is_for_service = attrs.get("is_for_service", False)
        is_for_product = attrs.get("is_for_product", False)
        country_id = attrs.get("country_id")

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

        # Check applicability for services
        if is_for_service and not gift_card.applicable_to_services:
            raise serializers.ValidationError({
                "code": "This gift card is not applicable to services."
            })

        # Check applicability for products
        if is_for_product and not gift_card.applicable_to_products:
            raise serializers.ValidationError({
                "code": "This gift card is not applicable to products."
            })

        # Check country restriction
        if country_id and gift_card.country_id:
            if str(gift_card.country_id) != str(country_id):
                raise serializers.ValidationError({
                    "code": f"This gift card is only valid in {gift_card.country.name if gift_card.country else 'a specific country'}."
                })

        attrs["gift_card"] = gift_card
        return attrs


class GiftCardRedeemSerializer(serializers.Serializer):
    """Serializer for redeeming a gift card with applicability checks."""

    code = serializers.CharField(max_length=50)
    pin = serializers.CharField(max_length=10, required=False, allow_blank=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    order_reference = serializers.CharField(max_length=100, required=False, default="")
    order_type = serializers.CharField(max_length=50, required=False, default="")
    is_for_service = serializers.BooleanField(required=False, default=False)
    is_for_product = serializers.BooleanField(required=False, default=False)
    country_id = serializers.UUIDField(required=False, allow_null=True)

    def validate_amount(self, value):
        """Validate amount is positive."""
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive.")
        return value

    def validate(self, attrs):
        """Validate gift card, amount, and applicability."""
        code = attrs.get("code")
        pin = attrs.get("pin", "")
        amount = attrs.get("amount")
        is_for_service = attrs.get("is_for_service", False)
        is_for_product = attrs.get("is_for_product", False)
        country_id = attrs.get("country_id")

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

        # Check applicability for services
        if is_for_service and not gift_card.applicable_to_services:
            raise serializers.ValidationError({
                "code": "This gift card is not applicable to services."
            })

        # Check applicability for products
        if is_for_product and not gift_card.applicable_to_products:
            raise serializers.ValidationError({
                "code": "This gift card is not applicable to products."
            })

        # Check country restriction
        if country_id and gift_card.country_id:
            if str(gift_card.country_id) != str(country_id):
                raise serializers.ValidationError({
                    "code": f"This gift card is only valid in {gift_card.country.name if gift_card.country else 'a specific country'}."
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
    """
    Serializer for transferring a gift card.
    
    Requires gift_card_id and either recipient_email or recipient_phone.
    If recipient doesn't exist, creates a new customer account.
    """

    gift_card_id = serializers.UUIDField()
    recipient_email = serializers.EmailField(required=False, allow_blank=True)
    recipient_phone = serializers.CharField(max_length=20, required=False, allow_blank=True)

    def validate(self, attrs):
        """Validate gift card and find or create recipient."""
        import secrets
        import string
        from django.contrib.auth import get_user_model
        
        User = get_user_model()

        gift_card_id = attrs.get("gift_card_id")
        recipient_email = attrs.get("recipient_email", "").strip()
        recipient_phone = attrs.get("recipient_phone", "").strip()

        # Require at least one of email or phone
        if not recipient_email and not recipient_phone:
            raise serializers.ValidationError({
                "recipient_email": "At least one of recipient_email or recipient_phone is required.",
            })

        # Validate gift card
        try:
            gift_card = GiftCard.objects.get(id=gift_card_id)
        except GiftCard.DoesNotExist:
            raise serializers.ValidationError({"gift_card_id": "Invalid gift card ID."})

        if not gift_card.is_transferable:
            raise serializers.ValidationError({"gift_card_id": "This gift card cannot be transferred."})

        if not gift_card.is_valid:
            raise serializers.ValidationError({"gift_card_id": "Cannot transfer an invalid gift card."})

        # Verify current owner
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            if gift_card.owner and gift_card.owner != request.user:
                raise serializers.ValidationError({"gift_card_id": "You are not the owner of this gift card."})
        else:
            raise serializers.ValidationError({"gift_card_id": "Authentication required."})

        # Find existing user by email or phone
        new_owner = None
        is_new_user = False
        generated_password = None

        if recipient_email:
            try:
                new_owner = User.objects.get(email__iexact=recipient_email)
            except User.DoesNotExist:
                pass

        if not new_owner and recipient_phone:
            # Try to find user by phone number
            try:
                from phonenumber_field.phonenumber import PhoneNumber
                phone_obj = PhoneNumber.from_string(recipient_phone)
                new_owner = User.objects.get(phone_number=phone_obj)
            except Exception:
                try:
                    new_owner = User.objects.get(phone_number=recipient_phone)
                except User.DoesNotExist:
                    pass

        # If no user found, create a new customer
        if not new_owner:
            # Generate random password
            alphabet = string.ascii_letters + string.digits
            generated_password = ''.join(secrets.choice(alphabet) for _ in range(12))

            user_data = {
                "first_name": "Customer",
                "last_name": "",
                "user_type": "customer",
                "is_active": True,
            }

            if recipient_email:
                user_data["email"] = recipient_email
            if recipient_phone:
                try:
                    from phonenumber_field.phonenumber import PhoneNumber
                    phone_obj = PhoneNumber.from_string(recipient_phone)
                    user_data["phone_number"] = phone_obj
                except Exception:
                    user_data["phone_number"] = recipient_phone

            new_owner = User.objects.create_user(
                password=generated_password,
                **user_data
            )
            is_new_user = True

        # Cannot transfer to yourself
        if new_owner == request.user:
            raise serializers.ValidationError({
                "recipient_email": "Cannot transfer to yourself.",
            })

        attrs["gift_card"] = gift_card
        attrs["new_owner"] = new_owner
        attrs["is_new_user"] = is_new_user
        attrs["generated_password"] = generated_password
        attrs["recipient_email"] = recipient_email
        attrs["recipient_phone"] = recipient_phone
        return attrs

    def create(self, validated_data):
        """Transfer the gift card to new owner and update recipient info."""
        gift_card = validated_data["gift_card"]
        new_owner = validated_data["new_owner"]
        is_new_user = validated_data["is_new_user"]
        generated_password = validated_data.get("generated_password")
        request = self.context.get("request")
        old_owner = gift_card.owner

        # Transfer ownership
        gift_card.owner = new_owner
        
        # Update recipient info from new owner
        gift_card.recipient_name = new_owner.get_full_name() or new_owner.username
        gift_card.recipient_email = new_owner.email or ""
        recipient_phone = getattr(new_owner, "phone_number", "") or ""
        if hasattr(recipient_phone, "as_e164"):
            recipient_phone = recipient_phone.as_e164
        gift_card.recipient_phone = str(recipient_phone) if recipient_phone else ""
        gift_card.save()

        # Create transfer transaction
        GiftCardTransaction.objects.create(
            gift_card=gift_card,
            transaction_type=GiftCardTransaction.TransactionType.TRANSFER,
            amount=0,
            balance_after=gift_card.current_balance,
            user=request.user if request else None,
            notes=f"Transferred from {old_owner.email if old_owner else 'Unknown'} to {new_owner.email or new_owner.username}",
        )

        # Send notification to new user if they were just created
        if is_new_user and generated_password:
            # TODO: Send email or SMS with login credentials
            pass

        return {
            "gift_card": gift_card,
            "new_owner": new_owner,
            "is_new_user": is_new_user,
            "generated_password": generated_password if is_new_user else None,
        }



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


# =============================================================================
# Loyalty Program Serializers
# =============================================================================

class LoyaltyTrackerSerializer(serializers.ModelSerializer):
    """Serializer for LoyaltyTracker – shows progress per service."""

    service_name = serializers.CharField(source="service.name", read_only=True)
    service_id = serializers.UUIDField(source="service.id", read_only=True)
    progress_percentage = serializers.FloatField(read_only=True)
    bookings_remaining = serializers.IntegerField(read_only=True)

    class Meta:
        model = LoyaltyTracker
        fields = [
            "id",
            "service_id",
            "service_name",
            "booking_count",
            "bookings_required",
            "bookings_remaining",
            "progress_percentage",
            "total_bookings",
            "total_rewards_earned",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class LoyaltyRewardSerializer(serializers.ModelSerializer):
    """Serializer for LoyaltyReward – shows earned free-booking rewards."""

    service_name = serializers.CharField(source="service.name", read_only=True)
    service_id = serializers.UUIDField(source="service.id", read_only=True)
    is_available = serializers.BooleanField(read_only=True)

    class Meta:
        model = LoyaltyReward
        fields = [
            "id",
            "service_id",
            "service_name",
            "status",
            "is_available",
            "earned_from_booking",
            "redeemed_in_booking",
            "redeemed_at",
            "expires_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class LoyaltyRedeemSerializer(serializers.Serializer):
    """Serializer for redeeming a loyalty reward."""

    reward_id = serializers.UUIDField()
    booking_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="Optional: Link this reward to a specific free booking.",
    )

    def validate_reward_id(self, value):
        """Ensure the reward exists and belongs to the current user."""
        request = self.context.get("request")
        try:
            reward = LoyaltyReward.objects.select_related("service").get(id=value)
        except LoyaltyReward.DoesNotExist:
            raise serializers.ValidationError("Loyalty reward not found.")

        if request and request.user.is_authenticated:
            if reward.customer != request.user:
                raise serializers.ValidationError("This reward does not belong to you.")

        if not reward.is_available:
            if reward.status == LoyaltyReward.RewardStatus.REDEEMED:
                raise serializers.ValidationError("This reward has already been redeemed.")
            elif reward.status == LoyaltyReward.RewardStatus.EXPIRED:
                raise serializers.ValidationError("This reward has expired.")
            elif reward.status == LoyaltyReward.RewardStatus.CANCELLED:
                raise serializers.ValidationError("This reward has been cancelled.")
            else:
                raise serializers.ValidationError("This reward is no longer available.")

        return value

    def validate(self, attrs):
        reward = LoyaltyReward.objects.select_related("service").get(id=attrs["reward_id"])
        attrs["reward"] = reward

        booking_id = attrs.get("booking_id")
        if booking_id:
            from bookings.models import Booking
            try:
                booking = Booking.objects.get(id=booking_id)
                attrs["booking"] = booking
            except Booking.DoesNotExist:
                raise serializers.ValidationError({"booking_id": "Booking not found."})
        else:
            attrs["booking"] = None

        return attrs

    def create(self, validated_data):
        """Redeem the loyalty reward."""
        reward = validated_data["reward"]
        booking = validated_data.get("booking")

        success, error = reward.redeem(booking=booking)
        if not success:
            raise serializers.ValidationError({"reward_id": str(error)})

        return reward

