"""
Promotions (Vouchers & Gift Cards) Views.
"""

from django.db import models
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
    Voucher,
    VoucherUsage,
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
    VoucherApplySerializer,
    VoucherSerializer,
    VoucherUsageSerializer,
    VoucherValidateSerializer,
)


# =============================================================================
# Voucher Views
# =============================================================================

class VoucherFilter(django_filters.FilterSet):
    """Filter for Voucher model."""

    status = django_filters.CharFilter(field_name="status")
    applicable_to = django_filters.CharFilter(field_name="applicable_to")
    country = django_filters.UUIDFilter(field_name="country__id")
    country_code = django_filters.CharFilter(
        field_name="country__code",
        lookup_expr="iexact",
    )
    is_valid = django_filters.BooleanFilter(method="filter_is_valid")

    class Meta:
        model = Voucher
        fields = ["status", "applicable_to", "country", "country_code"]

    def filter_is_valid(self, queryset, name, value):
        """Filter by current validity."""
        from django.utils import timezone
        now = timezone.now()

        if value:
            return queryset.filter(
                status=Voucher.Status.ACTIVE,
                valid_from__lte=now,
                valid_until__gte=now,
            ).exclude(
                max_uses__isnull=False,
                current_uses__gte=models.F("max_uses"),
            )
        return queryset


class VoucherViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Voucher (Read Only).
    
    Public vouchers can be listed.
    Use validate/apply endpoints to use vouchers.
    """

    queryset = Voucher.objects.filter(status=Voucher.Status.ACTIVE)
    serializer_class = VoucherSerializer
    permission_classes = [permissions.AllowAny]
    filterset_class = VoucherFilter
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = ["code", "name", "description"]
    ordering_fields = ["created_at", "valid_until", "discount_value"]
    ordering = ["-created_at"]

    @action(detail=False, methods=["post"])
    def validate(self, request):
        """
        Validate a voucher code.
        
        Request body:
        - code: Voucher code
        - amount: (optional) Order amount to check minimum purchase
        
        Returns voucher details if valid.
        """
        serializer = VoucherValidateSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        voucher = serializer.validated_data["voucher"]
        amount = serializer.validated_data.get("amount")

        response_data = VoucherSerializer(voucher).data
        if amount:
            response_data["calculated_discount"] = voucher.calculate_discount(amount)
            response_data["final_amount"] = amount - voucher.calculate_discount(amount)

        return Response(response_data)

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def apply(self, request):
        """
        Apply a voucher to an order.
        
        Request body:
        - code: Voucher code
        - amount: Order amount
        - order_reference: (optional) Order/booking reference
        - order_type: (optional) Type of order
        
        Creates a usage record and returns discount details.
        """
        serializer = VoucherApplySerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        usage = serializer.save()

        return Response({
            "success": True,
            "voucher_code": usage.voucher.code,
            "original_amount": str(usage.original_amount),
            "discount_amount": str(usage.discount_amount),
            "final_amount": str(usage.final_amount),
            "usage_id": str(usage.id),
        }, status=status.HTTP_201_CREATED)


class VoucherUsageViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for VoucherUsage (Read Only).
    
    Users can see their own voucher usage history.
    """

    serializer_class = VoucherUsageSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["used_at"]
    ordering = ["-used_at"]

    def get_queryset(self):
        """Return only current user's usage."""
        return VoucherUsage.objects.filter(user=self.request.user)


class MyVouchersListView(APIView):
    """
    List all valid vouchers for the current authenticated user.
    
    Returns vouchers that:
    - Are currently active
    - Are within their validity period
    - Have not exceeded total usage limits
    - The user has not exceeded their per-user usage limit
    
    Supports pagination with query params:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 10, max: 100)
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get all valid vouchers for the current user with pagination."""
        from django.utils import timezone
        from rest_framework.pagination import PageNumberPagination

        now = timezone.now()
        user = request.user

        # Get vouchers that are valid (active, within date range, not exhausted)
        vouchers = Voucher.objects.filter(
            status=Voucher.Status.ACTIVE,
            valid_from__lte=now,
            valid_until__gte=now,
        ).exclude(
            # Exclude vouchers where max_uses is set and current_uses >= max_uses
            max_uses__isnull=False,
            current_uses__gte=models.F("max_uses"),
        )

        # Filter out vouchers where the user has reached their per-user limit
        valid_vouchers = []
        for voucher in vouchers:
            user_uses = voucher.usages.filter(user=user).count()
            if user_uses < voucher.max_uses_per_user:
                valid_vouchers.append(voucher)

        # Apply pagination
        paginator = PageNumberPagination()
        paginator.page_size = 10
        paginator.page_size_query_param = "page_size"
        paginator.max_page_size = 100

        paginated_vouchers = paginator.paginate_queryset(valid_vouchers, request)
        serializer = VoucherSerializer(paginated_vouchers, many=True)
        return paginator.get_paginated_response(serializer.data)


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

    @action(detail=False, methods=["post"], permission_classes=[permissions.AllowAny])
    def validate(self, request):
        """
        Validate a gift card code.
        
        Request body:
        - code: Gift card code
        - pin: (optional) Security PIN
        
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
        - code: Gift card code
        - recipient_email: (optional) Email of recipient
        - recipient_phone: (optional) Phone number of recipient
        - recipient_name: (optional) Name of recipient
        - message: (optional) Custom message for recipient
        
        At least one of recipient_email or recipient_phone is required.
        If user doesn't exist, a new customer account will be created.
        
        Returns updated gift card details.
        """
        serializer = GiftCardTransferSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        gift_card = serializer.validated_data["gift_card"]
        new_owner = serializer.validated_data["new_owner"]
        is_new_user = serializer.validated_data.get("is_new_user", False)
        generated_password = serializer.validated_data.get("generated_password")
        recipient_name = serializer.validated_data.get("recipient_name", "")
        message = serializer.validated_data.get("message", "")

        # Transfer ownership
        success, error = gift_card.transfer_to(new_owner)
        if not success:
            return Response(
                {"error": error},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update recipient fields on gift card
        update_fields = []
        if recipient_name:
            gift_card.recipient_name = recipient_name
            update_fields.append("recipient_name")
        if message:
            gift_card.recipient_message = message
            update_fields.append("recipient_message")
        if update_fields:
            gift_card.save(update_fields=update_fields)

        # Send notification to new users
        if is_new_user and generated_password:
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
                    message=message,
                )

            # Send SMS notification
            if new_owner.phone_number:
                send_gift_card_welcome_sms.delay(
                    phone_number=str(new_owner.phone_number),
                    first_name=new_owner.first_name,
                    password=generated_password,
                    gift_card_amount=str(gift_card.current_balance),
                    gift_card_currency=gift_card.currency,
                )

        # Build response message
        recipient_identifier = new_owner.email or str(new_owner.phone_number) or str(new_owner.id)
        response_message = f"Gift card transferred to {recipient_identifier}"
        if is_new_user:
            response_message += " (new account created)"

        return Response({
            "success": True,
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
# Combined Payment View (Voucher + Gift Card)
# =============================================================================

class ApplyDiscountsView(APIView):
    """
    Apply both voucher and gift card to an order.
    
    This is a convenience endpoint that calculates total discounts
    from both voucher and gift card.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
        Calculate discounts from voucher and/or gift card.
        
        Request body:
        - amount: Original order amount
        - voucher_code: (optional) Voucher code to apply
        - gift_card_code: (optional) Gift card code to apply
        - gift_card_pin: (optional) Gift card PIN
        - gift_card_amount: (optional) Amount to use from gift card
        
        Returns breakdown of discounts.
        """
        from decimal import Decimal

        amount = Decimal(str(request.data.get("amount", 0)))
        voucher_code = request.data.get("voucher_code")
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
            "voucher_discount": "0.00",
            "gift_card_amount": "0.00",
            "final_amount": str(amount),
            "voucher": None,
            "gift_card": None,
        }

        remaining = amount

        # Apply voucher first
        if voucher_code:
            try:
                voucher = Voucher.objects.get(code__iexact=voucher_code)
                can_use, error = voucher.can_be_used_by(request.user, amount)
                
                if can_use:
                    discount = voucher.calculate_discount(amount)
                    remaining -= discount
                    result["voucher_discount"] = str(discount)
                    result["voucher"] = {
                        "code": voucher.code,
                        "discount_type": voucher.discount_type,
                        "discount_value": str(voucher.discount_value),
                    }
                else:
                    result["voucher_error"] = error
            except Voucher.DoesNotExist:
                result["voucher_error"] = "Invalid voucher code."

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
