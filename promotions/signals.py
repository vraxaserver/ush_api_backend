"""
Promotions Signals – Loyalty Program.

Hooks into booking lifecycle to award loyalty points when a booking is completed.
"""

import logging

from django.db.models.signals import pre_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(pre_save, sender="bookings.Booking")
def award_loyalty_on_payment_success(sender, instance, **kwargs):
    """
    Award loyalty points when a booking transitions to 'payment_success' status.

    This signal fires on every Booking save. It only takes action when:
    1. The booking already exists in the DB (not a new create).
    2. The status is changing **to** 'payment_success'.
    3. The service on the booking has `is_eligible_for_loyalty = True`.

    On activation it:
    - Gets or creates a LoyaltyTracker for (customer, service).
    - Calls `tracker.record_booking(booking)` which increments the counter
      and issues a LoyaltyReward if the threshold is met.
    """
    from bookings.models import Booking

    # Only act on status transition to PAYMENT_SUCCESS
    if instance.status != Booking.BookingStatus.PAYMENT_SUCCESS:
        return

    # Only act on existing bookings (not new creates)
    if instance._state.adding:
        return

    # Check if the status actually changed
    try:
        old_instance = Booking.objects.get(pk=instance.pk)
    except Booking.DoesNotExist:
        return

    if old_instance.status == Booking.BookingStatus.PAYMENT_SUCCESS:
        # Status didn't change – already payment_success
        return

    # Get the service – prefer the direct service FK, fallback to arrangement
    service = instance.service
    if not service and instance.service_arrangement:
        service = instance.service_arrangement.service

    if not service:
        logger.warning(
            "Booking %s completed but has no associated service – "
            "skipping loyalty tracking.",
            instance.pk,
        )
        return

    # Check if the service is eligible for the loyalty program
    if not getattr(service, "is_eligible_for_loyalty", False):
        return

    # Get the customer
    customer = instance.customer
    if not customer:
        logger.warning(
            "Booking %s completed but has no customer – "
            "skipping loyalty tracking.",
            instance.pk,
        )
        return

    # Get or create the loyalty tracker
    from promotions.models import LoyaltyTracker

    tracker, created = LoyaltyTracker.objects.get_or_create(
        customer=customer,
        service=service,
    )

    reward = tracker.record_booking(booking=instance)

    if reward:
        logger.info(
            "Loyalty reward issued for customer %s – service '%s' "
            "(reward ID: %s). Tracker reset to 0/%d.",
            customer,
            service.name,
            reward.pk,
            tracker.bookings_required,
        )
    else:
        logger.info(
            "Loyalty progress updated for customer %s – service '%s': "
            "%d/%d bookings.",
            customer,
            service.name,
            tracker.booking_count,
            tracker.bookings_required,
        )
