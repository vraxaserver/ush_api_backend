"""
Comprehensive Feature Tests for Spa Booking System.

Verifies all 4 core requirements:
  1. Each SpaCenter may have many Rooms with unique room_id per spa center.
  2. Each Room can have single or multiple ServiceArrangements.
  3. Each Arrangement can allow all or selected services / add-ons.
  4. Available date & timeslot calculation returns the correct response format.

Run with:
    python -m pytest bookings/tests/test_features.py -v --ds=config.settings
"""

from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from bookings.models import Booking, TimeSlot
from bookings.utils import calculate_service_availability, _get_blocked_hour_slots
from spacenter.models import (
    AddOnService,
    City,
    Country,
    Room,
    Service,
    ServiceArrangement,
    Specialty,
    SpaCenter,
)

User = get_user_model()

TODAY = timezone.now().date()
TOMORROW = TODAY + timedelta(days=1)
DAY_AFTER = TODAY + timedelta(days=2)


# =============================================================================
# Shared Test Fixtures (mixin so each test class is isolated)
# =============================================================================


class SpaCenterFixtureMixin:
    """
    Creates the minimal set of DB objects needed for each test class.

    Keeps setUp small and readable so individual tests can extend it
    without repeating boilerplate.
    """

    @classmethod
    def setUpTestData(cls):
        cls.country = Country.objects.create(
            name="Qatar", code="QAT", phone_code="+974"
        )
        cls.city = City.objects.create(country=cls.country, name="Doha")
        cls.specialty = Specialty.objects.create(name="Massage")

        cls.spa = SpaCenter.objects.create(
            name="Test Spa",
            slug="test-spa",
            country=cls.country,
            city=cls.city,
            address="Corniche",
            default_opening_time=time(9, 0),
            default_closing_time=time(21, 0),
        )

        cls.service_a = Service.objects.create(
            name="Swedish Massage",
            specialty=cls.specialty,
            country=cls.country,
            city=cls.city,
            duration_minutes=60,
            base_price=Decimal("100.00"),
            spa_center=cls.spa,
        )
        cls.service_b = Service.objects.create(
            name="Deep Tissue",
            specialty=cls.specialty,
            country=cls.country,
            city=cls.city,
            duration_minutes=90,
            base_price=Decimal("150.00"),
            spa_center=cls.spa,
        )

        cls.addon_a = AddOnService.objects.create(
            name="Hot Stones",
            duration_minutes=15,
            price=Decimal("30.00"),
        )
        cls.addon_b = AddOnService.objects.create(
            name="Aromatherapy",
            duration_minutes=10,
            price=Decimal("20.00"),
        )


        cls.customer = User.objects.create_user(
            email="customer@test.com",
            password="pass123",
            phone_number="+97455001234",
        )


# =============================================================================
# Requirement 1: Unique room_id per SpaCenter
# =============================================================================


class RoomUniquenessTests(SpaCenterFixtureMixin, TestCase):
    """
    Requirement 1: Each SpaCenter may have many Rooms with a unique room_id.
    """

    def test_create_multiple_rooms_in_same_spa(self):
        """A spa can have multiple rooms."""
        r1 = Room.objects.create(spa_center=self.spa, room_id="A1", name="Room A1")
        r2 = Room.objects.create(spa_center=self.spa, room_id="A2", name="Room A2")
        self.assertEqual(self.spa.rooms.count(), 2)
        self.assertNotEqual(r1.room_id, r2.room_id)

    def test_room_id_unique_within_spa(self):
        """Duplicate room_id within the same spa raises IntegrityError."""
        from django.db import IntegrityError

        Room.objects.create(spa_center=self.spa, room_id="A1", name="Room A1")
        with self.assertRaises(IntegrityError):
            Room.objects.create(spa_center=self.spa, room_id="A1", name="Duplicate")

    def test_same_room_id_allowed_in_different_spas(self):
        """The same room_id string can exist in a different spa center."""
        spa2 = SpaCenter.objects.create(
            name="Spa 2",
            slug="spa-2",
            country=self.country,
            city=self.city,
            address="Pearl Qatar",
        )
        Room.objects.create(spa_center=self.spa, room_id="VIP-01", name="VIP A")
        # Should NOT raise
        r2 = Room.objects.create(spa_center=spa2, room_id="VIP-01", name="VIP B")
        self.assertEqual(r2.room_id, "VIP-01")

    def test_room_str_includes_spa_and_room_id(self):
        """__str__ includes spa name and room_id for easy admin identification."""
        room = Room.objects.create(spa_center=self.spa, room_id="B3", name="Suite B3")
        self.assertIn(self.spa.name, str(room))
        self.assertIn("B3", str(room))


# =============================================================================
# Requirement 2: Each room can have single or multiple arrangements
# =============================================================================


class RoomArrangementTests(SpaCenterFixtureMixin, TestCase):
    """
    Requirement 2: A room can have one or many ServiceArrangements.
    """

    def setUp(self):
        self.room = Room.objects.create(
            spa_center=self.spa, room_id="C1", name="Combo Room"
        )

    def test_single_arrangement_per_room(self):
        """A room can have exactly one arrangement."""
        arr = ServiceArrangement.objects.create(
            spa_center=self.spa,
            room=self.room,
            arrangement_type=ServiceArrangement.ArrangementType.SINGLE_ROOM,
            arrangement_label="Single C1",
        )
        self.assertEqual(self.room.arrangements.count(), 1)
        self.assertEqual(arr.room, self.room)

    def test_multiple_arrangements_per_room(self):
        """A room can have multiple arrangements (e.g. single + couple)."""
        ServiceArrangement.objects.create(
            spa_center=self.spa,
            room=self.room,
            arrangement_type=ServiceArrangement.ArrangementType.SINGLE_ROOM,
            arrangement_label="Single C1",
        )
        ServiceArrangement.objects.create(
            spa_center=self.spa,
            room=self.room,
            arrangement_type=ServiceArrangement.ArrangementType.COUPLE_ROOM,
            arrangement_label="Couple C1",
        )
        self.assertEqual(self.room.arrangements.count(), 2)

    def test_room_based_arrangement_capacity_is_always_1(self):
        """
        Capacity == 1 for room-based arrangements.
        This enforces: one booking per arrangement per timeslot.
        """
        arr = ServiceArrangement.objects.create(
            spa_center=self.spa,
            room=self.room,
            arrangement_type=ServiceArrangement.ArrangementType.VIP_SUITE,
            arrangement_label="VIP C1",
        )
        self.assertEqual(arr.capacity, 1)

    def test_arrangement_must_belong_to_same_spa_as_room(self):
        """clean() raises ValidationError if room belongs to a different spa."""
        from django.core.exceptions import ValidationError

        spa2 = SpaCenter.objects.create(
            name="Other Spa",
            slug="other-spa",
            country=self.country,
            city=self.city,
            address="West Bay",
        )
        other_room = Room.objects.create(
            spa_center=spa2, room_id="X1", name="Other Room"
        )
        arr = ServiceArrangement(
            spa_center=self.spa,  # different spa
            room=other_room,
            arrangement_type=ServiceArrangement.ArrangementType.SINGLE_ROOM,
            arrangement_label="Cross-spa",
        )
        with self.assertRaises(ValidationError):
            arr.full_clean()


# =============================================================================
# Requirement 3: Service & Add-on whitelisting per arrangement
# =============================================================================


class ServiceWhitelistTests(SpaCenterFixtureMixin, TestCase):
    """
    Requirement 3a: Arrangement allows service if price exists.
    """

    def setUp(self):
        self.room = Room.objects.create(
            spa_center=self.spa, room_id="WL-R1", name="WL Room"
        )

    def test_service_allowed_if_price_exists(self):
        arr = ServiceArrangement.objects.create(
            spa_center=self.spa,
            room=self.room,
            arrangement_type=ServiceArrangement.ArrangementType.SINGLE_ROOM,
            arrangement_label="Selected Services",
        )
        from spacenter.models import ServiceArrangementPrice
        ServiceArrangementPrice.objects.create(
            service=self.service_a,
            service_arrangement=arr,
            price=Decimal("100.00"),
        )
        self.assertTrue(arr.is_service_allowed(self.service_a))
        self.assertFalse(arr.is_service_allowed(self.service_b))


class AddOnWhitelistTests(SpaCenterFixtureMixin, TestCase):
    """
    Requirement 3b: Arrangement allows all add-ons OR a selected whitelist.
    """

    def setUp(self):
        self.room = Room.objects.create(
            spa_center=self.spa, room_id="AO-R1", name="Add-on Room"
        )
        self.arr_all = ServiceArrangement.objects.create(
            spa_center=self.spa,
            room=self.room,
            arrangement_type=ServiceArrangement.ArrangementType.SINGLE_ROOM,
            arrangement_label="All Add-ons",
        )
        self.arr_selected = ServiceArrangement.objects.create(
            spa_center=self.spa,
            room=self.room,
            arrangement_type=ServiceArrangement.ArrangementType.COUPLE_ROOM,
            arrangement_label="Selected Add-ons",
        )
        from spacenter.models import ServiceArrangementAddOn
        selected_addon = ServiceArrangementAddOn.objects.create(
            service_arrangement=self.arr_selected
        )
        selected_addon.add_on_services.add(self.addon_a)

    def test_allows_all_add_ons_returns_all_active_addons(self):
        """No whitelist record -> returns all active add-ons by default."""
        qs = self.arr_all.get_effective_add_on_services(self.service_a)
        pks = set(qs.values_list("pk", flat=True))
        self.assertIn(self.addon_a.pk, pks)
        self.assertIn(self.addon_b.pk, pks)

    def test_selected_add_ons_only_returns_whitelist(self):
        """Whitelist record exists -> only returns whitelisted add-ons."""
        qs = self.arr_selected.get_effective_add_on_services(self.service_a)
        pks = set(qs.values_list("pk", flat=True))
        self.assertIn(self.addon_a.pk, pks)
        self.assertNotIn(self.addon_b.pk, pks)



# =============================================================================
# Requirement 4: Availability calculation
# =============================================================================


class BlockedHourSlotsTests(TestCase):
    """Unit tests for the _get_blocked_hour_slots helper."""

    def test_exact_one_hour(self):
        slots = _get_blocked_hour_slots(time(10, 0), time(11, 0))
        self.assertEqual(slots, ["10:00 - 11:00"])

    def test_partial_hour_at_end_blocks_next_slot(self):
        slots = _get_blocked_hour_slots(time(10, 0), time(11, 30))
        self.assertIn("10:00 - 11:00", slots)
        self.assertIn("11:00 - 12:00", slots)
        self.assertEqual(len(slots), 2)

    def test_multi_hour(self):
        slots = _get_blocked_hour_slots(time(9, 0), time(12, 0))
        self.assertEqual(slots, ["09:00 - 10:00", "10:00 - 11:00", "11:00 - 12:00"])

    def test_exact_boundary_does_not_bleed(self):
        """end_time with zero minutes should NOT add an extra slot."""
        slots = _get_blocked_hour_slots(time(14, 0), time(15, 0))
        self.assertEqual(slots, ["14:00 - 15:00"])


class AvailabilityUtilTests(SpaCenterFixtureMixin, TestCase):
    """
    Requirement 4: calculate_service_availability returns correct data.
    """

    def setUp(self):
        self.room1 = Room.objects.create(
            spa_center=self.spa, room_id="R1", name="Room 1"
        )
        self.room2 = Room.objects.create(
            spa_center=self.spa, room_id="R2", name="Room 2"
        )
        # Two single-room arrangements (one per room)
        self.arr1 = ServiceArrangement.objects.create(
            spa_center=self.spa,
            room=self.room1,
            arrangement_type=ServiceArrangement.ArrangementType.SINGLE_ROOM,
            arrangement_label="Single R1",
            cleanup_duration=15,
        )
        self.arr2 = ServiceArrangement.objects.create(
            spa_center=self.spa,
            room=self.room2,
            arrangement_type=ServiceArrangement.ArrangementType.SINGLE_ROOM,
            arrangement_label="Single R2",
            cleanup_duration=15,
        )
        from spacenter.models import ServiceArrangementPrice
        ServiceArrangementPrice.objects.create(
            service=self.service_a,
            service_arrangement=self.arr1,
            price=self.service_a.base_price,
        )
        ServiceArrangementPrice.objects.create(
            service=self.service_a,
            service_arrangement=self.arr2,
            price=self.service_a.base_price,
        )
        ServiceArrangementPrice.objects.create(
            service=self.service_b,
            service_arrangement=self.arr1,
            price=self.service_b.base_price,
        )
        ServiceArrangementPrice.objects.create(
            service=self.service_b,
            service_arrangement=self.arr2,
            price=self.service_b.base_price,
        )

    def _book_slot(self, arrangement, on_date, start, end):
        """Helper: create a TimeSlot (simulates a booking)."""
        return TimeSlot.objects.create(
            arrangement=arrangement, date=on_date, start_time=start, end_time=end
        )

    def test_response_has_required_keys(self):
        """Response dict contains arrangements and timeslots_availability."""
        result = calculate_service_availability(
            self.service_a, self.spa, TOMORROW, TOMORROW
        )
        self.assertIn("arrangements", result)
        self.assertIn("timeslots_availability", result)

    def test_all_slots_available_when_no_bookings(self):
        """Every hour slot is 'available' when no time slots are booked."""
        result = calculate_service_availability(
            self.service_a, self.spa, TOMORROW, TOMORROW
        )
        avail = result["timeslots_availability"]
        date_str = TOMORROW.isoformat()
        self.assertIn("single_room", avail)
        for slot_status in avail["single_room"][date_str].values():
            self.assertEqual(slot_status, "available")

    def test_slot_booked_when_all_arrangements_of_type_are_full(self):
        """
        A slot is 'booked' only when EVERY arrangement of that type has
        a conflicting booking (capacity exhausted for all rooms of that type).
        """
        self._book_slot(self.arr1, TOMORROW, time(10, 0), time(11, 15))
        self._book_slot(self.arr2, TOMORROW, time(10, 0), time(11, 15))

        result = calculate_service_availability(
            self.service_a, self.spa, TOMORROW, TOMORROW
        )
        avail = result["timeslots_availability"]["single_room"][TOMORROW.isoformat()]

        self.assertEqual(avail["10:00 - 11:00"], "booked")
        self.assertEqual(avail["11:00 - 12:00"], "booked")

    def test_slot_still_available_when_only_one_arrangement_is_full(self):
        """
        If one arrangement is booked but another of the same type is free,
        the slot remains 'available'.
        """
        # Only book arr1; arr2 is still free
        self._book_slot(self.arr1, TOMORROW, time(10, 0), time(11, 15))

        result = calculate_service_availability(
            self.service_a, self.spa, TOMORROW, TOMORROW
        )
        avail = result["timeslots_availability"]["single_room"][TOMORROW.isoformat()]
        self.assertEqual(avail["10:00 - 11:00"], "available")

    def test_availability_respects_spa_operating_hours(self):
        """
        Hour slots are generated from spa opening to closing time only.
        """
        result = calculate_service_availability(
            self.service_a, self.spa, TOMORROW, TOMORROW
        )
        avail = result["timeslots_availability"]["single_room"][TOMORROW.isoformat()]
        self.assertIn("09:00 - 10:00", avail)
        self.assertIn("20:00 - 21:00", avail)
        self.assertNotIn("08:00 - 09:00", avail)
        self.assertNotIn("21:00 - 22:00", avail)

    def test_multi_date_range_produces_entry_for_each_date(self):
        """
        Requesting a 3-day range produces availability for all 3 dates.
        """
        result = calculate_service_availability(
            self.service_a, self.spa, TOMORROW, DAY_AFTER
        )
        avail = result["timeslots_availability"]["single_room"]
        self.assertIn(TOMORROW.isoformat(), avail)
        self.assertIn(DAY_AFTER.isoformat(), avail)

    def test_arrangements_list_contains_expected_fields(self):
        """
        Each entry in 'arrangements' has the fields the frontend relies on.
        """
        result = calculate_service_availability(
            self.service_a, self.spa, TOMORROW, TOMORROW
        )
        for arr_data in result["arrangements"]:
            for field in [
                "id", "label", "type", "room_count", "base_price",
                "discount_price", "current_price", "has_discount",
                "discount_percentage", "extra_minutes",
                "price_for_extra_minutes", "count", "total_spaces",
            ]:
                self.assertIn(field, arr_data, msg=f"Missing field: {field}")

    def test_whitelist_arrangement_not_returned_for_unwhitelisted_service(self):
        """
        A whitelist-mode arrangement that does NOT include service_b
        must not appear in service_b's availability.
        """
        restricted = ServiceArrangement.objects.create(
            spa_center=self.spa,
            room=self.room1,
            arrangement_type=ServiceArrangement.ArrangementType.VIP_SUITE,
            arrangement_label="VIP (A only)",
        )
        from spacenter.models import ServiceArrangementPrice
        ServiceArrangementPrice.objects.create(
            service=self.service_a,
            service_arrangement=restricted,
            price=Decimal("300.00"),
        )

        # service_b availability: arr1+arr2 allow all services, restricted does not
        result = calculate_service_availability(
            self.service_b, self.spa, TOMORROW, TOMORROW
        )
        arrangement_types = {a["type"] for a in result["arrangements"]}
        # vip_suite should NOT be in service_b's availability
        self.assertNotIn("vip_suite", arrangement_types)
        # but single_room SHOULD be (arr1 and arr2 allow all services)
        self.assertIn("single_room", arrangement_types)


# =============================================================================
# Requirement 4: API endpoint tests (response format unchanged)
# =============================================================================


class AvailabilityAPITests(SpaCenterFixtureMixin, APITestCase):
    """
    Requirement 4 (API): The availability endpoint returns the correct
    response shape and honours date boundaries.
    """

    def setUp(self):
        self.room = Room.objects.create(
            spa_center=self.spa, room_id="API-R1", name="API Room 1"
        )
        self.arrangement = ServiceArrangement.objects.create(
            spa_center=self.spa,
            room=self.room,
            arrangement_type=ServiceArrangement.ArrangementType.SINGLE_ROOM,
            arrangement_label="API Single",
            cleanup_duration=15,
        )
        from spacenter.models import ServiceArrangementPrice
        ServiceArrangementPrice.objects.create(
            service=self.service_a,
            service_arrangement=self.arrangement,
            price=self.service_a.base_price,
        )
        self.url = f"/api/v1/bookings/services/{self.service_a.id}/availability/"

    def test_returns_200_with_valid_service(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_response_shape(self):
        """Top-level keys match the documented API contract."""
        response = self.client.get(
            self.url,
            {"date_from": TOMORROW.isoformat(), "date_to": TOMORROW.isoformat()},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        for key in [
            "service_id", "service_name", "date_from", "date_to",
            "spa_center", "arrangements", "timeslots_availability",
        ]:
            self.assertIn(key, data, msg=f"Missing top-level key: {key}")

    def test_date_from_past_is_clamped_to_today(self):
        """Passing a past date_from should be silently clamped to today."""
        past = (TODAY - timedelta(days=5)).isoformat()
        response = self.client.get(self.url, {"date_from": past})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["date_from"], TODAY.isoformat())

    def test_date_to_before_date_from_returns_400(self):
        """date_to < date_from must return 400."""
        response = self.client.get(
            self.url,
            {
                "date_from": DAY_AFTER.isoformat(),
                "date_to": TOMORROW.isoformat(),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_date_format_returns_400(self):
        response = self.client.get(self.url, {"date_from": "not-a-date"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_inactive_service_returns_404(self):
        self.service_a.is_active = False
        self.service_a.save(update_fields=["is_active"])
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.service_a.is_active = True
        self.service_a.save(update_fields=["is_active"])

    def test_timeslots_grouped_by_arrangement_type(self):
        """
        timeslots_availability keys are arrangement type strings, not IDs.
        """
        response = self.client.get(
            self.url,
            {"date_from": TOMORROW.isoformat(), "date_to": TOMORROW.isoformat()},
        )
        avail = response.data["timeslots_availability"]
        self.assertIn("single_room", avail)

    def test_hour_slots_within_operating_hours(self):
        """
        Hour slots in response fall within spa operating hours (09:00-21:00).
        """
        response = self.client.get(
            self.url,
            {"date_from": TOMORROW.isoformat(), "date_to": TOMORROW.isoformat()},
        )
        date_str = TOMORROW.isoformat()
        slots = response.data["timeslots_availability"]["single_room"][date_str]
        slot_keys = list(slots.keys())
        self.assertGreater(len(slot_keys), 0)
        self.assertEqual(slot_keys[0], "09:00 - 10:00")
        self.assertEqual(slot_keys[-1], "20:00 - 21:00")

    def test_arrangement_fields_in_response(self):
        """
        Each arrangement entry includes additive fields (room, allows_all_services,
        allows_all_add_ons) without removing legacy fields (id, label, type, room_count).
        """
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        arrangements = response.data["arrangements"]
        self.assertGreater(len(arrangements), 0)
        arr = arrangements[0]
        for field in ["id", "label", "type", "room_count"]:
            self.assertIn(field, arr, msg=f"Legacy field missing: {field}")
        for field in ["room", "allows_all_services", "allows_all_add_ons", "add_on_services", "arrangement_label"]:
            self.assertIn(field, arr, msg=f"Extension field missing: {field}")

    def test_room_field_populated_when_room_is_assigned(self):
        """When arrangement has a Room FK, the 'room' field is a dict."""
        response = self.client.get(self.url)
        arr_list = response.data["arrangements"]
        arr_with_room = next(
            (a for a in arr_list if a.get("room") is not None), None
        )
        self.assertIsNotNone(arr_with_room)
        room_data = arr_with_room["room"]
        self.assertIn("id", room_data)
        self.assertIn("room_id", room_data)
        self.assertIn("name", room_data)


# =============================================================================
# Requirement 4: Booking creation validates correctly
# =============================================================================


class BookingCreateTests(SpaCenterFixtureMixin, APITestCase):
    """
    Requirement 4: Booking creation correctly validates service whitelist,
    operating hours, and timeslot availability.
    """

    def setUp(self):
        self.room = Room.objects.create(
            spa_center=self.spa, room_id="BK-R1", name="Booking Room 1"
        )
        self.arrangement = ServiceArrangement.objects.create(
            spa_center=self.spa,
            room=self.room,
            arrangement_type=ServiceArrangement.ArrangementType.SINGLE_ROOM,
            arrangement_label="Booking Single",
            cleanup_duration=15,
        )
        from spacenter.models import ServiceArrangementPrice
        ServiceArrangementPrice.objects.create(
            service=self.service_a,
            service_arrangement=self.arrangement,
            price=self.service_a.base_price,
        )
        self.client.force_authenticate(user=self.customer)
        self.url = "/api/v1/bookings/"

    def _booking_payload(self, start_time="10:00:00", on_date=None):
        return {
            "service": str(self.service_a.id),
            "spa_center": str(self.spa.id),
            "date": (on_date or TOMORROW).isoformat(),
            "start_time": start_time,
            "service_arrangement_id": str(self.arrangement.id),
        }

    def test_create_booking_succeeds_with_valid_data(self):
        data = self._booking_payload()
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Booking.objects.filter(
                customer=self.customer,
                service_arrangement=self.arrangement,
            ).exists()
        )

    def test_create_booking_requires_arrangement_id(self):
        data = self._booking_payload()
        del data["service_arrangement_id"]
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("service_arrangement_id", response.data)

    def test_create_booking_rejects_unallowed_service(self):
        """
        A whitelist-restricted arrangement that does not include service_b
        must reject a booking for service_b.
        """
        restricted_arr = ServiceArrangement.objects.create(
            spa_center=self.spa,
            room=self.room,
            arrangement_type=ServiceArrangement.ArrangementType.VIP_SUITE,
            arrangement_label="Restricted VIP",
        )
        from spacenter.models import ServiceArrangementPrice
        ServiceArrangementPrice.objects.create(
            service=self.service_a,
            service_arrangement=restricted_arr,
            price=self.service_a.base_price,
        )

        data = {
            "service": str(self.service_b.id),  # NOT whitelisted
            "spa_center": str(self.spa.id),
            "date": TOMORROW.isoformat(),
            "start_time": "10:00:00",
            "service_arrangement_id": str(restricted_arr.id),
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("service_arrangement_id", response.data)

    def test_create_booking_rejects_past_date(self):
        data = self._booking_payload(on_date=TODAY - timedelta(days=1))
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_double_booking_same_room_arrangement_fails(self):
        """
        Two bookings at the same time for the same Room-based arrangement
        (capacity=1) must fail on the second attempt.
        """
        data = self._booking_payload(start_time="14:00:00")

        response1 = self.client.post(self.url, data)
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        response2 = self.client.post(self.url, data)
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("start_time", response2.data)

    def test_booking_rejects_start_before_opening_time(self):
        """Start time before spa opening must return a validation error."""
        data = self._booking_payload(start_time="07:00:00")  # spa opens at 09:00
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("start_time", response.data)

    def test_booking_rejects_end_after_closing_time(self):
        """
        A booking whose calculated end time exceeds the spa's closing time
        must be rejected.
        service_a duration=60 + cleanup=15 -> total 75 min
        start 20:10 -> end 21:25 > 21:00 closing
        """
        data = self._booking_payload(start_time="20:10:00")
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("start_time", response.data)

    def test_booking_response_contains_time_slot_details(self):
        """
        Successful booking response includes time_slot_details with date,
        start_time, and end_time.
        """
        data = self._booking_payload(start_time="13:00:00")
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("time_slot_details", response.data)
        ts = response.data["time_slot_details"]
        self.assertIn("date", ts)
        self.assertIn("start_time", ts)
        self.assertIn("end_time", ts)

    def test_end_time_calculated_correctly(self):
        """
        end_time = start_time + service_duration + cleanup_duration.
        service_a=60min + cleanup=15min -> 75min total from 10:00 -> 11:15.
        """
        data = self._booking_payload(start_time="10:00:00")
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        end_time_str = response.data["time_slot_details"]["end_time"]
        self.assertTrue(
            end_time_str.startswith("11:15"),
            msg=f"Expected end time ~11:15, got {end_time_str}",
        )
