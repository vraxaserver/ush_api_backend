"""
Seed products and home services with Arabic translations.

Seeds:
  - Product categories (5)
  - Base products with images (6)
  - Spa products per country (stock per location)
  - Home services per city with images (8 service types × 15 cities)

Usage:
    python manage.py seed_products_homeservices           # Seed (additive)
    python manage.py seed_products_homeservices --clear    # Clear + re-seed
"""

import io
import random
import urllib.request
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from spacenter.models import (
    BaseProduct,
    City,
    Country,
    HomeService,
    ProductCategory,
    Specialty,
    SpaProduct,
)


def _make_placeholder_image(label="Product", width=800, height=600, color=(64, 130, 150)):
    """Generate a simple placeholder PNG image in memory."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new("RGB", (width, height), color=color)
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 36)
        except (IOError, OSError):
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), label, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((width - tw) / 2, (height - th) / 2), label, fill="white", font=font)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except ImportError:
        import struct, zlib
        def _minimal_png(r, g, b):
            raw = b"\x00" + bytes([r, g, b])
            return (b"\x89PNG\r\n\x1a\n"
                    + b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
                    + struct.pack(">I", len(zlib.compress(raw)) + 0) + b"IDAT" + zlib.compress(raw)
                    + struct.pack(">I", zlib.crc32(b"IDAT" + zlib.compress(raw)) & 0xFFFFFFFF)
                    + b"\x00\x00\x00\x00IEND\xaeB`\x82")
        return _minimal_png(*color)


def _download_image(url, timeout=15):
    """Download an image from a URL. Returns bytes or None on failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════
# DATA – Product Categories
# ═══════════════════════════════════════════════════════════════════

PRODUCT_CATEGORIES = [
    {"name_en": "Skincare",      "name_ar": "العناية بالبشرة",  "desc_en": "Professional skincare products for face and body.",       "desc_ar": "منتجات احترافية للعناية بالبشرة للوجه والجسم."},
    {"name_en": "Body Care",     "name_ar": "العناية بالجسم",   "desc_en": "Lotions, oils, and body treatment products.",             "desc_ar": "لوشن وزيوت ومنتجات العناية بالجسم."},
    {"name_en": "Aromatherapy",  "name_ar": "العلاج بالروائح",  "desc_en": "Essential oils, diffusers, and aromatherapy accessories.", "desc_ar": "زيوت عطرية وموزعات وإكسسوارات العلاج بالروائح."},
    {"name_en": "Hair Care",     "name_ar": "العناية بالشعر",   "desc_en": "Premium hair care and scalp treatment products.",         "desc_ar": "منتجات فاخرة للعناية بالشعر وعلاج فروة الرأس."},
    {"name_en": "Wellness",      "name_ar": "العافية",          "desc_en": "Health supplements, teas, and wellness accessories.",     "desc_ar": "مكملات صحية وشاي وإكسسوارات العافية."},
]

# ═══════════════════════════════════════════════════════════════════
# DATA – Base Products
# ═══════════════════════════════════════════════════════════════════

BASE_PRODUCTS = [
    {"name_en": "Lavender Dream Essential Oil",  "name_ar": "زيت اللافندر الأساسي",        "short_en": "Pure lavender essential oil for relaxation.",              "short_ar": "زيت لافندر نقي للاسترخاء.",                  "type": "retail",     "cat": "Aromatherapy",  "brand": "AromaPure",  "sku": "AP-LAV-001", "organic": True,  "aroma": True,  "featured": True},
    {"name_en": "Deep Hydration Face Serum",     "name_ar": "سيروم الترطيب العميق",        "short_en": "Hyaluronic acid serum for intense hydration.",             "short_ar": "سيروم حمض الهيالورونيك للترطيب المكثف.",     "type": "retail",     "cat": "Skincare",      "brand": "GlowLab",    "sku": "GL-SER-001", "organic": False, "aroma": False, "featured": True,  "sensitive": True},
    {"name_en": "Coconut Body Butter",           "name_ar": "زبدة جوز الهند للجسم",        "short_en": "Rich coconut body butter for silky smooth skin.",         "short_ar": "زبدة جوز هند غنية لبشرة ناعمة كالحرير.",    "type": "retail",     "cat": "Body Care",     "brand": "NaturaSpa",  "sku": "NS-BOD-001", "organic": True,  "aroma": False, "featured": False},
    {"name_en": "Eucalyptus Steam Inhaler",      "name_ar": "مستنشق بخار الأوكالبتوس",     "short_en": "Eucalyptus blend for steam rooms and saunas.",            "short_ar": "مزيج أوكالبتوس لغرف البخار والساونا.",       "type": "consumable", "cat": "Aromatherapy",  "brand": "AromaPure",  "sku": "AP-EUC-002", "organic": False, "aroma": True,  "featured": False},
    {"name_en": "Spa Scalp Treatment Oil",       "name_ar": "زيت علاج فروة الرأس",         "short_en": "Nourishing scalp oil with tea tree and peppermint.",      "short_ar": "زيت مغذي لفروة الرأس بشجرة الشاي والنعناع.","type": "retail",     "cat": "Hair Care",     "brand": "HairZen",    "sku": "HZ-SCA-001", "organic": True,  "aroma": False, "featured": False},
    {"name_en": "Relaxation Herbal Tea Set",     "name_ar": "مجموعة شاي الأعشاب للاسترخاء","short_en": "Curated calming herbal teas – chamomile, lemongrass.",     "short_ar": "شاي أعشاب مهدئ - بابونج وعشبة الليمون.",     "type": "retail",     "cat": "Wellness",      "brand": "ZenLeaf",    "sku": "ZL-TEA-001", "organic": True,  "aroma": False, "featured": True},
]

# Real product images from Pexels (free, high-quality)
PRODUCT_IMAGE_URLS = {
    "AP-LAV-001": "https://images.pexels.com/photos/932577/pexels-photo-932577.jpeg?auto=compress&cs=tinysrgb&w=800&h=600&dpr=1",
    "GL-SER-001": "https://images.pexels.com/photos/3685530/pexels-photo-3685530.jpeg?auto=compress&cs=tinysrgb&w=800&h=600&dpr=1",
    "NS-BOD-001": "https://images.pexels.com/photos/725998/pexels-photo-725998.jpeg?auto=compress&cs=tinysrgb&w=800&h=600&dpr=1",
    "AP-EUC-002": "https://images.pexels.com/photos/4041392/pexels-photo-4041392.jpeg?auto=compress&cs=tinysrgb&w=800&h=600&dpr=1",
    "HZ-SCA-001": "https://images.pexels.com/photos/3993398/pexels-photo-3993398.jpeg?auto=compress&cs=tinysrgb&w=800&h=600&dpr=1",
    "ZL-TEA-001": "https://images.pexels.com/photos/1417945/pexels-photo-1417945.jpeg?auto=compress&cs=tinysrgb&w=800&h=600&dpr=1",
}

# Fallback colors for product placeholder images
PRODUCT_COLORS = {
    "AP-LAV-001": (140, 100, 180),
    "GL-SER-001": (100, 160, 200),
    "NS-BOD-001": (160, 130, 90),
    "AP-EUC-002": (80, 150, 120),
    "HZ-SCA-001": (120, 100, 140),
    "ZL-TEA-001": (100, 140, 80),
}

# ═══════════════════════════════════════════════════════════════════
# DATA – Home Services
# ═══════════════════════════════════════════════════════════════════

HOME_SERVICES = [
    {"name_en": "Home Swedish Massage",          "name_ar": "مساج سويدي منزلي",              "spec": "Swedish Massage",     "dur": 60,  "price": Decimal("400"),  "disc": Decimal("349"),  "desc_en": "A relaxing full-body Swedish massage delivered to your doorstep.",                               "desc_ar": "مساج سويدي مريح لكامل الجسم يُقدَّم في منزلك."},
    {"name_en": "Home Deep Tissue Massage",      "name_ar": "مساج أنسجة عميقة منزلي",        "spec": "Deep Tissue Massage",  "dur": 90,  "price": Decimal("500"),  "disc": None,            "desc_en": "Intensive deep tissue massage targeting chronic pain, at your location.",                        "desc_ar": "مساج مكثف للأنسجة العميقة يستهدف الآلام المزمنة في موقعك."},
    {"name_en": "Home Aromatherapy Session",     "name_ar": "جلسة علاج بالروائح منزلية",     "spec": "Aromatherapy",         "dur": 75,  "price": Decimal("450"),  "disc": Decimal("399"),  "desc_en": "Luxurious aromatherapy experience with essential oils in the comfort of your home.",              "desc_ar": "تجربة علاج بالروائح الفاخرة بالزيوت العطرية في راحة منزلك."},
    {"name_en": "Home Hot Stone Therapy",        "name_ar": "علاج بالأحجار الساخنة منزلي",   "spec": "Hot Stone Therapy",    "dur": 90,  "price": Decimal("550"),  "disc": Decimal("499"),  "desc_en": "Heated volcanic stones combined with massage techniques, brought to your home.",                  "desc_ar": "أحجار بركانية ساخنة مع تقنيات المساج تُقدَّم في منزلك."},
    {"name_en": "Home Facial Treatment",         "name_ar": "علاج الوجه المنزلي",            "spec": "Facial Treatment",     "dur": 60,  "price": Decimal("350"),  "disc": None,            "desc_en": "Professional facial treatment including cleansing, exfoliation, and hydration at home.",          "desc_ar": "علاج وجه احترافي يشمل التنظيف والتقشير والترطيب في المنزل."},
    {"name_en": "Home Thai Massage",             "name_ar": "مساج تايلندي منزلي",            "spec": "Thai Massage",         "dur": 90,  "price": Decimal("420"),  "disc": None,            "desc_en": "Traditional Thai stretching and acupressure massage delivered to your location.",                 "desc_ar": "مساج تايلندي تقليدي بالتمدد والضغط يُقدَّم في موقعك."},
    {"name_en": "Home Reflexology Session",      "name_ar": "جلسة ريفلكسولوجي منزلية",      "spec": "Reflexology",          "dur": 45,  "price": Decimal("280"),  "disc": Decimal("249"),  "desc_en": "Targeted pressure on feet and hands for holistic healing, in your home.",                        "desc_ar": "ضغط مستهدف على القدمين واليدين للعلاج الشامل في منزلك."},
    {"name_en": "Home Body Scrub & Wrap",        "name_ar": "تقشير ولف الجسم منزلي",        "spec": "Body Scrub & Wrap",    "dur": 90,  "price": Decimal("480"),  "disc": Decimal("429"),  "desc_en": "Full-body exfoliation and mineral wrap for detoxification, performed at your home.",              "desc_ar": "تقشير كامل للجسم ولف بالمعادن لإزالة السموم يُجرى في منزلك."},
]

# Real home-service / spa images from Pexels
HOME_SERVICE_IMAGE_URLS = {
    "Home Swedish Massage":     "https://images.pexels.com/photos/3757993/pexels-photo-3757993.jpeg?auto=compress&cs=tinysrgb&w=800&h=600&dpr=1",
    "Home Deep Tissue Massage": "https://images.pexels.com/photos/3764568/pexels-photo-3764568.jpeg?auto=compress&cs=tinysrgb&w=800&h=600&dpr=1",
    "Home Aromatherapy Session":"https://images.pexels.com/photos/3865676/pexels-photo-3865676.jpeg?auto=compress&cs=tinysrgb&w=800&h=600&dpr=1",
    "Home Hot Stone Therapy":   "https://images.pexels.com/photos/3188585/pexels-photo-3188585.jpeg?auto=compress&cs=tinysrgb&w=800&h=600&dpr=1",
    "Home Facial Treatment":    "https://images.pexels.com/photos/3985329/pexels-photo-3985329.jpeg?auto=compress&cs=tinysrgb&w=800&h=600&dpr=1",
    "Home Thai Massage":        "https://images.pexels.com/photos/5794058/pexels-photo-5794058.jpeg?auto=compress&cs=tinysrgb&w=800&h=600&dpr=1",
    "Home Reflexology Session": "https://images.pexels.com/photos/3737832/pexels-photo-3737832.jpeg?auto=compress&cs=tinysrgb&w=800&h=600&dpr=1",
    "Home Body Scrub & Wrap":   "https://images.pexels.com/photos/3737821/pexels-photo-3737821.jpeg?auto=compress&cs=tinysrgb&w=800&h=600&dpr=1",
}

HOME_SERVICE_COLORS = {
    "Home Swedish Massage":      (100, 160, 200),
    "Home Deep Tissue Massage":  (80, 100, 140),
    "Home Aromatherapy Session": (160, 120, 180),
    "Home Hot Stone Therapy":    (180, 100, 80),
    "Home Facial Treatment":     (200, 170, 150),
    "Home Thai Massage":         (200, 160, 80),
    "Home Reflexology Session":  (100, 150, 150),
    "Home Body Scrub & Wrap":    (120, 170, 130),
}

# Gender options: male-only, female-only, or both
GENDER_OPTIONS = [
    (True, False),   # male only
    (False, True),   # female only
    (True, True),    # both
]

CURRENCY_MAP = {"QAT": "QAR", "KWT": "KWD", "ARE": "AED"}


class Command(BaseCommand):
    help = "Seed products (categories, base products, spa products) and home services with Arabic translations"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Clear existing data before seeding")

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing products and home services data...")
            # Clear in dependency order
            SpaProduct.objects.all().delete()
            BaseProduct.objects.all().delete()
            ProductCategory.objects.all().delete()
            HomeService.objects.all().delete()

        self._seed_product_categories()
        self._seed_base_products()
        self._seed_spa_products()
        self._seed_home_services()
        self.stdout.write(self.style.SUCCESS("\nProducts & home services seeding complete!"))

    # ── Product Categories ─────────────────────────────────────
    def _seed_product_categories(self):
        self.stdout.write("\nSeeding product categories...")
        for d in PRODUCT_CATEGORIES:
            obj, created = ProductCategory.objects.update_or_create(
                name_en=d["name_en"],
                defaults={"name": d["name_en"], "name_ar": d["name_ar"],
                           "description": d["desc_en"], "description_en": d["desc_en"], "description_ar": d["desc_ar"]},
            )
            self.stdout.write(f"  {'Created' if created else 'Updated'}: {obj.name}")

    # ── Base Products ──────────────────────────────────────────
    def _seed_base_products(self):
        self.stdout.write("\nSeeding base products...")
        for d in BASE_PRODUCTS:
            obj, created = BaseProduct.objects.update_or_create(
                sku=d["sku"],
                defaults={
                    "name": d["name_en"], "name_en": d["name_en"], "name_ar": d["name_ar"],
                    "short_description": d["short_en"], "short_description_en": d["short_en"], "short_description_ar": d["short_ar"],
                    "product_type": d["type"], "category": d["cat"], "brand": d["brand"],
                    "is_organic": d.get("organic", False), "is_aromatherapy": d.get("aroma", False),
                    "suitable_for_sensitive_skin": d.get("sensitive", False), "is_featured": d.get("featured", False),
                },
            )

            # Download and save product image if none exists
            if not obj.image:
                img_url = PRODUCT_IMAGE_URLS.get(d["sku"])
                img_data = None
                file_ext = "jpg"

                if img_url:
                    self.stdout.write(f"    Downloading image for: {obj.name}...")
                    img_data = _download_image(img_url)

                if not img_data:
                    color = PRODUCT_COLORS.get(d["sku"], (100, 130, 160))
                    img_data = _make_placeholder_image(d["name_en"], color=color)
                    file_ext = "png"
                    self.stdout.write(self.style.WARNING(f"    ⚠ Download failed, using placeholder for: {obj.name}"))

                fname = f"product_{obj.id}.{file_ext}"
                obj.image.save(fname, ContentFile(img_data), save=True)
                self.stdout.write(f"    Image saved for: {obj.name}")

            self.stdout.write(f"  {'Created' if created else 'Updated'}: {obj.name}")

    # ── Spa Products (stock per location) ──────────────────────
    def _seed_spa_products(self):
        self.stdout.write("\nSeeding spa products...")
        for country in Country.objects.all():
            currency = CURRENCY_MAP.get(country.code, "QAR")
            first_city = country.cities.first()
            if not first_city:
                continue
            for bp in BaseProduct.objects.all():
                obj, created = SpaProduct.objects.update_or_create(
                    product=bp, country=country, city=first_city,
                    defaults={"price": Decimal("99.00"), "currency": currency, "quantity": 50},
                )
                self.stdout.write(f"  {'Created' if created else 'Updated'}: {bp.name} @ {first_city.name}")

    # ── Home Services ──────────────────────────────────────────
    def _seed_home_services(self):
        self.stdout.write("\nSeeding home services...")

        for country in Country.objects.all().order_by("sort_order"):
            currency = CURRENCY_MAP.get(country.code, "QAR")
            for city in country.cities.all().order_by("sort_order"):
                for hs in HOME_SERVICES:
                    specialty = Specialty.objects.filter(name_en=hs["spec"]).first()
                    if not specialty:
                        self.stdout.write(self.style.WARNING(
                            f"  ⚠ Specialty '{hs['spec']}' not found, skipping: {hs['name_en']}"
                        ))
                        continue

                    gender = random.choice(GENDER_OPTIONS)
                    obj, created = HomeService.objects.update_or_create(
                        name_en=hs["name_en"], country=country, city=city,
                        defaults={
                            "name": hs["name_en"], "name_ar": hs["name_ar"],
                            "description": hs["desc_en"], "description_en": hs["desc_en"], "description_ar": hs["desc_ar"],
                            "specialty": specialty,
                            "duration_minutes": hs["dur"],
                            "price": hs["price"], "discount_price": hs["disc"],
                            "is_for_male": gender[0], "is_for_female": gender[1],
                        },
                    )

                    # Assign image if none exists
                    if not obj.image:
                        img_url = HOME_SERVICE_IMAGE_URLS.get(hs["name_en"])
                        img_data = None
                        file_ext = "jpg"

                        if img_url:
                            self.stdout.write(f"    Downloading image for: {hs['name_en']}...")
                            img_data = _download_image(img_url)

                        if not img_data:
                            color = HOME_SERVICE_COLORS.get(hs["name_en"], (100, 130, 160))
                            img_data = _make_placeholder_image(hs["name_en"], color=color)
                            file_ext = "png"
                            self.stdout.write(self.style.WARNING(
                                f"    ⚠ Download failed, using placeholder for: {hs['name_en']}"
                            ))

                        fname = f"home_service_{obj.id}.{file_ext}"
                        obj.image.save(fname, ContentFile(img_data), save=True)
                        self.stdout.write(f"    Image set for: {hs['name_en']}")

                    status = "Created" if created else "Updated"
                    self.stdout.write(f"  {status}: {obj.name} @ {city.name}, {country.name}")
