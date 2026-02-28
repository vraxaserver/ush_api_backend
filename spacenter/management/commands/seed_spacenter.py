"""
Seed spa center infrastructure with Arabic translations.

3 countries (Qatar, Kuwait, UAE) × 5 cities × 1 branch per city = 15 branches.
Each branch gets 5-10 services with images.
All translatable fields include both English and Arabic data.
"""

import io
import random
import os
import urllib.request
from datetime import time
from decimal import Decimal

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from accounts.models import User, UserType
from spacenter.models import (
    AddOnService,
    BaseProduct,
    City,
    Country,
    ProductCategory,
    Service,
    ServiceArrangement,
    ServiceImage,
    SpaCenter,
    SpaCenterOperatingHours,
    SpaProduct,
    Specialty,
)


def _make_placeholder_image(label="Spa", width=800, height=600, color=(64, 130, 150)):
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
        # Minimal 1×1 PNG fallback if Pillow unavailable
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
# DATA
# ═══════════════════════════════════════════════════════════════════

COUNTRIES = [
    {"name_en": "Qatar",                "name_ar": "قطر",                  "code": "QAT", "phone_code": "+974", "sort_order": 1},
    {"name_en": "Kuwait",               "name_ar": "الكويت",              "code": "KWT", "phone_code": "+965", "sort_order": 2},
    {"name_en": "United Arab Emirates",  "name_ar": "الإمارات العربية المتحدة", "code": "ARE", "phone_code": "+971", "sort_order": 3},
]

CITIES = {
    "QAT": [
        {"name_en": "Doha",       "name_ar": "الدوحة",     "state_en": "Ad Dawhah",  "state_ar": "الدوحة"},
        {"name_en": "Lusail",     "name_ar": "لوسيل",      "state_en": "Ad Dawhah",  "state_ar": "الدوحة"},
        {"name_en": "Al Wakrah",  "name_ar": "الوكرة",     "state_en": "Al Wakrah",  "state_ar": "الوكرة"},
        {"name_en": "Al Khor",    "name_ar": "الخور",      "state_en": "Al Khor",    "state_ar": "الخور"},
        {"name_en": "Al Rayyan",  "name_ar": "الريان",     "state_en": "Al Rayyan",  "state_ar": "الريان"},
    ],
    "KWT": [
        {"name_en": "Kuwait City",  "name_ar": "مدينة الكويت",  "state_en": "Al Asimah",  "state_ar": "العاصمة"},
        {"name_en": "Salmiya",      "name_ar": "السالمية",       "state_en": "Hawalli",    "state_ar": "حولي"},
        {"name_en": "Hawalli",      "name_ar": "حولي",           "state_en": "Hawalli",    "state_ar": "حولي"},
        {"name_en": "Jabriya",      "name_ar": "الجابرية",       "state_en": "Hawalli",    "state_ar": "حولي"},
        {"name_en": "Farwaniya",    "name_ar": "الفروانية",      "state_en": "Farwaniya",  "state_ar": "الفروانية"},
    ],
    "ARE": [
        {"name_en": "Dubai",        "name_ar": "دبي",           "state_en": "Dubai",      "state_ar": "دبي"},
        {"name_en": "Abu Dhabi",    "name_ar": "أبوظبي",        "state_en": "Abu Dhabi",  "state_ar": "أبوظبي"},
        {"name_en": "Sharjah",      "name_ar": "الشارقة",       "state_en": "Sharjah",    "state_ar": "الشارقة"},
        {"name_en": "Ajman",        "name_ar": "عجمان",         "state_en": "Ajman",      "state_ar": "عجمان"},
        {"name_en": "Ras Al Khaimah","name_ar": "رأس الخيمة",   "state_en": "RAK",        "state_ar": "رأس الخيمة"},
    ],
}

BRANCH_TEMPLATE = {
    "QAT": {"currency": "QAR", "domain": "ushspa.qa"},
    "KWT": {"currency": "KWD", "domain": "ushspa.kw"},
    "ARE": {"currency": "AED", "domain": "ushspa.ae"},
}

SPECIALTIES = [
    {"name_en": "Swedish Massage",    "name_ar": "المساج السويدي",       "desc_en": "A gentle full-body massage using long strokes, kneading, and circular movements.",                    "desc_ar": "مساج كامل للجسم باستخدام حركات طويلة وعجن ودوائر للاسترخاء والتنشيط."},
    {"name_en": "Deep Tissue Massage", "name_ar": "مساج الأنسجة العميقة", "desc_en": "Targets deeper layers of muscle and connective tissue to relieve chronic pain.",                     "desc_ar": "يستهدف الطبقات العميقة من العضلات والأنسجة الضامة لتخفيف الآلام المزمنة."},
    {"name_en": "Aromatherapy",        "name_ar": "العلاج بالروائح",      "desc_en": "Uses essential oils during massage to promote relaxation and well-being.",                            "desc_ar": "يستخدم الزيوت العطرية أثناء المساج لتعزيز الاسترخاء والرفاهية."},
    {"name_en": "Hot Stone Therapy",   "name_ar": "العلاج بالأحجار الساخنة","desc_en": "Heated stones placed on the body to ease muscle stiffness and increase circulation.",               "desc_ar": "وضع أحجار ساخنة على الجسم لتخفيف تصلب العضلات وتحسين الدورة الدموية."},
    {"name_en": "Facial Treatment",    "name_ar": "علاج الوجه",           "desc_en": "Professional skincare including cleansing, exfoliation, and moisturising.",                           "desc_ar": "علاج احترافي للبشرة يشمل التنظيف والتقشير والترطيب."},
    {"name_en": "Body Scrub & Wrap",   "name_ar": "تقشير ولف الجسم",     "desc_en": "Exfoliation and body wrapping for skin renewal and detoxification.",                                  "desc_ar": "تقشير الجسم ولفه لتجديد البشرة وإزالة السموم."},
    {"name_en": "Thai Massage",        "name_ar": "المساج التايلندي",     "desc_en": "Traditional Thai stretching and pressure-point massage for flexibility and relaxation.",              "desc_ar": "مساج تايلندي تقليدي بالتمدد ونقاط الضغط لتحسين المرونة والاسترخاء."},
    {"name_en": "Reflexology",         "name_ar": "الريفلكسولوجي",        "desc_en": "Pressure applied to feet and hands corresponding to body organs for holistic healing.",              "desc_ar": "ضغط على القدمين واليدين يتوافق مع أعضاء الجسم للعلاج الشامل."},
]

ADDON_SERVICES = [
    {"name_en": "Hot Towel Treatment",       "name_ar": "علاج المنشفة الساخنة",     "desc_en": "Warm towel application to enhance relaxation.",          "desc_ar": "تطبيق منشفة دافئة لتعزيز الاسترخاء.",         "dur": 10, "price": Decimal("25.00")},
    {"name_en": "Scalp Massage",             "name_ar": "مساج فروة الرأس",          "desc_en": "Invigorating head massage to relieve tension.",          "desc_ar": "مساج منعش للرأس لتخفيف التوتر.",               "dur": 15, "price": Decimal("35.00")},
    {"name_en": "Aromatherapy Oil Upgrade",  "name_ar": "ترقية زيت العلاج العطري",  "desc_en": "Upgrade to premium essential oils.",                     "desc_ar": "ترقية إلى الزيوت العطرية الفاخرة.",           "dur": 0,  "price": Decimal("40.00")},
    {"name_en": "Foot Soak",                 "name_ar": "نقع القدمين",              "desc_en": "Relaxing warm foot soak with essential salts.",           "desc_ar": "نقع دافئ ومريح للقدمين بأملاح عطرية.",        "dur": 10, "price": Decimal("20.00")},
    {"name_en": "Extended Session (+15 min)", "name_ar": "جلسة ممتدة (+15 دقيقة)",   "desc_en": "Add 15 extra minutes for deeper relaxation.",            "desc_ar": "أضف 15 دقيقة إضافية لاسترخاء أعمق.",          "dur": 15, "price": Decimal("50.00")},
]

# Gender options: male-only, female-only, or both (never neither)
GENDER_OPTIONS = [
    (True, False),   # male only
    (False, True),   # female only
    (True, True),    # both
]

SERVICES = [
    {"name_en": "Classic Swedish Massage",         "name_ar": "المساج السويدي الكلاسيكي",         "spec": "Swedish Massage",     "dur": 60,  "price": Decimal("350"), "disc": Decimal("299"),  "home": True,  "home_price": Decimal("450"), "ideal_en": "Relaxation, Stress Relief",          "ideal_ar": "الاسترخاء، تخفيف التوتر",             "desc_en": "A soothing full-body massage using gentle strokes to promote relaxation and ease tension.",                      "desc_ar": "مساج مهدئ لكامل الجسم بحركات لطيفة لتعزيز الاسترخاء وتخفيف التوتر."},
    {"name_en": "Deep Tissue Recovery",            "name_ar": "مساج استعادة الأنسجة العميقة",     "spec": "Deep Tissue Massage",  "dur": 90,  "price": Decimal("450"), "disc": None,            "home": False, "home_price": None,           "ideal_en": "Pain Relief, Athletes",              "ideal_ar": "تخفيف الألم، الرياضيين",              "desc_en": "Intensive massage targeting deep muscle layers to relieve chronic pain and stiffness.",                           "desc_ar": "مساج مكثف يستهدف طبقات العضلات العميقة لتخفيف الآلام المزمنة والتصلب."},
    {"name_en": "Signature Aromatherapy",          "name_ar": "تجربة العلاج بالروائح المميزة",    "spec": "Aromatherapy",         "dur": 75,  "price": Decimal("400"), "disc": Decimal("349"),  "home": True,  "home_price": Decimal("500"), "ideal_en": "Relaxation, Wellness",               "ideal_ar": "الاسترخاء، العافية",                  "desc_en": "A luxurious massage blending custom essential oils for a personalised sensory journey.",                         "desc_ar": "مساج فاخر يمزج الزيوت العطرية المخصصة لرحلة حسية شخصية."},
    {"name_en": "Volcanic Hot Stone Therapy",      "name_ar": "علاج الأحجار البركانية الساخنة",   "spec": "Hot Stone Therapy",    "dur": 90,  "price": Decimal("500"), "disc": Decimal("449"),  "home": False, "home_price": None,           "ideal_en": "Deep Relaxation, Muscle Relief",     "ideal_ar": "استرخاء عميق، راحة العضلات",          "desc_en": "Heated basalt stones placed along energy centres combined with massage techniques.",                             "desc_ar": "أحجار بازلتية ساخنة موضوعة على مراكز الطاقة مع تقنيات المساج."},
    {"name_en": "Radiance Facial Treatment",       "name_ar": "علاج الوجه المشرق",                "spec": "Facial Treatment",     "dur": 60,  "price": Decimal("300"), "disc": None,            "home": False, "home_price": None,           "ideal_en": "Skincare, Anti-Aging",               "ideal_ar": "العناية بالبشرة، مكافحة الشيخوخة",    "desc_en": "A revitalising facial including deep cleanse, exfoliation, mask, and hydration.",                                "desc_ar": "علاج وجه منعش يشمل تنظيف عميق وتقشير وقناع وترطيب."},
    {"name_en": "Detox Body Scrub & Wrap",         "name_ar": "تقشير ولف الجسم للتخلص من السموم", "spec": "Body Scrub & Wrap",    "dur": 90,  "price": Decimal("420"), "disc": Decimal("379"),  "home": False, "home_price": None,           "ideal_en": "Detox, Skin Renewal",                "ideal_ar": "إزالة السموم، تجديد البشرة",          "desc_en": "Full-body exfoliation followed by a mineral-rich body wrap for total detoxification.",                           "desc_ar": "تقشير كامل للجسم يتبعه لف بالمعادن لإزالة السموم بالكامل."},
    {"name_en": "Traditional Thai Massage",        "name_ar": "المساج التايلندي التقليدي",        "spec": "Thai Massage",         "dur": 90,  "price": Decimal("380"), "disc": None,            "home": False, "home_price": None,           "ideal_en": "Flexibility, Energy",                "ideal_ar": "المرونة، الطاقة",                     "desc_en": "An ancient healing technique combining acupressure, stretching, and yoga-like postures.",                        "desc_ar": "تقنية علاجية قديمة تجمع بين الضغط والتمدد ووضعيات تشبه اليوغا."},
    {"name_en": "Holistic Reflexology",            "name_ar": "الريفلكسولوجي الشاملة",            "spec": "Reflexology",          "dur": 45,  "price": Decimal("250"), "disc": Decimal("220"),  "home": True,  "home_price": Decimal("320"), "ideal_en": "Holistic Healing, Stress Relief",    "ideal_ar": "العلاج الشامل، تخفيف التوتر",         "desc_en": "Targeted pressure on feet and hands to restore balance and promote healing.",                                    "desc_ar": "ضغط مستهدف على القدمين واليدين لاستعادة التوازن وتعزيز الشفاء."},
    {"name_en": "Royal Hammam Experience",         "name_ar": "تجربة الحمام الملكي",              "spec": "Body Scrub & Wrap",    "dur": 120, "price": Decimal("600"), "disc": Decimal("529"),  "home": False, "home_price": None,           "ideal_en": "Luxury, Deep Cleansing",             "ideal_ar": "الفخامة، التنظيف العميق",             "desc_en": "A premium hammam ritual with steam, black soap scrub, and ghassoul clay wrap.",                                  "desc_ar": "طقوس حمام فاخرة مع بخار وتقشير بالصابون الأسود ولف بطين الغسول."},
    {"name_en": "Couples Harmony Massage",         "name_ar": "مساج الانسجام للأزواج",            "spec": "Swedish Massage",      "dur": 90,  "price": Decimal("700"), "disc": Decimal("599"),  "home": False, "home_price": None,           "ideal_en": "Couples, Romance",                   "ideal_ar": "الأزواج، الرومانسية",                 "desc_en": "Side-by-side massage for couples in a private suite with candles and rose petals.",                              "desc_ar": "مساج جنباً إلى جنب للأزواج في جناح خاص مع شموع وبتلات الورد."},
]

# Real spa service images from Pexels (free, high-quality, verified working)
SERVICE_IMAGE_URLS = {
    "Classic Swedish Massage":    "https://images.pexels.com/photos/3757993/pexels-photo-3757993.jpeg?auto=compress&cs=tinysrgb&w=800&h=600&dpr=1",
    "Deep Tissue Recovery":       "https://images.pexels.com/photos/3764568/pexels-photo-3764568.jpeg?auto=compress&cs=tinysrgb&w=800&h=600&dpr=1",
    "Signature Aromatherapy":     "https://images.pexels.com/photos/3865676/pexels-photo-3865676.jpeg?auto=compress&cs=tinysrgb&w=800&h=600&dpr=1",
    "Volcanic Hot Stone Therapy": "https://images.pexels.com/photos/3188585/pexels-photo-3188585.jpeg?auto=compress&cs=tinysrgb&w=800&h=600&dpr=1",
    "Radiance Facial Treatment":  "https://images.pexels.com/photos/3985329/pexels-photo-3985329.jpeg?auto=compress&cs=tinysrgb&w=800&h=600&dpr=1",
    "Detox Body Scrub & Wrap":    "https://images.pexels.com/photos/3737821/pexels-photo-3737821.jpeg?auto=compress&cs=tinysrgb&w=800&h=600&dpr=1",
    "Traditional Thai Massage":   "https://images.pexels.com/photos/5794058/pexels-photo-5794058.jpeg?auto=compress&cs=tinysrgb&w=800&h=600&dpr=1",
    "Holistic Reflexology":       "https://images.pexels.com/photos/3737832/pexels-photo-3737832.jpeg?auto=compress&cs=tinysrgb&w=800&h=600&dpr=1",
    "Royal Hammam Experience":    "https://images.pexels.com/photos/3997993/pexels-photo-3997993.jpeg?auto=compress&cs=tinysrgb&w=800&h=600&dpr=1",
    "Couples Harmony Massage":    "https://images.pexels.com/photos/3757942/pexels-photo-3757942.jpeg?auto=compress&cs=tinysrgb&w=800&h=600&dpr=1",
}

# Fallback colors per specialty for placeholder images (used if download fails)
SPECIALTY_COLORS = {
    "Swedish Massage": (100, 160, 200),
    "Deep Tissue Massage": (80, 100, 140),
    "Aromatherapy": (160, 120, 180),
    "Hot Stone Therapy": (180, 100, 80),
    "Facial Treatment": (200, 170, 150),
    "Body Scrub & Wrap": (120, 170, 130),
    "Thai Massage": (200, 160, 80),
    "Reflexology": (100, 150, 150),
}

PRODUCT_CATEGORIES = [
    {"name_en": "Skincare",      "name_ar": "العناية بالبشرة",  "desc_en": "Professional skincare products for face and body.",       "desc_ar": "منتجات احترافية للعناية بالبشرة للوجه والجسم."},
    {"name_en": "Body Care",     "name_ar": "العناية بالجسم",   "desc_en": "Lotions, oils, and body treatment products.",             "desc_ar": "لوشن وزيوت ومنتجات العناية بالجسم."},
    {"name_en": "Aromatherapy",  "name_ar": "العلاج بالروائح",  "desc_en": "Essential oils, diffusers, and aromatherapy accessories.","desc_ar": "زيوت عطرية وموزعات وإكسسوارات العلاج بالروائح."},
    {"name_en": "Hair Care",     "name_ar": "العناية بالشعر",   "desc_en": "Premium hair care and scalp treatment products.",        "desc_ar": "منتجات فاخرة للعناية بالشعر وعلاج فروة الرأس."},
    {"name_en": "Wellness",      "name_ar": "العافية",          "desc_en": "Health supplements, teas, and wellness accessories.",     "desc_ar": "مكملات صحية وشاي وإكسسوارات العافية."},
]

BASE_PRODUCTS = [
    {"name_en": "Lavender Dream Essential Oil",  "name_ar": "زيت اللافندر الأساسي",     "short_en": "Pure lavender essential oil for relaxation.",              "short_ar": "زيت لافندر نقي للاسترخاء.",                  "type": "retail",     "cat": "Aromatherapy",  "brand": "AromaPure",  "sku": "AP-LAV-001", "organic": True,  "aroma": True,  "featured": True},
    {"name_en": "Deep Hydration Face Serum",     "name_ar": "سيروم الترطيب العميق",     "short_en": "Hyaluronic acid serum for intense hydration.",             "short_ar": "سيروم حمض الهيالورونيك للترطيب المكثف.",     "type": "retail",     "cat": "Skincare",      "brand": "GlowLab",    "sku": "GL-SER-001", "organic": False, "aroma": False, "featured": True,  "sensitive": True},
    {"name_en": "Coconut Body Butter",           "name_ar": "زبدة جوز الهند للجسم",     "short_en": "Rich coconut body butter for silky smooth skin.",         "short_ar": "زبدة جوز هند غنية لبشرة ناعمة كالحرير.",    "type": "retail",     "cat": "Body Care",     "brand": "NaturaSpa",  "sku": "NS-BOD-001", "organic": True,  "aroma": False, "featured": False},
    {"name_en": "Eucalyptus Steam Inhaler",      "name_ar": "مستنشق بخار الأوكالبتوس",  "short_en": "Eucalyptus blend for steam rooms and saunas.",            "short_ar": "مزيج أوكالبتوس لغرف البخار والساونا.",       "type": "consumable", "cat": "Aromatherapy",  "brand": "AromaPure",  "sku": "AP-EUC-002", "organic": False, "aroma": True,  "featured": False},
    {"name_en": "Spa Scalp Treatment Oil",       "name_ar": "زيت علاج فروة الرأس",      "short_en": "Nourishing scalp oil with tea tree and peppermint.",      "short_ar": "زيت مغذي لفروة الرأس بشجرة الشاي والنعناع.","type": "retail",     "cat": "Hair Care",     "brand": "HairZen",    "sku": "HZ-SCA-001", "organic": True,  "aroma": False, "featured": False},
    {"name_en": "Relaxation Herbal Tea Set",     "name_ar": "مجموعة شاي الأعشاب للاسترخاء","short_en": "Curated calming herbal teas – chamomile, lemongrass.", "short_ar": "شاي أعشاب مهدئ - بابونج وعشبة الليمون.",     "type": "retail",     "cat": "Wellness",      "brand": "ZenLeaf",    "sku": "ZL-TEA-001", "organic": True,  "aroma": False, "featured": True},
]

DEFAULT_HOURS = [
    (0, time(9,0),  time(22,0), False),
    (1, time(9,0),  time(22,0), False),
    (2, time(9,0),  time(22,0), False),
    (3, time(9,0),  time(22,0), False),
    (4, time(14,0), time(22,0), False),  # Friday
    (5, time(10,0), time(23,0), False),
    (6, time(10,0), time(23,0), False),
]

ARRANGEMENT_TYPES = [
    ("single_room", "Single Room", "غرفة فردية", Decimal("1.0")),
    ("couple_room", "Couple Room", "غرفة أزواج",  Decimal("1.8")),
    ("vip_suite",   "VIP Suite",   "جناح VIP",    Decimal("1.5")),
]

# Real spa center / luxury interior images from Pexels (free, high-quality, verified working)
# Each city gets a unique spa/wellness/luxury interior photo
# Keyed by city name (English) for deterministic assignment
SPACENTER_IMAGE_URLS = {
    # Qatar
    "Doha":           "https://images.pexels.com/photos/3757942/pexels-photo-3757942.jpeg?auto=compress&cs=tinysrgb&w=1200&h=800&dpr=1",   # Spa pool interior
    "Lusail":          "https://images.pexels.com/photos/1579739/pexels-photo-1579739.jpeg?auto=compress&cs=tinysrgb&w=1200&h=800&dpr=1",   # Spa reception luxury
    "Al Wakrah":       "https://images.pexels.com/photos/3865676/pexels-photo-3865676.jpeg?auto=compress&cs=tinysrgb&w=1200&h=800&dpr=1",   # Wellness candles
    "Al Khor":         "https://images.pexels.com/photos/3997993/pexels-photo-3997993.jpeg?auto=compress&cs=tinysrgb&w=1200&h=800&dpr=1",   # Spa treatment room
    "Al Rayyan":       "https://images.pexels.com/photos/261102/pexels-photo-261102.jpeg?auto=compress&cs=tinysrgb&w=1200&h=800&dpr=1",     # Luxury hotel pool
    # Kuwait
    "Kuwait City":     "https://images.pexels.com/photos/3757952/pexels-photo-3757952.jpeg?auto=compress&cs=tinysrgb&w=1200&h=800&dpr=1",   # Massage table setup
    "Salmiya":         "https://images.pexels.com/photos/6585759/pexels-photo-6585759.jpeg?auto=compress&cs=tinysrgb&w=1200&h=800&dpr=1",   # Spa relaxation lounge
    "Hawalli":          "https://images.pexels.com/photos/1029604/pexels-photo-1029604.jpeg?auto=compress&cs=tinysrgb&w=1200&h=800&dpr=1",  # Zen spa stones
    "Jabriya":         "https://images.pexels.com/photos/3910071/pexels-photo-3910071.jpeg?auto=compress&cs=tinysrgb&w=1200&h=800&dpr=1",   # Candle relaxation
    "Farwaniya":       "https://images.pexels.com/photos/3735149/pexels-photo-3735149.jpeg?auto=compress&cs=tinysrgb&w=1200&h=800&dpr=1",   # Spa towels flowers
    # UAE
    "Dubai":           "https://images.pexels.com/photos/261327/pexels-photo-261327.jpeg?auto=compress&cs=tinysrgb&w=1200&h=800&dpr=1",     # Indoor pool luxury
    "Abu Dhabi":       "https://images.pexels.com/photos/2507007/pexels-photo-2507007.jpeg?auto=compress&cs=tinysrgb&w=1200&h=800&dpr=1",   # Spa entrance
    "Sharjah":         "https://images.pexels.com/photos/3225529/pexels-photo-3225529.jpeg?auto=compress&cs=tinysrgb&w=1200&h=800&dpr=1",   # Wellness retreat
    "Ajman":           "https://images.pexels.com/photos/1910472/pexels-photo-1910472.jpeg?auto=compress&cs=tinysrgb&w=1200&h=800&dpr=1",   # Luxury bathroom spa
    "Ras Al Khaimah":  "https://images.pexels.com/photos/189296/pexels-photo-189296.jpeg?auto=compress&cs=tinysrgb&w=1200&h=800&dpr=1",     # Luxury resort pool
}

# Fallback colors per city for spa center placeholder images (if download fails)
SPACENTER_COLORS = {
    "Doha": (50, 120, 160), "Lusail": (60, 130, 170), "Al Wakrah": (70, 110, 150),
    "Al Khor": (80, 140, 130), "Al Rayyan": (90, 100, 140),
    "Kuwait City": (100, 130, 120), "Salmiya": (60, 100, 150), "Hawalli": (80, 120, 160),
    "Jabriya": (70, 130, 140), "Farwaniya": (90, 110, 130),
    "Dubai": (120, 100, 170), "Abu Dhabi": (100, 110, 150), "Sharjah": (80, 130, 130),
    "Ajman": (70, 120, 140), "Ras Al Khaimah": (60, 140, 120),
}


class Command(BaseCommand):
    help = "Seed spa center data (countries, cities, centers, services, products, arrangements) with Arabic translations"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Clear existing data before seeding")

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing spa center data...")
            # Delete bookings/timeslots first (they have protected FKs to ServiceArrangement)
            from bookings.models import Booking, TimeSlot, ProductOrder, OrderItem
            for M in [OrderItem, ProductOrder, Booking, TimeSlot,
                       ServiceArrangement, ServiceImage, SpaProduct, BaseProduct, ProductCategory,
                       Service, AddOnService, Specialty, SpaCenterOperatingHours, SpaCenter, City, Country]:
                M.objects.all().delete()

        self._seed_countries()
        self._seed_cities()
        self._seed_specialties()
        self._seed_addons()
        self._seed_branches()
        self._seed_operating_hours()
        self._seed_services_with_images()
        self._seed_product_categories()
        self._seed_base_products()
        self._seed_spa_products()
        self._seed_arrangements()
        self.stdout.write(self.style.SUCCESS("\n✅ Spa center seeding complete!"))

    # ── Countries ──────────────────────────────────────────────
    def _seed_countries(self):
        self.stdout.write("\nSeeding countries...")
        for d in COUNTRIES:
            obj, created = Country.objects.update_or_create(
                code=d["code"],
                defaults={"name": d["name_en"], "name_en": d["name_en"], "name_ar": d["name_ar"],
                           "phone_code": d["phone_code"], "sort_order": d["sort_order"]},
            )
            self.stdout.write(f"  {'Created' if created else 'Updated'}: {obj.name}")

    # ── Cities ─────────────────────────────────────────────────
    def _seed_cities(self):
        self.stdout.write("\nSeeding cities...")
        for code, cities in CITIES.items():
            country = Country.objects.get(code=code)
            for i, c in enumerate(cities):
                obj, created = City.objects.update_or_create(
                    country=country, name_en=c["name_en"],
                    defaults={"name": c["name_en"], "name_ar": c["name_ar"],
                              "state": c["state_en"], "state_en": c["state_en"], "state_ar": c["state_ar"],
                              "sort_order": i + 1},
                )
                self.stdout.write(f"  {'Created' if created else 'Updated'}: {obj}")

    # ── Specialties ────────────────────────────────────────────
    def _seed_specialties(self):
        self.stdout.write("\nSeeding specialties...")
        for i, s in enumerate(SPECIALTIES):
            obj, created = Specialty.objects.update_or_create(
                name_en=s["name_en"],
                defaults={"name": s["name_en"], "name_ar": s["name_ar"],
                           "description": s["desc_en"], "description_en": s["desc_en"], "description_ar": s["desc_ar"],
                           "sort_order": i + 1},
            )
            self.stdout.write(f"  {'Created' if created else 'Updated'}: {obj.name}")

    # ── Add-Ons ────────────────────────────────────────────────
    def _seed_addons(self):
        self.stdout.write("\nSeeding add-on services...")
        for i, a in enumerate(ADDON_SERVICES):
            obj, created = AddOnService.objects.update_or_create(
                name_en=a["name_en"],
                defaults={"name": a["name_en"], "name_ar": a["name_ar"],
                           "description": a["desc_en"], "description_en": a["desc_en"], "description_ar": a["desc_ar"],
                           "duration_minutes": a["dur"], "price": a["price"], "currency": "QAR",
                           "sort_order": i + 1},
            )
            self.stdout.write(f"  {'Created' if created else 'Updated'}: {obj.name}")

    # ── Branches (5 per country) ───────────────────────────────
    def _seed_branches(self):
        self.stdout.write("\nSeeding spa center branches...")
        managers = list(User.objects.filter(user_type=UserType.EMPLOYEE).order_by("date_joined"))
        mgr_idx = 0

        for country in Country.objects.all().order_by("sort_order"):
            info = BRANCH_TEMPLATE.get(country.code, {"currency": "QAR", "domain": "ushspa.com"})
            for city in country.cities.all().order_by("sort_order"):
                slug = f"ush-spa-{city.name_en.lower().replace(' ', '-')}"
                name_en = f"USH Spa – {city.name_en}"
                name_ar = f"يو إس إتش سبا – {city.name_ar}"
                desc_en = f"Premium spa experience in {city.name_en}, {country.name_en}. World-class treatments and luxurious facilities."
                desc_ar = f"تجربة سبا فاخرة في {city.name_ar}، {country.name_ar}. علاجات عالمية المستوى ومرافق فخمة."
                addr_en = f"Main Boulevard, {city.name_en}"
                addr_ar = f"الشارع الرئيسي، {city.name_ar}"

                defaults = {
                    "name": name_en, "name_en": name_en, "name_ar": name_ar,
                    "description": desc_en, "description_en": desc_en, "description_ar": desc_ar,
                    "address": addr_en, "address_en": addr_en, "address_ar": addr_ar,
                    "country": country, "city": city,
                    "phone": f"{country.phone_code}40001234",
                    "email": f"{city.name_en.lower().replace(' ','')}@{info['domain']}",
                    "default_opening_time": time(9, 0),
                    "default_closing_time": time(22, 0),
                    "sort_order": city.sort_order,
                }
                if mgr_idx < len(managers):
                    defaults["branch_manager"] = managers[mgr_idx]
                    mgr_idx += 1

                obj, created = SpaCenter.objects.update_or_create(slug=slug, defaults=defaults)
                self.stdout.write(f"  {'Created' if created else 'Updated'}: {obj.name}")

                # Assign image to spa center if none exists
                if not obj.image:
                    img_url = SPACENTER_IMAGE_URLS.get(city.name_en)
                    img_data = None
                    file_ext = "jpg"

                    if img_url:
                        self.stdout.write(f"    Downloading image for: {obj.name}...")
                        img_data = _download_image(img_url)

                    if not img_data:
                        color = SPACENTER_COLORS.get(city.name_en, (80, 120, 150))
                        img_data = _make_placeholder_image(f"USH Spa – {city.name_en}", width=1200, height=800, color=color)
                        file_ext = "png"
                        self.stdout.write(self.style.WARNING(f"    ⚠ Download failed, using placeholder for: {obj.name}"))

                    fname = f"spacenter_{obj.id}.{file_ext}"
                    obj.image.save(fname, ContentFile(img_data), save=True)
                    self.stdout.write(f"    📷 Image set for: {obj.name}")

    # ── Operating Hours ────────────────────────────────────────
    def _seed_operating_hours(self):
        self.stdout.write("\nSeeding operating hours...")
        for spa in SpaCenter.objects.all():
            for day, opening, closing, closed in DEFAULT_HOURS:
                SpaCenterOperatingHours.objects.update_or_create(
                    spa_center=spa, day_of_week=day,
                    defaults={"opening_time": opening, "closing_time": closing, "is_closed": closed},
                )
            self.stdout.write(f"  Set hours for: {spa.name}")

    # ── Services + Images ──────────────────────────────────────
    def _seed_services_with_images(self):
        self.stdout.write("\nSeeding services with images...")
        addons = list(AddOnService.objects.all())
        admin = User.objects.filter(user_type=UserType.ADMIN).first()

        for spa in SpaCenter.objects.select_related("country", "city").all():
            # Each branch gets 5-10 services (we cycle through all 10, use 8 for variety)
            branch_services = SERVICES[:8]  # 8 services per branch
            for i, sd in enumerate(branch_services):
                specialty = Specialty.objects.get(name_en=sd["spec"])
                svc, created = Service.objects.update_or_create(
                    name_en=sd["name_en"], spa_center=spa,
                    defaults={
                        "name": sd["name_en"], "name_ar": sd["name_ar"],
                        "description": sd["desc_en"], "description_en": sd["desc_en"], "description_ar": sd["desc_ar"],
                        "ideal_for": sd["ideal_en"], "ideal_for_en": sd["ideal_en"], "ideal_for_ar": sd["ideal_ar"],
                        "specialty": specialty, "country": spa.country, "city": spa.city,
                        "duration_minutes": sd["dur"], "currency": BRANCH_TEMPLATE.get(spa.country.code, {}).get("currency", "QAR"),
                        "base_price": sd["price"], "discount_price": sd["disc"],
                        "is_for_male": (gender := random.choice(GENDER_OPTIONS))[0], "is_for_female": gender[1],
                        "is_home_service": sd["home"], "price_for_home_service": sd["home_price"],
                        "spa_center": spa, "created_by": admin, "sort_order": i + 1,
                    },
                )
                if addons:
                    svc.add_on_services.set(addons)

                # Create 1 primary image per service if none exists
                if not svc.images.exists():
                    img_url = SERVICE_IMAGE_URLS.get(sd["name_en"])
                    img_data = None
                    file_ext = "jpg"

                    if img_url:
                        self.stdout.write(f"    Downloading image for: {sd['name_en']}...")
                        img_data = _download_image(img_url)

                    if not img_data:
                        # Fallback to placeholder if download fails
                        color = SPECIALTY_COLORS.get(sd["spec"], (100, 130, 160))
                        img_data = _make_placeholder_image(sd["name_en"], color=color)
                        file_ext = "png"
                        self.stdout.write(self.style.WARNING(f"    ⚠ Download failed, using placeholder for: {sd['name_en']}"))

                    fname = f"{svc.id}.{file_ext}"
                    si = ServiceImage(service=svc, alt_text=sd["name_en"], is_primary=True, sort_order=0)
                    si.image.save(fname, ContentFile(img_data), save=True)

                status = "Created" if created else "Updated"
                self.stdout.write(f"  {status}: {svc.name} @ {spa.name}")

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
            self.stdout.write(f"  {'Created' if created else 'Updated'}: {obj.name}")

    # ── Spa Products ───────────────────────────────────────────
    def _seed_spa_products(self):
        self.stdout.write("\nSeeding spa products...")
        prices = {"QAT": "QAR", "KWT": "KWD", "ARE": "AED"}
        for country in Country.objects.all():
            currency = prices.get(country.code, "QAR")
            first_city = country.cities.first()
            if not first_city:
                continue
            for bp in BaseProduct.objects.all():
                obj, created = SpaProduct.objects.update_or_create(
                    product=bp, country=country, city=first_city,
                    defaults={"price": Decimal("99.00"), "currency": currency, "quantity": 50},
                )
                self.stdout.write(f"  {'Created' if created else 'Updated'}: {bp.name} @ {first_city.name}")

    # ── Arrangements ───────────────────────────────────────────
    def _seed_arrangements(self):
        self.stdout.write("\nSeeding service arrangements...")
        extra_minutes_choices = ["15", "30", "45", "60"]
        room_counter = 1
        for spa in SpaCenter.objects.all():
            for svc in spa.services.all():
                for arr_type, label_en, label_ar, multiplier in ARRANGEMENT_TYPES:
                    room_no = f"R-{room_counter:04d}"
                    bp = svc.base_price * multiplier
                    dp = svc.discount_price * multiplier if svc.discount_price else None
                    extra_min = random.choice(extra_minutes_choices)
                    extra_price = Decimal(str(random.randint(25, 150)))
                    obj, created = ServiceArrangement.objects.update_or_create(
                        spa_center=spa, service=svc, room_no=room_no,
                        defaults={
                            "arrangement_type": arr_type,
                            "arrangement_label": f"{label_en} – {svc.name}",
                            "cleanup_duration": 15, "base_price": bp, "discount_price": dp,
                            "extra_minutes": extra_min,
                            "price_for_extra_minutes": extra_price,
                        },
                    )
                    room_counter += 1
                self.stdout.write(f"  Arrangements for: {svc.name} @ {spa.name}")
