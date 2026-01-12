"""
Seed Promotions (Vouchers and Gift Cards).

Creates demo vouchers and gift card templates.
Requires: seed_locations to be run first.

Usage:
    python manage.py seed_promotions
    python manage.py seed_promotions --clear
"""

from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from spacenter.models import Country
from promotions.models import GiftCard, GiftCardTemplate, GiftCardTransaction, Voucher


# Demo vouchers
VOUCHERS_DATA = [
    {
        "code": "WELCOME10",
        "name": "Welcome 10% Off",
        "description": "10% off for new customers",
        "discount_type": "percentage",
        "discount_value": Decimal("10.00"),
        "max_discount_amount": Decimal("50.00"),
        "applicable_to": "all",
        "minimum_purchase": Decimal("50.00"),
        "max_uses": 1000,
        "max_uses_per_user": 1,
        "first_time_only": True,
        "validity_days": 365,
    },
    {
        "code": "SUMMER25",
        "name": "Summer Sale 25% Off",
        "description": "25% off on all services during summer",
        "discount_type": "percentage",
        "discount_value": Decimal("25.00"),
        "max_discount_amount": Decimal("100.00"),
        "applicable_to": "services",
        "minimum_purchase": Decimal("100.00"),
        "max_uses": 500,
        "max_uses_per_user": 3,
        "first_time_only": False,
        "validity_days": 90,
    },
    {
        "code": "PRODUCT15",
        "name": "Product Discount 15%",
        "description": "15% off on all spa products",
        "discount_type": "percentage",
        "discount_value": Decimal("15.00"),
        "max_discount_amount": None,
        "applicable_to": "products",
        "minimum_purchase": Decimal("75.00"),
        "max_uses": None,
        "max_uses_per_user": 5,
        "first_time_only": False,
        "validity_days": 180,
    },
    {
        "code": "FLAT50",
        "name": "Flat 50 QAR Off",
        "description": "Fixed 50 QAR discount on orders above 200 QAR",
        "discount_type": "fixed",
        "discount_value": Decimal("50.00"),
        "max_discount_amount": None,
        "applicable_to": "all",
        "minimum_purchase": Decimal("200.00"),
        "max_uses": 200,
        "max_uses_per_user": 2,
        "first_time_only": False,
        "validity_days": 60,
    },
    {
        "code": "VIP100",
        "name": "VIP 100 QAR Off",
        "description": "Exclusive VIP discount - 100 QAR off",
        "discount_type": "fixed",
        "discount_value": Decimal("100.00"),
        "max_discount_amount": None,
        "applicable_to": "services",
        "minimum_purchase": Decimal("300.00"),
        "max_uses": 50,
        "max_uses_per_user": 1,
        "first_time_only": False,
        "validity_days": 30,
    },
    {
        "code": "AROMATHERAPY20",
        "name": "Aromatherapy Special",
        "description": "20% off on aromatherapy products",
        "discount_type": "percentage",
        "discount_value": Decimal("20.00"),
        "max_discount_amount": Decimal("75.00"),
        "applicable_to": "specific",
        "specific_categories": "Aromatherapy,Oils",
        "minimum_purchase": Decimal("50.00"),
        "max_uses": 300,
        "max_uses_per_user": 2,
        "first_time_only": False,
        "validity_days": 120,
    },
]

# Gift card templates
GIFT_CARD_TEMPLATES_DATA = [
    {
        "name": "Classic Gift Card",
        "description": "A perfect gift for any occasion",
        "amount": Decimal("100.00"),
        "validity_days": 365,
        "applicable_to_services": True,
        "applicable_to_products": True,
    },
    {
        "name": "Premium Gift Card",
        "description": "Treat someone special to a luxurious spa experience",
        "amount": Decimal("250.00"),
        "validity_days": 365,
        "applicable_to_services": True,
        "applicable_to_products": True,
    },
    {
        "name": "Deluxe Gift Card",
        "description": "The ultimate spa gift for complete relaxation",
        "amount": Decimal("500.00"),
        "validity_days": 365,
        "applicable_to_services": True,
        "applicable_to_products": True,
    },
    {
        "name": "Services Only Gift Card",
        "description": "Gift a spa service experience",
        "amount": Decimal("200.00"),
        "validity_days": 180,
        "applicable_to_services": True,
        "applicable_to_products": False,
    },
    {
        "name": "Product Gift Card",
        "description": "Gift premium spa products",
        "amount": Decimal("150.00"),
        "validity_days": 180,
        "applicable_to_services": False,
        "applicable_to_products": True,
    },
    {
        "name": "Mini Gift Card",
        "description": "A small token of appreciation",
        "amount": Decimal("50.00"),
        "validity_days": 90,
        "applicable_to_services": True,
        "applicable_to_products": True,
    },
]


class Command(BaseCommand):
    help = "Seed promotions (vouchers and gift card templates)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing promotion data before seeding",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.clear_data()

        with transaction.atomic():
            self.stdout.write("🎟️ Seeding vouchers...")
            vouchers = self.create_vouchers()

            self.stdout.write("🎁 Seeding gift card templates...")
            templates = self.create_gift_card_templates()

            self.stdout.write(self.style.SUCCESS(
                f"\n✅ Promotions seeded: {len(vouchers)} vouchers, {len(templates)} gift card templates"
            ))

            self.print_summary()

    def clear_data(self):
        """Clear existing data."""
        self.stdout.write(self.style.WARNING("⚠️ Clearing promotions..."))
        GiftCardTransaction.objects.all().delete()
        GiftCard.objects.all().delete()
        GiftCardTemplate.objects.all().delete()
        Voucher.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("✓ Promotions cleared"))

    def create_vouchers(self):
        """Create demo vouchers."""
        vouchers = []
        now = timezone.now()

        for data in VOUCHERS_DATA:
            valid_from = now
            valid_until = now + timedelta(days=data.pop("validity_days"))
            specific_categories = data.pop("specific_categories", "")

            voucher, created = Voucher.objects.update_or_create(
                code=data["code"],
                defaults={
                    **data,
                    "valid_from": valid_from,
                    "valid_until": valid_until,
                    "specific_categories": specific_categories,
                    "status": Voucher.Status.ACTIVE,
                },
            )
            vouchers.append(voucher)
            action = "Created" if created else "Updated"
            self.stdout.write(f"  {action}: {voucher.code} - {voucher.name}")

        return vouchers

    def create_gift_card_templates(self):
        """Create gift card templates."""
        templates = []

        # Get first country for templates (or None for global)
        country = Country.objects.first()

        for idx, data in enumerate(GIFT_CARD_TEMPLATES_DATA):
            template, created = GiftCardTemplate.objects.update_or_create(
                name=data["name"],
                defaults={
                    **data,
                    "currency": "QAR",
                    "country": None,  # Global availability
                    "sort_order": idx,
                    "is_active": True,
                },
            )
            templates.append(template)
            action = "Created" if created else "Updated"
            self.stdout.write(f"  {action}: {template.name} - {template.currency} {template.amount}")

        return templates

    def print_summary(self):
        """Print summary of seeded data."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("📊 VOUCHERS & GIFT CARDS SUMMARY")
        self.stdout.write("=" * 60)

        self.stdout.write(f"\n  🎟️ Vouchers:")
        for voucher in Voucher.objects.all():
            discount = f"{voucher.discount_value}%"
            if voucher.discount_type == Voucher.DiscountType.FIXED:
                discount = f"{voucher.discount_value} Fixed"
            self.stdout.write(
                f"    {voucher.code}: {discount} ({voucher.applicable_to})"
            )

        self.stdout.write(f"\n  🎁 Gift Card Templates:")
        for template in GiftCardTemplate.objects.all():
            self.stdout.write(
                f"    {template.name}: {template.currency} {template.amount}"
            )

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("🔗 API ENDPOINTS")
        self.stdout.write("=" * 60)
        self.stdout.write("\n  Vouchers:")
        self.stdout.write("    GET  /api/v1/promotions/vouchers/")
        self.stdout.write("    POST /api/v1/promotions/vouchers/validate/")
        self.stdout.write("    POST /api/v1/promotions/vouchers/apply/")
        self.stdout.write("\n  Gift Cards:")
        self.stdout.write("    GET  /api/v1/promotions/gift-card-templates/")
        self.stdout.write("    GET  /api/v1/promotions/gift-cards/")
        self.stdout.write("    POST /api/v1/promotions/gift-cards/")
        self.stdout.write("    POST /api/v1/promotions/gift-cards/validate/")
        self.stdout.write("    POST /api/v1/promotions/gift-cards/check_balance/")
        self.stdout.write("    POST /api/v1/promotions/gift-cards/redeem/")
        self.stdout.write("    POST /api/v1/promotions/gift-cards/transfer/")
        self.stdout.write("\n  Combined:")
        self.stdout.write("    POST /api/v1/promotions/apply-discounts/")

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("✅ PROMOTIONS SEED COMPLETE!"))
        self.stdout.write("=" * 60 + "\n")
