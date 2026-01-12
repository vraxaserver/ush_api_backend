"""
Seed Products.

Creates product categories, base products, and spa products (stock per location).
Requires: seed_locations to be run first.

Usage:
    python manage.py seed_products
    python manage.py seed_products --clear
"""

import random
from decimal import Decimal

from django.db import transaction

from spacenter.models import (
    BaseProduct,
    City,
    Country,
    ProductCategory,
    SpaProduct,
)

from .seed_base import BaseSeedCommand, CLOUD_IMAGES


# Currency mapping by country code
CURRENCY_BY_COUNTRY = {
    "UAE": "AED",
    "SAU": "SAR",
    "QAT": "QAR",
    "KWT": "KWD",
    "BHR": "BHD",
    "OMN": "OMR",
}

# Product categories data (for ProductCategory model - used in admin)
CATEGORIES_DATA = [
    {
        "name_en": "Skincare",
        "name_ar": "العناية بالبشرة",
        "description_en": "Premium skincare products for face and body",
        "description_ar": "منتجات العناية بالبشرة الفاخرة للوجه والجسم",
    },
    {
        "name_en": "Body Care",
        "name_ar": "العناية بالجسم",
        "description_en": "Luxurious body care and treatment products",
        "description_ar": "منتجات العناية الفاخرة بالجسم والعلاج",
    },
    {
        "name_en": "Aromatherapy",
        "name_ar": "العلاج بالروائح",
        "description_en": "Essential oils and aromatherapy products",
        "description_ar": "الزيوت العطرية ومنتجات العلاج بالروائح",
    },
    {
        "name_en": "Hair Care",
        "name_ar": "العناية بالشعر",
        "description_en": "Professional hair care products",
        "description_ar": "منتجات العناية بالشعر الاحترافية",
    },
    {
        "name_en": "Wellness",
        "name_ar": "الصحة والعافية",
        "description_en": "Wellness and relaxation products",
        "description_ar": "منتجات الصحة والاسترخاء",
    },
    {
        "name_en": "Oils",
        "name_ar": "الزيوت",
        "description_en": "Massage and essential oils",
        "description_ar": "زيوت التدليك والزيوت العطرية",
    },
]

# Base product templates (category is a string field)
PRODUCTS_DATA = [
    {
        "name_en": "Rejuvenating Facial Serum",
        "name_ar": "سيروم الوجه المجدد",
        "short_description_en": "Advanced anti-aging serum with vitamin C",
        "short_description_ar": "سيروم متقدم لمكافحة الشيخوخة بفيتامين سي",
        "category": "Skincare",
        "brand": "Spa Luxe",
        "product_type": "retail",
        "base_price": Decimal("189.00"),
        "discount_price": Decimal("149.00"),
        "image_key": "facial_serum",
        "is_featured": True,
        "is_organic": False,
        "is_aromatherapy": False,
        "suitable_for_sensitive_skin": True,
    },
    {
        "name_en": "Hydrating Day Moisturizer",
        "name_ar": "مرطب النهار المرطب",
        "short_description_en": "Lightweight daily moisturizer with SPF 30",
        "short_description_ar": "مرطب يومي خفيف مع عامل حماية 30",
        "category": "Skincare",
        "brand": "Spa Luxe",
        "product_type": "retail",
        "base_price": Decimal("145.00"),
        "discount_price": None,
        "image_key": "moisturizer",
        "is_featured": True,
        "is_organic": False,
        "is_aromatherapy": False,
        "suitable_for_sensitive_skin": True,
    },
    {
        "name_en": "Nourishing Body Lotion",
        "name_ar": "لوشن الجسم المغذي",
        "short_description_en": "Rich body lotion with shea butter",
        "short_description_ar": "لوشن غني للجسم بزبدة الشيا",
        "category": "Body Care",
        "brand": "Nature's Touch",
        "product_type": "retail",
        "base_price": Decimal("95.00"),
        "discount_price": Decimal("79.00"),
        "image_key": "body_lotion",
        "is_featured": False,
        "is_organic": True,
        "is_aromatherapy": False,
        "suitable_for_sensitive_skin": True,
    },
    {
        "name_en": "Relaxing Massage Oil",
        "name_ar": "زيت التدليك المريح",
        "short_description_en": "Aromatherapy massage oil blend",
        "short_description_ar": "مزيج زيت التدليك بالعلاج العطري",
        "category": "Oils",
        "brand": "Essence Spa",
        "product_type": "service_addon",
        "base_price": Decimal("120.00"),
        "discount_price": None,
        "image_key": "massage_oil",
        "is_featured": True,
        "is_organic": True,
        "is_aromatherapy": True,
        "suitable_for_sensitive_skin": True,
    },
    {
        "name_en": "Lavender Essential Oil",
        "name_ar": "زيت اللافندر العطري",
        "short_description_en": "Pure lavender essential oil",
        "short_description_ar": "زيت اللافندر العطري النقي",
        "category": "Aromatherapy",
        "brand": "Pure Essence",
        "product_type": "retail",
        "base_price": Decimal("85.00"),
        "discount_price": Decimal("69.00"),
        "image_key": "essential_oil",
        "is_featured": False,
        "is_organic": True,
        "is_aromatherapy": True,
        "suitable_for_sensitive_skin": True,
    },
    {
        "name_en": "Dead Sea Bath Salts",
        "name_ar": "أملاح البحر الميت للاستحمام",
        "short_description_en": "Mineral-rich Dead Sea bath salts",
        "short_description_ar": "أملاح الاستحمام الغنية بالمعادن من البحر الميت",
        "category": "Body Care",
        "brand": "Dead Sea Spa",
        "product_type": "consumable",
        "base_price": Decimal("75.00"),
        "discount_price": None,
        "image_key": "bath_salt",
        "is_featured": False,
        "is_organic": False,
        "is_aromatherapy": False,
        "suitable_for_sensitive_skin": True,
    },
    {
        "name_en": "Coffee Body Scrub",
        "name_ar": "مقشر الجسم بالقهوة",
        "short_description_en": "Exfoliating coffee body scrub",
        "short_description_ar": "مقشر الجسم بالقهوة المنعش",
        "category": "Body Care",
        "brand": "Nature's Touch",
        "product_type": "service_addon",
        "base_price": Decimal("110.00"),
        "discount_price": Decimal("89.00"),
        "image_key": "body_scrub",
        "is_featured": True,
        "is_organic": True,
        "is_aromatherapy": False,
        "suitable_for_sensitive_skin": False,
    },
    {
        "name_en": "Hydrating Face Mask",
        "name_ar": "قناع الوجه المرطب",
        "short_description_en": "Intensive hydrating face mask",
        "short_description_ar": "قناع الوجه المرطب المكثف",
        "category": "Skincare",
        "brand": "Spa Luxe",
        "product_type": "service_addon",
        "base_price": Decimal("65.00"),
        "discount_price": None,
        "image_key": "face_mask",
        "is_featured": False,
        "is_organic": False,
        "is_aromatherapy": False,
        "suitable_for_sensitive_skin": True,
    },
    {
        "name_en": "Argan Hair Treatment Oil",
        "name_ar": "زيت الأرجان لعلاج الشعر",
        "short_description_en": "Nourishing argan hair oil",
        "short_description_ar": "زيت الأرجان المغذي للشعر",
        "category": "Hair Care",
        "brand": "Moroccan Gold",
        "product_type": "retail",
        "base_price": Decimal("135.00"),
        "discount_price": Decimal("115.00"),
        "image_key": "shampoo",
        "is_featured": False,
        "is_organic": True,
        "is_aromatherapy": False,
        "suitable_for_sensitive_skin": True,
    },
    {
        "name_en": "Relaxation Candle",
        "name_ar": "شمعة الاسترخاء",
        "short_description_en": "Soy wax aromatherapy candle",
        "short_description_ar": "شمعة شمع الصويا للعلاج بالروائح",
        "category": "Wellness",
        "brand": "Zen Home",
        "product_type": "retail",
        "base_price": Decimal("95.00"),
        "discount_price": None,
        "image_key": "candle",
        "is_featured": True,
        "is_organic": True,
        "is_aromatherapy": True,
        "suitable_for_sensitive_skin": True,
    },
    {
        "name_en": "Ultrasonic Aroma Diffuser",
        "name_ar": "موزع العطر بالموجات فوق الصوتية",
        "short_description_en": "Modern ultrasonic essential oil diffuser",
        "short_description_ar": "موزع زيوت عطرية بالموجات فوق الصوتية",
        "category": "Aromatherapy",
        "brand": "Zen Home",
        "product_type": "retail",
        "base_price": Decimal("185.00"),
        "discount_price": Decimal("159.00"),
        "image_key": "diffuser",
        "is_featured": True,
        "is_organic": False,
        "is_aromatherapy": True,
        "suitable_for_sensitive_skin": True,
    },
    {
        "name_en": "Organic Soap Bar",
        "name_ar": "صابون عضوي",
        "short_description_en": "Handmade organic soap with olive oil",
        "short_description_ar": "صابون عضوي مصنوع يدوياً بزيت الزيتون",
        "category": "Body Care",
        "brand": "Pure Nature",
        "product_type": "consumable",
        "base_price": Decimal("35.00"),
        "discount_price": None,
        "image_key": "soap",
        "is_featured": False,
        "is_organic": True,
        "is_aromatherapy": False,
        "suitable_for_sensitive_skin": True,
    },
]


class Command(BaseSeedCommand):
    help = "Seed products with categories and stock per location"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sku_counter = 1000

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing product data before seeding",
        )

    def handle(self, *args, **options):
        # Check prerequisites
        if not Country.objects.exists():
            self.stdout.write(self.style.ERROR(
                "❌ No countries found. Run 'python manage.py seed_locations' first."
            ))
            return

        if options["clear"]:
            self.clear_data()

        with transaction.atomic():
            self.stdout.write("📦 Seeding product categories...")
            self.create_categories()

            self.stdout.write("🛍️ Seeding base products...")
            base_products = self.create_base_products()

            self.stdout.write("📍 Seeding spa products (stock per location)...")
            spa_products = self.create_spa_products(base_products)

            self.stdout.write(self.style.SUCCESS(
                f"\n✅ Products seeded: {ProductCategory.objects.count()} categories, "
                f"{len(base_products)} base products, {len(spa_products)} spa products"
            ))
            self.print_image_stats()

    def clear_data(self):
        """Clear existing product data."""
        self.stdout.write(self.style.WARNING("⚠️ Clearing products..."))
        SpaProduct.objects.all().delete()
        BaseProduct.objects.all().delete()
        ProductCategory.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("✓ Products cleared"))

    def create_categories(self):
        """Create product categories (for admin reference)."""
        for idx, data in enumerate(CATEGORIES_DATA):
            ProductCategory.objects.update_or_create(
                name_en=data["name_en"],
                defaults={
                    "name": data["name_en"],
                    "name_ar": data["name_ar"],
                    "description": data["description_en"],
                    "description_en": data["description_en"],
                    "description_ar": data["description_ar"],
                    "sort_order": idx,
                    "is_active": True,
                },
            )

        self.stdout.write(f"  Created {ProductCategory.objects.count()} categories")

    def create_base_products(self):
        """Create base products (master catalog)."""
        base_products = []

        for idx, data in enumerate(PRODUCTS_DATA):
            self.sku_counter += 1
            sku = f"SPA-{self.sku_counter}"

            product, created = BaseProduct.objects.update_or_create(
                sku=sku,
                defaults={
                    "name": data["name_en"],
                    "name_en": data["name_en"],
                    "name_ar": data["name_ar"],
                    "short_description": data["short_description_en"],
                    "short_description_en": data["short_description_en"],
                    "short_description_ar": data["short_description_ar"],
                    "product_type": data["product_type"],
                    "category": data["category"],  # CharField
                    "brand": data["brand"],
                    "status": "active",
                    "is_organic": data["is_organic"],
                    "is_aromatherapy": data["is_aromatherapy"],
                    "suitable_for_sensitive_skin": data["suitable_for_sensitive_skin"],
                    "is_featured": data["is_featured"],
                    "is_visible": True,
                },
            )

            # Download product image
            if not product.image:
                image_url = self.get_image_url("products", data["image_key"])
                if image_url:
                    image_content = self.download_image(
                        image_url,
                        f"product_{sku}.jpg"
                    )
                    if image_content:
                        product.image.save(
                            f"product_{sku}.jpg",
                            image_content,
                            save=True
                        )

            # Store base price and discount for spa product creation
            product._base_price = data["base_price"]
            product._discount_price = data["discount_price"]
            base_products.append(product)

        self.stdout.write(f"  Created {len(base_products)} base products")
        return base_products

    def create_spa_products(self, base_products):
        """Create spa products (stock per location)."""
        cities = City.objects.select_related("country").all()
        all_spa_products = []

        for city in cities:
            country = city.country
            currency = CURRENCY_BY_COUNTRY.get(country.code, "QAR")

            for product in base_products:
                spa_product, _ = SpaProduct.objects.update_or_create(
                    product=product,
                    country=country,
                    city=city,
                    defaults={
                        "price": product._base_price,
                        "discounted_price": product._discount_price,
                        "currency": currency,
                        "quantity": random.randint(10, 100),
                        "reserved_quantity": random.randint(0, 5),
                        "low_stock_threshold": 5,
                    },
                )
                all_spa_products.append(spa_product)

            self.stdout.write(
                f"    {city.name} ({country.code}): {len(base_products)} products"
            )

        return all_spa_products
