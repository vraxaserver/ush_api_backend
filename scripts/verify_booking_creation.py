
import os
import django
import uuid
from datetime import date, time, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from spacenter.models import SpaCenter, Service, AddOnService, TherapistProfile, ServiceArrangement
from bookings.models import Booking, TimeSlot
from bookings.serializers import BookingCreateSerializer
from rest_framework.test import APIRequestFactory

User = get_user_model()

def run_test():
    print("Starting Booking Creation Logic Verification...")
    customer, _ = User.objects.get_or_create(username='testcustomer', email='test@example.com')
    spa = SpaCenter.objects.first()
    service = Service.objects.filter(is_active=True).first()
    
    if not spa or not service:
        print("Error: Could not find SpaCenter or Service in database.")
        return

    arrangement_type = ServiceArrangement.ArrangementType.COUPLE_ROOM
    arrangement, _ = ServiceArrangement.objects.get_or_create(
        spa_center=spa, 
        service=service, 
        arrangement_type=arrangement_type, 
        room_no="TEST-101", 
        defaults={"arrangement_label": "Test Room 101", "cleanup_duration": 15, "is_active": True}
    )

    test_date = date(2026, 1, 26)
    test_time = time(10, 0)
    
    payload = {
        "arrangement_type": arrangement_type, 
        "service": str(service.id), 
        "spa_center": str(spa.id), 
        "date": test_date.isoformat(), 
        "start_time": test_time.isoformat(), 
        "add_on_services": [], 
        "customer_message": "Test booking"
    }

    factory = APIRequestFactory()
    request = factory.post('/api/v1/bookings/', payload)
    request.user = customer
    
    serializer = BookingCreateSerializer(data=payload, context={'request': request})
    
    if serializer.is_valid():
        print("Validation successful!")
        booking = serializer.save()
        print(f"Booking created: {booking.booking_number}")
        print(f"Arrangement: {booking.service_arrangement.room_no}")
        
        # Test overlap
        serializer2 = BookingCreateSerializer(data=payload, context={'request': request})
        if not serializer2.is_valid():
            print(f"Overlap check passed: {serializer2.errors['start_time'][0]}")
        else:
            print("FAILED: Overlap check did not catch duplicate.")
    else:
        print(f"Validation failed: {serializer.errors}")

if __name__ == "__main__":
    run_test()
