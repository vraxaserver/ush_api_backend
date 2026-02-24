"""
Promotions (Gift Cards) Views.
"""

from django.db.models import Sum
from django_filters import rest_framework as django_filters
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    GiftCard,
    GiftCardTemplate,
    GiftCardTransaction,
)
from .serializers import (
    GiftCardCheckBalanceSerializer,
    GiftCardDetailSerializer,
    GiftCardPurchaseSerializer,
    GiftCardRedeemSerializer,
    GiftCardSerializer,
    GiftCardTemplateSerializer,
    GiftCardTransactionSerializer,
    GiftCardTransferSerializer,
    GiftCardValidateSerializer,
)


# =============================================================================
# Gift Card Views
# =============================================================================

class GiftCardTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for GiftCardTemplate (Read Only).
    
    Public listing of available gift card options.
    """

    queryset = GiftCardTemplate.objects.filter(is_active=True)
    serializer_class = GiftCardTemplateSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.OrderingFilter,
    ]
    filterset_fields = ["currency", "country"]
    ordering_fields = ["amount", "sort_order"]
    ordering = ["sort_order", "amount"]


class GiftCardViewSet(viewsets.ModelViewSet):
    """
    ViewSet for GiftCard.
    
    - List: User's owned gift cards
    - Retrieve: Get gift card details
    - Create: Purchase a new gift card
    - Custom actions: validate, redeem, transfer, check_balance
    """

    serializer_class = GiftCardSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.OrderingFilter,
    ]
    filterset_fields = ["status", "currency"]
    ordering_fields = ["created_at", "valid_until", "current_balance"]
    ordering = ["-created_at"]

    def get_queryset(self):
        """Return user's owned gift cards."""
        return GiftCard.objects.filter(owner=self.request.user)

    def get_serializer_class(self):
        if self.action == "retrieve":
            return GiftCardDetailSerializer
        elif self.action == "create":
            return GiftCardPurchaseSerializer
        return GiftCardSerializer

    def create(self, request, *args, **kwargs):
        """Purchase a new gift card."""
        serializer = GiftCardPurchaseSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        gift_card = serializer.save()

        return Response(
            GiftCardSerializer(gift_card).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"])
    def buy(self, request):
        """
        Buy/purchase a new gift card.
        
        Request body:
        - template_id: UUID of the gift card template
        - recipient_message: (optional) Personal message
        
        The authenticated user becomes both the purchaser and owner.
        Recipient info is automatically set from the owner's profile.
        """
        serializer = GiftCardPurchaseSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        gift_card = serializer.save()

        return Response(
            {
                "success": True,
                "message": "Gift card purchased successfully.",
                "gift_card": GiftCardSerializer(gift_card).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], permission_classes=[permissions.AllowAny])
    def validate(self, request):
        """
        Validate a gift card code.
        
        Request body:
        - code: Gift card code
        - pin: (optional) Security PIN
        - is_for_service: (optional) True if using for a service
        - is_for_product: (optional) True if using for a product
        - country_id: (optional) UUID of country to check restriction
        
        Returns gift card details if valid.
        """
        serializer = GiftCardValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        gift_card = serializer.validated_data["gift_card"]
        return Response(GiftCardSerializer(gift_card).data)

    @action(detail=False, methods=["post"], permission_classes=[permissions.AllowAny])
    def check_balance(self, request):
        """
        Check gift card balance.
        
        Request body:
        - code: Gift card code
        - pin: (optional) Security PIN
        
        Returns balance information.
        """
        serializer = GiftCardCheckBalanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        gift_card = serializer.validated_data["gift_card"]
        return Response({
            "code": gift_card.code,
            "initial_amount": str(gift_card.initial_amount),
            "current_balance": str(gift_card.current_balance),
            "used_amount": str(gift_card.used_amount),
            "currency": gift_card.currency,
            "status": gift_card.status,
            "is_valid": gift_card.is_valid,
            "valid_until": gift_card.valid_until,
        })

    @action(detail=False, methods=["post"])
    def redeem(self, request):
        """
        Redeem amount from gift card.
        
        Request body:
        - code: Gift card code
        - pin: (optional) Security PIN
        - amount: Amount to redeem
        - order_reference: (optional) Order/booking reference
        - order_type: (optional) Type of order
        - is_for_service: (optional) True if redeeming for a service
        - is_for_product: (optional) True if redeeming for a product
        - country_id: (optional) UUID of country to check restriction
        
        Returns redemption details.
        """
        serializer = GiftCardRedeemSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        return Response({
            "success": True,
            "code": result["gift_card"].code,
            "redeemed_amount": str(result["redeemed_amount"]),
            "remaining_balance": str(result["remaining_balance"]),
            "currency": result["gift_card"].currency,
        })

    @action(detail=False, methods=["post"])
    def transfer(self, request):
        """
        Transfer gift card to another user.
        
        Request body:
        - gift_card_id: UUID of the gift card
        - recipient_email: (optional) Email of recipient
        - recipient_phone: (optional) Phone number of recipient
        
        At least one of recipient_email or recipient_phone is required.
        If user doesn't exist, a new customer account will be created
        and login details will be sent via email/SMS.
        
        Returns updated gift card details.
        """
        serializer = GiftCardTransferSerializer(
            data=request.data,
            context={"request": request},
        )
        
        if not serializer.is_valid():
            errors = serializer.errors
            error_message = next(iter(errors.values()))[0] if errors else "Invalid request."
            return Response(
                {"status": "error", "message": str(error_message), "errors": errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = serializer.save()
        gift_card = result["gift_card"]
        new_owner = result["new_owner"]
        is_new_user = result["is_new_user"]
        generated_password = result.get("generated_password")

        # Send notification to new users
        if is_new_user and generated_password:
            try:
                from .tasks import send_gift_card_welcome_email, send_gift_card_welcome_sms

                # Send email notification
                if new_owner.email:
                    send_gift_card_welcome_email.delay(
                        email=new_owner.email,
                        first_name=new_owner.first_name,
                        password=generated_password,
                        gift_card_code=gift_card.code,
                        gift_card_amount=str(gift_card.current_balance),
                        gift_card_currency=gift_card.currency,
                        sender_name=request.user.get_full_name() or str(request.user),
                        message="",
                    )

                # Send SMS notification
                if hasattr(new_owner, 'phone_number') and new_owner.phone_number:
                    send_gift_card_welcome_sms.delay(
                        phone_number=str(new_owner.phone_number),
                        first_name=new_owner.first_name,
                        password=generated_password,
                        gift_card_amount=str(gift_card.current_balance),
                        gift_card_currency=gift_card.currency,
                    )
            except ImportError:
                # Tasks module not available, skip notifications
                pass

        # Build response message
        recipient_identifier = new_owner.email or str(getattr(new_owner, 'phone_number', '')) or str(new_owner.id)
        response_message = f"Gift card transferred to {recipient_identifier}"
        if is_new_user:
            response_message += " (new account created)"

        return Response({
            "status": "success",
            "message": response_message,
            "is_new_user": is_new_user,
            "gift_card": GiftCardSerializer(gift_card).data,
        })

    @action(detail=True, methods=["get"])
    def transactions(self, request, pk=None):
        """
        Get transaction history for a gift card.
        """
        gift_card = self.get_object()
        transactions = gift_card.transactions.order_by("-created_at")

        page = self.paginate_queryset(transactions)
        if page is not None:
            serializer = GiftCardTransactionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = GiftCardTransactionSerializer(transactions, many=True)
        return Response(serializer.data)


class GiftCardTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for GiftCardTransaction (Read Only).
    
    Users can see transactions for their owned gift cards.
    """

    serializer_class = GiftCardTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.OrderingFilter,
    ]
    filterset_fields = ["transaction_type", "gift_card"]
    ordering_fields = ["created_at", "amount"]
    ordering = ["-created_at"]

    def get_queryset(self):
        """Return transactions for user's gift cards."""
        return GiftCardTransaction.objects.filter(
            gift_card__owner=self.request.user
        )


# =============================================================================
# Combined Payment View (Gift Card)
# =============================================================================

class ApplyDiscountsView(APIView):
    """
    Apply gift card to an order.
    
    This is a convenience endpoint that calculates total discounts
    from a gift card.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
        Calculate discounts from gift card.
        
        Request body:
        - amount: Original order amount
        - gift_card_code: (optional) Gift card code to apply
        - gift_card_pin: (optional) Gift card PIN
        - gift_card_amount: (optional) Amount to use from gift card
        
        Returns breakdown of discounts.
        """
        from decimal import Decimal

        amount = Decimal(str(request.data.get("amount", 0)))
        gift_card_code = request.data.get("gift_card_code")
        gift_card_pin = request.data.get("gift_card_pin", "")
        gift_card_amount = request.data.get("gift_card_amount")

        if amount <= 0:
            return Response(
                {"error": "Invalid amount."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = {
            "original_amount": str(amount),
            "gift_card_amount": "0.00",
            "final_amount": str(amount),
            "gift_card": None,
        }

        remaining = amount

        # Apply gift card
        if gift_card_code:
            try:
                gift_card = GiftCard.objects.get(code__iexact=gift_card_code)
                
                if gift_card.pin and gift_card.pin != gift_card_pin:
                    result["gift_card_error"] = "Invalid PIN."
                elif not gift_card.is_valid:
                    result["gift_card_error"] = "Gift card is not valid."
                else:
                    # Determine amount to use
                    if gift_card_amount:
                        gc_amount = min(
                            Decimal(str(gift_card_amount)),
                            gift_card.current_balance,
                            remaining,
                        )
                    else:
                        gc_amount = min(gift_card.current_balance, remaining)

                    remaining -= gc_amount
                    result["gift_card_amount"] = str(gc_amount)
                    result["gift_card"] = {
                        "code": gift_card.code,
                        "balance_before": str(gift_card.current_balance),
                        "balance_after": str(gift_card.current_balance - gc_amount),
                    }
            except GiftCard.DoesNotExist:
                result["gift_card_error"] = "Invalid gift card code."

        result["final_amount"] = str(max(Decimal("0"), remaining))
        
        return Response(result)
