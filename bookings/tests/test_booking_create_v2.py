import uuid
from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from bookings.models import Booking, TimeSlot
from promotions.models import GiftCard
from spacenter.models import City, Country, Room, Service, ServiceArrangement, Specialty, SpaCenter

User = get_user_model()


class BookingCreateV2Tests(APITestCase):
    def setUp(self):
        # Create location
        self.country = Country.objects.create(name="Qatar", code="QAT", phone_code="+974")
        self.city = City.objects.create(country=self.country, name="Doha")

        # Create specialty
        self.specialty = Specialty.objects.create(name="Massage")

        # Create spa center
        self.spa_center = SpaCenter.objects.create(
            name="Main Spa",
            slug="main-spa",
            country=self.country,
            city=self.city,
            address="Corniche",
        )

        # Create room
        self.room = Room.objects.create(
            spa_center=self.spa_center,
            room_id="101",
            name="Room 101",
        )

        # Create service
        self.service = Service.objects.create(
            name="Swedish Massage",
            specialty=self.specialty,
            country=self.country,
            city=self.city,
            duration_minutes=60,
            base_price=Decimal("100.00"),
            spa_center=self.spa_center,
        )

        # Create arrangement — restrict to self.service only
        self.arrangement = ServiceArrangement.objects.create(
            spa_center=self.spa_center,
            room=self.room,
            arrangement_type=ServiceArrangement.ArrangementType.SINGLE_ROOM,
            arrangement_label="Room 101 Arrangement",
            base_price=Decimal("100.00"),
            allows_all_services=False,
        )
        self.arrangement.allowed_services.add(self.service)

        # Create customer
        self.customer = User.objects.create_user(
            email="customer@example.com", password="password123", user_type="customer", phone_number="+97455001007"
        )
        self.client.force_authenticate(user=self.customer)

        self.url = "/api/v1/bookings/"

    def test_create_booking_with_explicit_arrangement_id(self):
        """Test booking with service_arrangement_id."""
        tomorrow = date.today() + timedelta(days=1)
        data = {
            "service": str(self.service.id),
            "spa_center": str(self.spa_center.id),
            "date": tomorrow.isoformat(),
            "start_time": "10:00:00",
            "service_arrangement_id": str(self.arrangement.id),
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["service_arrangement"], self.arrangement.id)
        
        booking = Booking.objects.get(id=response.data["id"])
        self.assertEqual(booking.service_arrangement, self.arrangement)
        self.assertEqual(booking.total_price, Decimal("100.00"))

    def test_multi_booking_capacity(self):
        """Test that only one booking is allowed on the room-based arrangement."""
        tomorrow = date.today() + timedelta(days=1)
        data = {
            "service": str(self.service.id),
            "spa_center": str(self.spa_center.id),
            "date": tomorrow.isoformat(),
            "start_time": "14:00:00",
            "service_arrangement_id": str(self.arrangement.id),
        }

        # First booking - should succeed
        response1 = self.client.post(self.url, data)
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Second booking - should fail (capacity is 1)
        response2 = self.client.post(self.url, data)
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Selected arrangement has no available space", str(response2.data))

    def test_invalid_arrangement_id(self):
        """Test error when arrangement ID doesn't match service/spa."""
        other_service = Service.objects.create(
            name="Other",
            specialty=self.specialty,
            country=self.country,
            city=self.city,
            base_price=50,
            spa_center=self.spa_center,
        )
        tomorrow = date.today() + timedelta(days=1)
        data = {
            "service": str(other_service.id), # Mismatch
            "spa_center": str(self.spa_center.id),
            "date": tomorrow.isoformat(),
            "start_time": "15:00:00",
            "service_arrangement_id": str(self.arrangement.id),
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("service_arrangement_id", response.data)

    def test_missing_arrangement_id(self):
        """Test error when arrangement ID is missing."""
        tomorrow = date.today() + timedelta(days=1)
        data = {
            "service": str(self.service.id),
            "spa_center": str(self.spa_center.id),
            "date": tomorrow.isoformat(),
            "start_time": "16:00:00",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("service_arrangement_id", response.data)
