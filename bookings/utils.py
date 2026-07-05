"""
Booking Utility Functions.

Centralises availability calculation so it can be reused across views
and serializers without duplication.  The core function returns a dict
whose shape is guaranteed to remain stable so the frontend contract is
never broken.
"""

from collections import defaultdict
from datetime import timedelta

from django.db.models import Q

from bookings.models import TimeSlot
from spacenter.models import ServiceArrangement


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def calculate_service_availability(service, spa_center, date_from, date_to):
    """
    Calculate timeslot availability for a service at a specific spa center.

    Fetches every active ServiceArrangement that accepts *service*
    (via the legacy `service` FK, the `allows_all_services` flag, or the
    `allowed_services` M2M whitelist), then derives per-date-per-hour-slot
    occupancy from the TimeSlot table in a single query.

    The same room can run different arrangement types concurrently; capacity
    is therefore per-arrangement (1 if a Room FK is set, else ``room_count``).

    Args:
        service:    A ``Service`` instance.
        spa_center: A ``SpaCenter`` instance.
        date_from:  ``datetime.date`` — start of the range (inclusive).
        date_to:    ``datetime.date`` — end of the range (inclusive).

    Returns:
        {
            "arrangements": [
                {
                    "id": "<uuid>",
                    "label": "Single Room",      # human-readable type label
                    "type": "single_room",
                    "room_count": 2,              # total concurrent capacity
                    "base_price": "150.00",
                    "discount_price": null,
                    "current_price": "150.00",
                    "has_discount": false,
                    "discount_percentage": 0,
                    "extra_minutes": "0",
                    "price_for_extra_minutes": null,
                    "count": 2,                  # number of arrangement records
                    "total_spaces": 2,
                    # Extension (additive — does not break existing frontend):
                    "room": {"id": "...", "room_id": "A1", "name": "Room A1"} | null,
                    "allows_all_services": true,
                    "allows_all_add_ons": true,
                },
                ...
            ],
            "timeslots_availability": {
                "single_room": {
                    "2026-01-19": {"08:00 - 09:00": "available", ...},
                    ...
                },
                ...
            }
        }
    """

    # ------------------------------------------------------------------
    # 1. Fetch active arrangements that accept this service (one query)
    # ------------------------------------------------------------------
    arrangements = (
        ServiceArrangement.objects
        .filter(
            spa_center=spa_center,
            is_active=True,
            prices__service=service
        )
        .select_related("room")
        .distinct()
    )

    if not arrangements.exists():
        return {"arrangements": [], "timeslots_availability": {}}

    arrangement_ids = [arr.id for arr in arrangements]
    # capacity map: {str(arr.id): int}
    arr_capacity_map = {str(arr.id): arr.capacity for arr in arrangements}

    # ------------------------------------------------------------------
    # 2. Fetch all booked slots for the date range in one DB query
    # ------------------------------------------------------------------
    booked_slots = (
        TimeSlot.objects
        .filter(
            arrangement_id__in=arrangement_ids,
            date__gte=date_from,
            date__lte=date_to,
        )
        .values("arrangement_id", "date", "start_time", "end_time")
    )

    # ------------------------------------------------------------------
    # 3. Build occupancy map: {arr_id: {date_str: {hour_slot: count}}}
    # ------------------------------------------------------------------
    occupancy: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

    for slot in booked_slots:
        arr_id = str(slot["arrangement_id"])
        date_str = slot["date"].isoformat()
        for hour_slot in _get_blocked_hour_slots(slot["start_time"], slot["end_time"]):
            occupancy[arr_id][date_str][hour_slot] += 1

    # ------------------------------------------------------------------
    # 4. Generate hour-slots from spa operating hours
    # ------------------------------------------------------------------
    opening_hour = spa_center.default_opening_time.hour
    closing_hour = spa_center.default_closing_time.hour
    all_hour_slots = [
        f"{h:02d}:00 - {h + 1:02d}:00"
        for h in range(opening_hour, closing_hour)
    ]

    # ------------------------------------------------------------------
    # 5. Group arrangements by type; compute merged availability per type
    #
    #    A slot is "available" when at least one arrangement of that type
    #    still has free capacity (booked_count < capacity).
    # ------------------------------------------------------------------
    arrangements_by_type: dict = defaultdict(list)
    for arr in arrangements:
        arrangements_by_type[arr.arrangement_type].append(str(arr.id))

    merged: dict = defaultdict(lambda: defaultdict(dict))

    current_date = date_from
    while current_date <= date_to:
        date_str = current_date.isoformat()

        for arr_type, arr_ids in arrangements_by_type.items():
            for hour_slot in all_hour_slots:
                is_available = any(
                    occupancy[arr_id][date_str].get(hour_slot, 0)
                    < arr_capacity_map[arr_id]
                    for arr_id in arr_ids
                )
                merged[arr_type][date_str][hour_slot] = (
                    "available" if is_available else "booked"
                )

        current_date += timedelta(days=1)

    timeslots_availability = {
        arr_type: dict(dates)
        for arr_type, dates in merged.items()
    }

    # ------------------------------------------------------------------
    # 6. Build the arrangements summary (deduplicated by type + pricing)
    # ------------------------------------------------------------------
    unique: dict = {}
    for arr in arrangements:
        from spacenter.models import ServiceArrangementPrice
        arr_price_obj = ServiceArrangementPrice.objects.filter(
            service=service,
            service_arrangement=arr
        ).first()
        if arr_price_obj:
            base_price = arr_price_obj.price
            discount_price = arr_price_obj.discounted_price
            current_price = discount_price if discount_price else base_price
            has_discount = discount_price is not None and discount_price < base_price
            discount_percentage = round(((base_price - discount_price) / base_price) * 100, 0) if has_discount else 0
        else:
            base_price = service.base_price
            discount_price = service.discount_price
            current_price = service.current_price
            has_discount = service.has_discount
            discount_percentage = service.discount_percentage

        key = (arr.arrangement_type, base_price, discount_price)
        if key not in unique:
            unique[key] = {
                # Core fields (unchanged from original contract)
                "id": str(arr.id),
                "label": arr.get_arrangement_type_display(),
                "type": arr.arrangement_type,
                "arrangement_label": arr.arrangement_label,
                "room_count": arr.capacity,
                "base_price": str(base_price),
                "discount_price": str(discount_price) if discount_price else None,
                "current_price": str(current_price),
                "has_discount": has_discount,
                "discount_percentage": discount_percentage,
                "extra_minutes": arr_price_obj.extra_minutes if arr_price_obj else "0",
                "price_for_extra_minutes": (
                    str(arr_price_obj.price_for_extra_minutes)
                    if arr_price_obj and arr_price_obj.price_for_extra_minutes else None
                ),
                "count": 1,
                "total_spaces": arr.capacity,
                # Extensions (additive — no frontend breakage)
                "room": (
                    {
                        "id": str(arr.room.id),
                        "room_id": arr.room.room_id,
                        "name": arr.room.name,
                    }
                    if arr.room else None
                ),
                "allows_all_services": True,
                "allows_all_add_ons": True,
                "add_on_services_queryset": arr.get_effective_add_on_services(service),
            }
        else:
            unique[key]["count"] += 1
            unique[key]["total_spaces"] += arr.capacity
            unique[key]["room_count"] += arr.capacity

    return {
        "arrangements": list(unique.values()),
        "timeslots_availability": timeslots_availability,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_blocked_hour_slots(start_time, end_time) -> list:
    """
    Return the list of standard 1-hour slot strings blocked by a booking.

    Example: start=10:00, end=11:30  →  ["10:00 - 11:00", "11:00 - 12:00"]
    """
    blocked = []
    start_hour = start_time.hour
    end_hour = end_time.hour + (1 if end_time.minute > 0 else 0)
    for h in range(start_hour, end_hour):
        blocked.append(f"{h:02d}:00 - {h + 1:02d}:00")
    return blocked
