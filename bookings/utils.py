
from collections import defaultdict
from datetime import timedelta
from django.utils import timezone
from bookings.models import TimeSlot
from spacenter.models import ServiceArrangement

def calculate_service_availability(service, spa_center, date_from, date_to):
    """
    Calculate availability for a service at a specific spa center within a date range.
    
    Returns a dictionary containing:
    - arrangements: List of arrangement details with their prices
    - timeslots_availability: Merged availability slots
    """
    
    # Get arrangements for this service at this spa center
    arrangements = ServiceArrangement.objects.filter(
        service=service,
        spa_center=spa_center,
        is_active=True
    )

    if not arrangements.exists():
        return {
            "arrangements": [],
            "timeslots_availability": {}
        }

    # Get all booked time slots for the date range
    booked_slots = TimeSlot.objects.filter(
        arrangement__in=arrangements,
        date__gte=date_from,
        date__lte=date_to,
    ).select_related("arrangement")

    # Build booked slots response and helper structure
    # Store count of bookings per (arrangement, date, hour_slot)
    booked_slots_data = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    
    for slot in booked_slots:
        arr_id = str(slot.arrangement_id)
        date_str = slot.date.isoformat()
        
        # Get all blocked hour slots for this booking
        blocked_hours = slot.get_blocked_hour_slots()
        for hour_slot in blocked_hours:
            booked_slots_data[arr_id][date_str][hour_slot] += 1

    # Generate all possible time slots from spa opening to closing
    opening_hour = spa_center.default_opening_time.hour
    closing_hour = spa_center.default_closing_time.hour
    all_hour_slots = [
        f"{h:02d}:00 - {h+1:02d}:00"
        for h in range(opening_hour, closing_hour)
    ]

    # Map arrangement IDs to their room_count for quick lookup
    arr_room_counts = {str(arr.id): arr.room_count for arr in arrangements}

    # Group arrangements by type to merge availability
    arrangements_by_type = defaultdict(list)
    for arr in arrangements:
        arrangements_by_type[arr.arrangement_type].append(str(arr.id))

    # Calculate merged availability per arrangement type
    # A slot is "available" if at least one arrangement of that type has free space (OR condition)
    merged_availability = defaultdict(lambda: defaultdict(dict))
    
    current_date = date_from
    while current_date <= date_to:
        date_str = current_date.isoformat()
        
        for arr_type, arr_ids in arrangements_by_type.items():
            for hour_slot in all_hour_slots:
                # Check if at least one arrangement of this type has free space
                is_available = False
                for arr_id in arr_ids:
                    booked_count = booked_slots_data[arr_id][date_str].get(hour_slot, 0)
                    if booked_count < arr_room_counts.get(arr_id, 1):
                        is_available = True
                        break
                
                merged_availability[arr_type][date_str][hour_slot] = (
                    "available" if is_available else "booked"
                )
        
        current_date += timedelta(days=1)

    # Convert nested defaultdicts to regular dicts
    merged_availability_dict = {
        arr_type: dict(dates)
        for arr_type, dates in merged_availability.items()
    }

    # Build unique arrangements list with pricing
    unique_arrangements = {}
    
    for arr in arrangements:
        # Create a unique key based on type and pricing
        key = (
            arr.arrangement_type, 
            arr.base_price, 
            arr.discount_price
        )
        
        if key not in unique_arrangements:
            unique_arrangements[key] = {
                "id": str(arr.id),  # Representative ID
                "label": arr.get_arrangement_type_display(),  # Use generic type label
                "type": arr.arrangement_type,
                "room_count": arr.room_count, 
                "base_price": str(arr.base_price),
                "discount_price": str(arr.discount_price) if arr.discount_price else None,
                "current_price": str(arr.current_price),
                "has_discount": arr.has_discount,
                "discount_percentage": arr.discount_percentage,
                "extra_minutes": arr.extra_minutes,
                "price_for_extra_minutes": str(arr.price_for_extra_minutes) if arr.price_for_extra_minutes else None,
                "count": 1, 
                "total_spaces": arr.room_count,
            }
        else:
            unique_arrangements[key]["count"] += 1
            unique_arrangements[key]["total_spaces"] += arr.room_count

    arrangements_data = list(unique_arrangements.values())

    return {
        "arrangements": arrangements_data,
        "timeslots_availability": merged_availability_dict
    }
