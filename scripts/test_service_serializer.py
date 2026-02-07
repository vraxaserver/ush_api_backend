
import os
import sys
import django
import json
from datetime import date, timedelta
from django.utils import timezone

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from spacenter.models import Service, SpaCenter, ServiceArrangement
from spacenter.serializers import ServiceSerializer
from bookings.models import TimeSlot

def test_serializer():
    print("Testing ServiceSerializer...")
    
    # 1. Setup Data
    # Get or create a service
    service = Service.objects.filter(is_active=True).first()
    if not service:
        print("No active service found. Creating one...")
        service = Service.objects.create(name="Test Service", duration_minutes=60, base_price=100)
        
    # Get or create a spa center
    spa_center = SpaCenter.objects.filter(is_active=True).first()
    if not spa_center:
        print("No active spa center found. Creating one...")
        spa_center = SpaCenter.objects.create(name="Test Spa", is_active=True)
        
    # Ensure service is linked to spa center
    if not service.spa_centers.filter(id=spa_center.id).exists():
        service.spa_centers.add(spa_center)
        service.save()
        
    # Create/Get an arrangement
    arrangement1, _ = ServiceArrangement.objects.get_or_create(
        service=service,
        spa_center=spa_center,
        room_no="TEST-SER-001",
        defaults={
            "arrangement_type": ServiceArrangement.ArrangementType.SINGLE_ROOM,
            "arrangement_label": "Test Room",
            "base_price": 100,
            "is_active": True
        }
    )
    
    # Create duplicate arrangement (same type/price, different room)
    arrangement2, _ = ServiceArrangement.objects.get_or_create(
        service=service,
        spa_center=spa_center,
        room_no="TEST-SER-002",
        defaults={
            "arrangement_type": ServiceArrangement.ArrangementType.SINGLE_ROOM,
            "arrangement_label": "Test Room (duplicate)",
            "base_price": 100,
            "is_active": True
        }
    )
    
    # 2. Serialize
    serializer = ServiceSerializer(service)
    data = serializer.data
    
    # 3. Verify Structure
    print(f"Service ID: {data['id']}")
    
    if not data['branches']:
        print("ERROR: No branches found in response!")
        return

    branch = data['branches'][0]
    print(f"Branch Name: {branch['name']}")
    
    # Check Arrangements
    if 'arrangements' not in branch:
        print("ERROR: 'arrangements' key missing in branch data")
    else:
        arrs = branch['arrangements']
        print(f"Arrangements count: {len(arrs)}")
        
        # We expect 1 arrangement because both are Single Room / $100
        if len(arrs) == 1:
            print("SUCCESS: Duplicates aggregated correctly.")
            print(f"Arrangement: {arrs[0]['label']} (${arrs[0]['current_price']}) Count: {arrs[0]['count']}")
        else:
            print(f"FAILURE: Expected 1 aggregated arrangement, found {len(arrs)}")
            for a in arrs:
                print(f"  - {a['label']} ({a['type']})")
            
    # Check Availability
    if 'timeslots_availability' not in branch:
        print("ERROR: 'timeslots_availability' key missing in branch data")
    else:
        availability = branch['timeslots_availability']
        print(f"Availability Types: {list(availability.keys())}")
        
    print("\nTest Complete!")

if __name__ == "__main__":
    test_serializer()
