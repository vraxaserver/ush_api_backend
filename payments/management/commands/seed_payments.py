"""
Seed payments: StripeCustomers and Payment records.

Depends on: seed_users, seed_bookings.
"""

import random
from decimal import Decimal

from django.core.management.base import BaseCommand

from accounts.models import User, UserType
from bookings.models import Booking
from payments.models import Payment, StripeCustomer


class Command(BaseCommand):
    help = "Seed payments (Stripe customers and payment records)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing payment data before seeding",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing payments...")
            Payment.objects.all().delete()
            StripeCustomer.objects.all().delete()

        self._seed_stripe_customers()
        self._seed_payments()

        self.stdout.write(self.style.SUCCESS("\n✅ Payments seeding complete!"))

    def _seed_stripe_customers(self):
        self.stdout.write("\nSeeding Stripe customers...")
        customers = User.objects.filter(user_type=UserType.CUSTOMER)

        created_count = 0
        for i, user in enumerate(customers):
            stripe_id = f"cus_seed_{user.id.hex[:12]}"

            obj, created = StripeCustomer.objects.get_or_create(
                user=user,
                defaults={"stripe_customer_id": stripe_id},
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  Created: {user.get_full_name()} → {stripe_id}"
                    )
                )
            else:
                self.stdout.write(f"  Exists: {user.get_full_name()}")

        self.stdout.write(f"  Stripe customers created: {created_count}")

    def _seed_payments(self):
        self.stdout.write("\nSeeding payments...")
        bookings = Booking.objects.filter(
            status__in=[
                Booking.BookingStatus.PAYMENT_SUCCESS,
                Booking.BookingStatus.CONFIRMED,
                Booking.BookingStatus.COMPLETED,
            ]
        ).select_related("customer")

        if not bookings.exists():
            self.stdout.write(
                self.style.WARNING("  Skipping – no completed/confirmed bookings found")
            )
            return

        created_count = 0
        for booking in bookings:
            pi_id = f"pi_seed_{booking.id.hex[:16]}"

            if Payment.objects.filter(stripe_payment_intent_id=pi_id).exists():
                self.stdout.write(f"  Exists: Payment for {booking.booking_number}")
                continue

            status_map = {
                Booking.BookingStatus.PAYMENT_SUCCESS: Payment.PaymentStatus.SUCCEEDED,
                Booking.BookingStatus.CONFIRMED: Payment.PaymentStatus.SUCCEEDED,
                Booking.BookingStatus.COMPLETED: Payment.PaymentStatus.SUCCEEDED,
            }

            Payment.objects.create(
                user=booking.customer,
                booking=booking,
                stripe_payment_intent_id=pi_id,
                amount=booking.total_price,
                currency="qar",
                status=status_map.get(
                    booking.status, Payment.PaymentStatus.SUCCEEDED
                ),
                metadata={
                    "booking_number": booking.booking_number,
                    "service": booking.service_arrangement.service.name,
                    "spa_center": booking.spa_center.name,
                    "seeded": True,
                },
            )
            created_count += 1
            self.stdout.write(
                f"  Created: Payment {pi_id[:20]}… for {booking.booking_number} "
                f"(QAR {booking.total_price})"
            )

        self.stdout.write(f"  Payments created: {created_count}")
