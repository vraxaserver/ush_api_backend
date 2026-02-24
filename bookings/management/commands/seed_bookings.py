"""
Seed bookings: TimeSlots, Bookings, ProductOrders, and OrderItems.

Depends on: seed_users, seed_spacenter, seed_promotions.
"""

import random
from datetime import date, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User, UserType
from bookings.models import (
    Booking,
    OrderItem,
    ProductOrder,
    TimeSlot,
)
from spacenter.models import ServiceArrangement, SpaCenter, SpaProduct


class Command(BaseCommand):
    help = "Seed bookings (time slots, bookings, product orders, order items)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing bookings before seeding",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing bookings...")
            OrderItem.objects.all().delete()
            ProductOrder.objects.all().delete()
            Booking.objects.all().delete()
            TimeSlot.objects.all().delete()

        self._seed_bookings()
        self._seed_product_orders()

        self.stdout.write(self.style.SUCCESS("\n✅ Bookings seeding complete!"))

    def _seed_bookings(self):
        self.stdout.write("\nSeeding bookings...")
        customers = list(User.objects.filter(user_type=UserType.CUSTOMER))
        arrangements = list(ServiceArrangement.objects.select_related(
            "spa_center", "service"
        ).filter(is_active=True))

        if not customers or not arrangements:
            self.stdout.write(
                self.style.WARNING("  Skipping – no customers or arrangements found")
            )
            return

        # Generate bookings across the next 14 days
        today = date.today()
        start_hours = [9, 10, 11, 13, 14, 15, 16, 17, 18, 19]
        statuses = [
            Booking.BookingStatus.CONFIRMED,
            Booking.BookingStatus.CONFIRMED,
            Booking.BookingStatus.PAYMENT_SUCCESS,
            Booking.BookingStatus.COMPLETED,
            Booking.BookingStatus.REQUESTED,
        ]

        created_count = 0
        for day_offset in range(14):
            booking_date = today + timedelta(days=day_offset)

            # 2–4 bookings per day
            num_bookings = random.randint(2, 4)
            day_arrangements = random.sample(
                arrangements, min(num_bookings, len(arrangements))
            )

            for i, arrangement in enumerate(day_arrangements):
                customer = random.choice(customers)
                start_hour = start_hours[i % len(start_hours)]
                start_t = time(start_hour, 0)

                # Calculate end time
                end_t = Booking.calculate_end_time(
                    start_t,
                    arrangement.service.duration_minutes,
                    cleanup_duration=arrangement.cleanup_duration,
                )

                # Check for existing time slot conflict
                if TimeSlot.objects.filter(
                    arrangement=arrangement,
                    date=booking_date,
                    start_time=start_t,
                ).exists():
                    continue

                # Create time slot
                time_slot = TimeSlot.objects.create(
                    arrangement=arrangement,
                    date=booking_date,
                    start_time=start_t,
                    end_time=end_t,
                )

                # Calculate pricing
                base = arrangement.current_price
                discount = Decimal("0.00")
                total = base - discount

                # Pick status
                if day_offset < 0:
                    status = Booking.BookingStatus.COMPLETED
                elif day_offset == 0:
                    status = random.choice([
                        Booking.BookingStatus.CONFIRMED,
                        Booking.BookingStatus.PAYMENT_SUCCESS,
                    ])
                else:
                    status = random.choice(statuses)

                booking = Booking.objects.create(
                    customer=customer,
                    spa_center=arrangement.spa_center,
                    service=arrangement.service,
                    service_arrangement=arrangement,
                    time_slot=time_slot,
                    subtotal=base,
                    discount_amount=discount,
                    total_price=total,
                    status=status,
                    customer_message=random.choice([
                        "",
                        "Please prepare a quiet room.",
                        "I have sensitive skin, please use gentle oils.",
                        "First visit – looking forward to it!",
                        "Celebrating anniversary, any special touches appreciated.",
                    ]),
                )
                created_count += 1
                self.stdout.write(
                    f"  Created: {booking.booking_number} – "
                    f"{arrangement.service.name} on {booking_date} at {start_t}"
                )

        self.stdout.write(f"  Total bookings created: {created_count}")

    def _seed_product_orders(self):
        self.stdout.write("\nSeeding product orders...")
        customers = list(User.objects.filter(user_type=UserType.CUSTOMER))
        products = list(SpaProduct.objects.select_related("product").filter(
            quantity__gt=0
        ))

        if not customers or not products:
            self.stdout.write(
                self.style.WARNING("  Skipping – no customers or products found")
            )
            return

        created_count = 0
        for customer in customers[:3]:
            # 1–2 orders per customer
            num_orders = random.randint(1, 2)
            for _ in range(num_orders):
                order = ProductOrder.objects.create(
                    user=customer,
                    status=random.choice([
                        ProductOrder.OrderStatus.COMPLETED,
                        ProductOrder.OrderStatus.PROCESSING,
                        ProductOrder.OrderStatus.PENDING,
                    ]),
                    payment_status=ProductOrder.PaymentStatus.PAID,
                    currency="QAR",
                    payment_method=random.choice([
                        "Credit Card", "Apple Pay", "Cash",
                    ]),
                )

                # Add 1–3 items
                order_total = Decimal("0.00")
                num_items = random.randint(1, 3)
                order_products = random.sample(products, min(num_items, len(products)))

                for spa_product in order_products:
                    qty = random.randint(1, 3)
                    unit_price = spa_product.current_price
                    item_total = unit_price * qty

                    OrderItem.objects.create(
                        order=order,
                        product=spa_product,
                        quantity=qty,
                        unit_price=unit_price,
                        total_price=item_total,
                    )
                    order_total += item_total

                order.total_amount = order_total
                order.final_amount = order_total
                order.save(update_fields=["total_amount", "final_amount"])

                created_count += 1
                self.stdout.write(
                    f"  Created: {order.order_number} – "
                    f"{num_items} items, Total: QAR {order_total}"
                )

        self.stdout.write(f"  Total product orders created: {created_count}")
