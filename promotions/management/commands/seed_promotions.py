"""
Seed promotions: GiftCardTemplates and GiftCards for all countries.

Depends on: seed_users, seed_spacenter.
"""

from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User, UserType
from promotions.models import (
    GiftCard,
    GiftCardTemplate,
    generate_gift_card_code,
)
from spacenter.models import Country


GIFT_TEMPLATES = [
    {"name": "Classic Gift Card",            "description": "Redeemable for all spa services and products.",           "amount": Decimal("100"),  "validity_days": 365, "sort_order": 1},
    {"name": "Premium Gift Card",            "description": "Treat someone special with a premium spa experience.",    "amount": Decimal("250"),  "validity_days": 365, "sort_order": 2},
    {"name": "Luxury Gift Card",             "description": "Full access to all services and products.",               "amount": Decimal("500"),  "validity_days": 365, "sort_order": 3},
    {"name": "Couple's Experience Card",     "description": "A shared relaxation experience for couples.",             "amount": Decimal("750"),  "validity_days": 365, "sort_order": 4},
    {"name": "Royal Retreat Card",           "description": "The ultimate spa day – unlimited pampering.",             "amount": Decimal("1000"), "validity_days": 730, "sort_order": 5},
]

CURRENCY_MAP = {"QAT": "QAR", "KWT": "KWD", "ARE": "AED"}


class Command(BaseCommand):
    help = "Seed promotions (gift card templates, gift cards)"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true")

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing promotions...")
            GiftCard.objects.all().delete()
            GiftCardTemplate.objects.all().delete()

        self._seed_gift_templates()
        self._seed_gift_cards()
        self.stdout.write(self.style.SUCCESS("\n✅ Promotions seeding complete!"))

    def _seed_gift_templates(self):
        self.stdout.write("\nSeeding gift card templates (per country)...")
        for country in Country.objects.all():
            currency = CURRENCY_MAP.get(country.code, "QAR")
            for t in GIFT_TEMPLATES:
                name = f"{t['name']} ({country.code})"
                obj, created = GiftCardTemplate.objects.update_or_create(
                    name=name,
                    defaults={
                        "description": t["description"],
                        "amount": t["amount"],
                        "currency": currency,
                        "validity_days": t["validity_days"],
                        "sort_order": t["sort_order"],
                        "country": country,
                        "is_active": True,
                    },
                )
                self.stdout.write(f"  {'Created' if created else 'Updated'}: {name}")

    def _seed_gift_cards(self):
        self.stdout.write("\nSeeding sample gift cards...")
        customers = list(User.objects.filter(user_type=UserType.CUSTOMER)[:3])
        templates = list(GiftCardTemplate.objects.all()[:3])
        now = timezone.now()

        if not customers or not templates:
            self.stdout.write(self.style.WARNING("  Skip – no customers or templates"))
            return

        for customer, template in zip(customers, templates):
            if GiftCard.objects.filter(purchased_by=customer, template=template).exists():
                continue
            card = GiftCard.objects.create(
                code=generate_gift_card_code(),
                template=template,
                initial_amount=template.amount,
                current_balance=template.amount,
                currency=template.currency,
                purchased_by=customer,
                owner=customer,
                recipient_name=customer.get_full_name(),
                recipient_email=customer.email or "",
                country=template.country,
                applicable_to_services=template.applicable_to_services,
                applicable_to_products=template.applicable_to_products,
                valid_from=now,
                valid_until=now + timedelta(days=template.validity_days),
                status="active",
                purchased_at=now,
                activated_at=now,
            )
            self.stdout.write(self.style.SUCCESS(f"  Created: {card.code} for {customer.get_full_name()}"))
