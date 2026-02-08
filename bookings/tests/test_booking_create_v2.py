import uuid
from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from bookings.models import Booking, TimeSlot
from promotions.models import GiftCard, GiftCardTemplate, Voucher
from spacenter.models import City, Country, Service, ServiceArrangement, Specialty, SpaCenter

User = get_user_model()


class BookingCreateV2Tests(APITestCase):
    def setUp(self):
        # Create location
        self.country = Country.objects.create(name="Qatar", code="QAT", phone_code="+974")
        self.city = City.objects.create(country=self.country, name="Doha")

        # Create specialty
        self.specialty = Specialty.objects.create(name="Massage")

        # Create spa center
        self.user_manager = User.objects.create_user(
            email="manager@example.com", password="password123", user_type="employee"
        )
        self.spa_center = SpaCenter.objects.create(
            name="Main Spa",
            slug="main-spa",
            country=self.country,
            city=self.city,
            address="Corniche",
            branch_manager=self.user_manager,
        )

        # Create service
        self.service = Service.objects.create(
            name="Swedish Massage",
            specialty=self.specialty,
            country=self.country,
            city=self.city,
            duration_minutes=60,
            base_price=Decimal("100.00"),
        )
        self.spa_center.services.add(self.service)

        # Create arrangement
        self.arrangement = ServiceArrangement.objects.create(
            spa_center=self.spa_center,
            service=self.service,
            room_no="101",
            arrangement_type=ServiceArrangement.ArrangementType.SINGLE_ROOM,
            arrangement_label="Room 101",
            base_price=Decimal("100.00"),
        )

        # Create customer
        self.customer = User.objects.create_user(
            email="customer@example.com", password="password123", user_type="customer"
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

    def test_create_booking_with_voucher(self):
        """Test booking with a voucher discount."""
        voucher = Voucher.objects.create(
            code="SAVE20",
            name="Save 20%",
            discount_type=Voucher.DiscountType.PERCENTAGE,
            discount_value=Decimal("20.00"),
            valid_from=timezone.now() - timedelta(days=1),
            valid_until=timezone.now() + timedelta(days=7),
            applicable_to=Voucher.ApplicableTo.ALL,
        )
        
        tomorrow = date.today() + timedelta(days=1)
        data = {
            "service": str(self.service.id),
            "spa_center": str(self.spa_center.id),
            "date": tomorrow.isoformat(),
            "start_time": "11:00:00",
            "service_arrangement_id": str(self.arrangement.id),
            "voucher_ids": ["SAVE20"],
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        booking = Booking.objects.get(id=response.data["id"])
        self.assertEqual(booking.subtotal, Decimal("100.00"))
        self.assertEqual(booking.discount_amount, Decimal("20.00"))
        self.assertEqual(booking.total_price, Decimal("80.00"))
        self.assertIn(voucher, booking.vouchers.all())

    def test_create_booking_with_gift_card(self):
        """Test booking paid with gift card."""
        template = GiftCardTemplate.objects.create(
            name="Gift 50",
            amount=Decimal("50.00"),
            is_active=True
        )
        gift_card = GiftCard.objects.create(
            template=template,
            initial_amount=Decimal("50.00"),
            current_balance=Decimal("50.00"),
            owner=self.customer,
            valid_from=timezone.now() - timedelta(days=1),
            valid_until=timezone.now() + timedelta(days=365),
            status=GiftCard.Status.ACTIVE
        )
        
        tomorrow = date.today() + timedelta(days=1)
        data = {
            "service": str(self.service.id),
            "spa_center": str(self.spa_center.id),
            "date": tomorrow.isoformat(),
            "start_time": "12:00:00",
            "service_arrangement_id": str(self.arrangement.id),
            "gift_card_ids": [str(gift_card.id)],
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        booking = Booking.objects.get(id=response.data["id"])
        self.assertEqual(booking.subtotal, Decimal("100.00"))
        # Gift card is payment, reducing total_price in this implementation
        self.assertEqual(booking.total_price, Decimal("50.00")) 
        self.assertIn(gift_card, booking.gift_cards.all())
        
        # Check gift card balance
        gift_card.refresh_from_db()
        self.assertEqual(gift_card.current_balance, Decimal("0.00"))
        self.assertEqual(gift_card.status, GiftCard.Status.FULLY_USED)

    def test_create_booking_with_voucher_and_gift_card(self):
        """Test combined voucher and gift card usage."""
        # 20% voucher = 20 QAR discount
        Voucher.objects.create(
            code="PROMO20",
            discount_type=Voucher.DiscountType.PERCENTAGE,
            discount_value=Decimal("20.00"),
            valid_from=timezone.now() - timedelta(days=1),
            valid_until=timezone.now() + timedelta(days=7),
        )
        # 50 QAR gift card
        template = GiftCardTemplate.objects.create(amount=Decimal("50.00"))
        gift_card = GiftCard.objects.create(
            template=template,
            initial_amount=Decimal("50.00"),
            current_balance=Decimal("50.00"),
            owner=self.customer,
            valid_from=timezone.now() - timedelta(days=1),
            valid_until=timezone.now() + timedelta(days=365),
            status=GiftCard.Status.ACTIVE
        )
        
        tomorrow = date.today() + timedelta(days=1)
        data = {
            "service": str(self.service.id),
            "spa_center": str(self.spa_center.id),
            "date": tomorrow.isoformat(),
            "start_time": "14:00:00",
            "service_arrangement_id": str(self.arrangement.id),
            "voucher_ids": ["PROMO20"],
            "gift_card_ids": [str(gift_card.id)],
        }
        # Subtotal (100) - Voucher (20) = 80
        # 80 - Gift Card (50) = 30 Remaining
        
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        booking = Booking.objects.get(id=response.data["id"])
        self.assertEqual(booking.subtotal, Decimal("100.00"))
        self.assertEqual(booking.discount_amount, Decimal("20.00"))
        self.assertEqual(booking.total_price, Decimal("30.00"))
        
        gift_card.refresh_from_db()
        self.assertEqual(gift_card.current_balance, Decimal("0.00"))

    def test_invalid_arrangement_id(self):
        """Test error when arrangement ID doesn't match service/spa."""
        other_service = Service.objects.create(
            name="Other", specialty=self.specialty, country=self.country, city=self.city, base_price=50
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
