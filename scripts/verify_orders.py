import os
import sys
import django
from decimal import Decimal

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate
from orders.views import CartViewSet, OrderViewSet
from spacenter.models import SpaCenter, Country, City, SpaProduct, BaseProduct, ProductCategory
from promotions.models import Voucher

User = get_user_model()

def run_verification():
    print("--- Starting Orders App Verification ---")

    factory = APIRequestFactory()

    # 1. Setup Data
    print("\n1. Setting up test data...")
    user, _ = User.objects.get_or_create(email="testuser@example.com", defaults={
        "first_name": "Test", 
        "last_name": "User",
        "password": "password123"
    })
    
    country, _ = Country.objects.get_or_create(name="Test Country", code="TC")
    city, _ = City.objects.get_or_create(name="Test City", country=country)
    
    category, _ = ProductCategory.objects.get_or_create(name="Test Category")
    base_product, _ = BaseProduct.objects.get_or_create(
        sku="TEST-SKU-001",
        defaults={"name": "Test Product", "category": "Test Category"}
    )
    
    if not base_product.name:
         base_product.name = "Test Product"
         base_product.category = "Test Category"
         base_product.save()

    spa_product, _ = SpaProduct.objects.get_or_create(
        product=base_product,
        country=country,
        city=city,
        defaults={
            "price": Decimal("100.00"),
            "quantity": 10
        }
    )
    # Ensure stock is reset for test run
    spa_product.quantity = 10
    spa_product.reserved_quantity = 0
    spa_product.save()

    voucher, _ = Voucher.objects.get_or_create(
        code="TESTVOUCHER",
        defaults={
            "discount_type": Voucher.DiscountType.PERCENTAGE,
            "discount_value": Decimal("10.00"),
            "valid_from": "2020-01-01",
            "valid_until": "2030-01-01",
            "status": Voucher.Status.ACTIVE,
            "minimum_purchase": Decimal("0.00"),
            "max_uses": 100,
            # "expiration_date" was wrong, using valid_until which is already set above
        }
    )
    
    # Refresh logic for voucher dates
    if not voucher.code:
        voucher.code = "TESTVOUCHER"
        voucher.save()

    print(f"User: {user}")
    print(f"SPA Product: {spa_product} (Qty: {spa_product.quantity})")
    print(f"Voucher: {voucher.code}")

    # 2. Test Cart - Add Item
    print("\n2. Testing Add to Cart...")
    view = CartViewSet.as_view({'post': 'add_item'})
    # Need to mock request properly
    request = factory.post(
        '/api/v1/orders/cart/add_item/', 
        data={'product_id': spa_product.id, 'quantity': 2},
        format='json'
    )
    force_authenticate(request, user=user)
    response = view(request)
    
    print(f"Add Item Product ID: {spa_product.id}")
    if response.status_code == 200:
        print(f"Cart Updated: {response.data}")
    else:
        print(f"Error Adding to Cart: {response.status_code} - {response.data}")

    # 3. Test Checkout with Voucher
    print("\n3. Testing Checkout with Voucher...")
    checkout_view = OrderViewSet.as_view({'post': 'checkout'})
    checkout_data = {
        'payment_method': 'card',
        'voucher_code': 'TESTVOUCHER'
    }
    request = factory.post(
        '/api/v1/orders/orders/checkout/', 
        data=checkout_data,
        format='json'
    )
    force_authenticate(request, user=user)
    response = checkout_view(request)
    
    if response.status_code == 201:
        order_data = response.data
        print(f"Order Created Successfully: {order_data['order_number']}")
        print(f"Total Amount: {order_data['total_amount']}")
        print(f"Discount Amount: {order_data['discount_amount']}")
        print(f"Final Amount: {order_data['final_amount']}")
        
        # Verify Stock Deduction
        spa_product.refresh_from_db()
        print(f"Remaining Stock: {spa_product.quantity} (Expected 8)")
    else:
        print(f"Checkout Failed: {response.status_code} - {response.data}")

    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    run_verification()
