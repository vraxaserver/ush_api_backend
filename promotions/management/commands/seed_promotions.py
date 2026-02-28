"""
Seed promotions: Gift Cards and Loyalty Program data.

Depends on: seed_users, seed_spacenter.

Creates:
- Sample GiftCards (active, redeemed, expired) across spa centers
- LoyaltyTrackers for customers with eligible services
- LoyaltyRewards (available and redeemed)
"""

import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User, UserType
from promotions.models import (
    GiftCard,
    LoyaltyReward,
    LoyaltyTracker,
    generate_public_token,
    generate_secret_code,
)
from spacenter.models import Service, ServiceArrangement, SpaCenter


# ── Gift Card seed data ────────────────────────────────────────────

GIFT_MESSAGES = [
    "Happy Birthday! Enjoy a relaxing spa day 🎂",
    "Thank you for everything. You deserve this!",
    "Congratulations on your promotion! Treat yourself 🎉",
    "Wishing you a wonderful anniversary ❤️",
    "Just because – you deserve some pampering!",
    "Get well soon! A spa day will help you recover 💐",
    "Merry Christmas! Enjoy the gift of relaxation 🎄",
    "Happy Mother's Day! Love you so much 💕",
]

RECIPIENT_PHONES = [
    "+97455501001",
    "+97455501002",
    "+97455501003",
    "+97455501004",
    "+97455501005",
    "+96565501001",
    "+96565501002",
    "+97150501001",
    "+97150501002",
    "+97150501003",
]

RECIPIENT_NAMES = [
    "Fatima Al Thani",
    "Noura Khalid",
    "Sara Mohamed",
    "Maryam Al Suwaidi",
    "Hessa Al Mansouri",
    "Abeer Hassan",
    "Reem Abdullah",
    "Aisha Al Maktoum",
    "Latifa Nasser",
    "Maitha Al Shamsi",
]


class Command(BaseCommand):
    help = "Seed promotions (gift cards, loyalty trackers, loyalty rewards)"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true")

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing promotions...")
            LoyaltyReward.objects.all().delete()
            LoyaltyTracker.objects.all().delete()
            GiftCard.objects.all().delete()

        self._seed_gift_cards()
        self._seed_loyalty_trackers()
        self._seed_loyalty_rewards()
        self.stdout.write(self.style.SUCCESS("\n✅ Promotions seeding complete!"))

    # ── Gift Cards ─────────────────────────────────────────────────
    def _seed_gift_cards(self):
        self.stdout.write("\nSeeding gift cards...")
        customers = list(User.objects.filter(user_type=UserType.CUSTOMER))
        spa_centers = list(
            SpaCenter.objects.select_related("country", "city").all()
        )

        if not customers or not spa_centers:
            self.stdout.write(
                self.style.WARNING("  Skip – no customers or spa centers")
            )
            return

        now = timezone.now()
        created_count = 0

        for i, customer in enumerate(customers):
            # Each customer sends 2–3 gift cards
            num_cards = random.randint(2, 3)
            for j in range(num_cards):
                spa = random.choice(spa_centers)
                services = list(
                    Service.objects.filter(spa_center=spa, is_active=True)[:5]
                )
                if not services:
                    continue
                service = random.choice(services)

                # Pick a random arrangement for this service/spa combo
                arrangements = list(
                    ServiceArrangement.objects.filter(
                        spa_center=spa, service=service, is_active=True
                    )
                )
                arrangement = random.choice(arrangements) if arrangements else None

                # Extra minutes from the arrangement
                extra_mins = (
                    int(arrangement.extra_minutes) if arrangement and arrangement.extra_minutes else 0
                )
                total_dur = service.duration_minutes + extra_mins

                # Price
                amount = service.current_price
                if arrangement:
                    amount = arrangement.current_price

                # Determine status
                status_weights = [
                    (GiftCard.GiftCardStatus.ACTIVE, 4),
                    (GiftCard.GiftCardStatus.REDEEMED, 2),
                    (GiftCard.GiftCardStatus.PENDING_PAYMENT, 1),
                    (GiftCard.GiftCardStatus.EXPIRED, 1),
                ]
                status = random.choices(
                    [s for s, _ in status_weights],
                    weights=[w for _, w in status_weights],
                )[0]

                recipient_idx = (i * num_cards + j) % len(RECIPIENT_PHONES)
                card = GiftCard(
                    sender=customer,
                    recipient_phone=RECIPIENT_PHONES[recipient_idx],
                    recipient_name=RECIPIENT_NAMES[recipient_idx],
                    gift_message=random.choice(GIFT_MESSAGES),
                    service=service,
                    spa_center=spa,
                    service_arrangement=arrangement,
                    extra_minutes=extra_mins,
                    total_duration=total_dur,
                    amount=amount,
                    currency=service.currency,
                    secret_code=generate_secret_code(),
                    public_token=generate_public_token(),
                    status=status,
                    sms_sent=status != GiftCard.GiftCardStatus.PENDING_PAYMENT,
                    sms_sent_at=(
                        now - timedelta(days=random.randint(1, 30))
                        if status != GiftCard.GiftCardStatus.PENDING_PAYMENT
                        else None
                    ),
                    expires_at=now + timedelta(days=random.randint(30, 365)),
                )

                # Redeemed cards get redeemed metadata
                if status == GiftCard.GiftCardStatus.REDEEMED:
                    card.redeemed_at = now - timedelta(days=random.randint(1, 15))
                    # Pick a random customer as redeemer
                    card.redeemed_by = random.choice(customers)

                # Expired cards get past expiry
                if status == GiftCard.GiftCardStatus.EXPIRED:
                    card.expires_at = now - timedelta(days=random.randint(1, 60))

                card.save()
                created_count += 1
                self.stdout.write(
                    f"  Created: Gift Card → {card.recipient_phone} "
                    f"({card.get_status_display()}) – {service.name} @ {spa.name}"
                )

        self.stdout.write(f"  Total gift cards created: {created_count}")

    # ── Loyalty Trackers ───────────────────────────────────────────
    def _seed_loyalty_trackers(self):
        self.stdout.write("\nSeeding loyalty trackers...")
        customers = list(User.objects.filter(user_type=UserType.CUSTOMER))
        eligible_services = list(
            Service.objects.filter(
                is_eligible_for_loyalty=True, is_active=True
            ).select_related("spa_center")[:20]
        )

        if not customers or not eligible_services:
            # If no eligible services, pick some random ones and note it
            eligible_services = list(
                Service.objects.filter(is_active=True)
                .select_related("spa_center")[:10]
            )
            if not eligible_services:
                self.stdout.write(
                    self.style.WARNING("  Skip – no services found")
                )
                return
            self.stdout.write(
                self.style.WARNING(
                    "  ⚠ No loyalty-eligible services found; using random services"
                )
            )

        created_count = 0
        for customer in customers:
            # Each customer tracks 2–4 services
            num_services = min(random.randint(2, 4), len(eligible_services))
            tracked_services = random.sample(eligible_services, num_services)

            for service in tracked_services:
                booking_count = random.randint(0, 4)
                total_bookings = booking_count + random.randint(0, 10)
                total_rewards = total_bookings // 5

                tracker, created = LoyaltyTracker.objects.update_or_create(
                    customer=customer,
                    service=service,
                    defaults={
                        "booking_count": booking_count,
                        "bookings_required": 5,
                        "total_bookings": total_bookings,
                        "total_rewards_earned": total_rewards,
                    },
                )
                if created:
                    created_count += 1
                self.stdout.write(
                    f"  {'Created' if created else 'Updated'}: "
                    f"{customer.get_full_name()} – {service.name} "
                    f"({tracker.booking_count}/5)"
                )

        self.stdout.write(f"  Total loyalty trackers created: {created_count}")

    # ── Loyalty Rewards ────────────────────────────────────────────
    def _seed_loyalty_rewards(self):
        self.stdout.write("\nSeeding loyalty rewards...")
        trackers = list(
            LoyaltyTracker.objects.filter(total_rewards_earned__gt=0)
            .select_related("customer", "service")
        )

        if not trackers:
            self.stdout.write(
                self.style.WARNING("  Skip – no trackers with earned rewards")
            )
            return

        now = timezone.now()
        created_count = 0

        for tracker in trackers:
            # Create 1–2 rewards per tracker (up to total_rewards_earned)
            num_rewards = min(
                random.randint(1, 2), tracker.total_rewards_earned
            )
            for r in range(num_rewards):
                # Decide reward status
                status = random.choice([
                    LoyaltyReward.RewardStatus.AVAILABLE,
                    LoyaltyReward.RewardStatus.AVAILABLE,
                    LoyaltyReward.RewardStatus.REDEEMED,
                ])

                reward = LoyaltyReward(
                    customer=tracker.customer,
                    service=tracker.service,
                    status=status,
                    expires_at=now + timedelta(days=random.randint(30, 180)),
                )

                if status == LoyaltyReward.RewardStatus.REDEEMED:
                    reward.redeemed_at = now - timedelta(
                        days=random.randint(1, 30)
                    )

                reward.save()
                created_count += 1
                self.stdout.write(
                    f"  Created: Reward for {tracker.customer.get_full_name()} "
                    f"– {tracker.service.name} ({reward.get_status_display()})"
                )

        self.stdout.write(f"  Total loyalty rewards created: {created_count}")
