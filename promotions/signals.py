"""
Promotions Signals – Loyalty Program & Gift Cards.

Hooks into booking lifecycle to award loyalty points when a booking is completed.
Hooks into gift card lifecycle to send SMS and award loyalty when a gift card
is activated (e.g. via admin status change from pending_payment → active).
"""

import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(pre_save, sender="promotions.GiftCard")
def handle_gift_card_activation(sender, instance, **kwargs):
    """
    Send SMS and award loyalty when a gift card transitions to 'active' status.

    This covers the case where an admin manually changes the status from
    'pending_payment' to 'active' (e.g. after verifying a failed payment).

    Only triggers when:
    1. The gift card already exists in the DB (not a new create).
    2. The status is changing from 'pending_payment' to 'active'.
    """
    from promotions.models import GiftCard

    # Only act on status transition to ACTIVE
    if instance.status != GiftCard.GiftCardStatus.ACTIVE:
        return

    # Only act on existing gift cards (not new creates — serializer handles those)
    if instance._state.adding:
        return

    # Check if the status actually changed from PENDING_PAYMENT
    try:
        old_instance = GiftCard.objects.get(pk=instance.pk)
    except GiftCard.DoesNotExist:
        return

    if old_instance.status != GiftCard.GiftCardStatus.PENDING_PAYMENT:
        # Not transitioning from pending_payment – skip
        return

    # Award loyalty to sender
    try:
        instance._award_sender_loyalty()
        logger.info(
            "Loyalty awarded to sender %s for gift card %s (admin activation).",
            instance.sender,
            instance.pk,
        )
    except Exception:
        logger.exception(
            "Failed to award loyalty for gift card %s on admin activation.",
            instance.pk,
        )

    # Send gift card SMS to recipient (after save completes, use post_save pattern)
    # We flag the instance so a post_save handler can send the SMS
    instance._send_sms_on_activation = True


@receiver(post_save, sender="promotions.GiftCard")
def send_sms_on_gift_card_activation(sender, instance, created, **kwargs):
    """
    Send gift card SMS after the gift card has been saved with ACTIVE status.

    Only fires when the pre_save handler flagged the instance for SMS sending
    (i.e. status transitioned from pending_payment → active via admin).
    """
    if not getattr(instance, "_send_sms_on_activation", False):
        return

    # Clear the flag to prevent re-triggering
    del instance._send_sms_on_activation

    try:
        from promotions.tasks import send_gift_card_sms
        send_gift_card_sms(str(instance.id))
        logger.info(
            "Gift card SMS sent for gift card %s (admin activation).",
            instance.pk,
        )
    except Exception:
        logger.exception(
            "Failed to send SMS for gift card %s on admin activation.",
            instance.pk,
        )

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

    # Get the service arrangement from the booking
    service_arrangement = getattr(instance, "service_arrangement", None)

    # Get or create the loyalty tracker
    from promotions.models import LoyaltyTracker

    tracker, created = LoyaltyTracker.objects.get_or_create(
        customer=customer,
        service=service,
        service_arrangement=service_arrangement,
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
