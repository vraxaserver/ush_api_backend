"""
Seed slides for the landing page carousel with Arabic translations and real images.
Images are downloaded from Pexels and saved via Django's storage backend (S3 in production, local in dev).
"""

import urllib.request

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from profiles.models import Slide


# Real high-quality spa/wellness images from Pexels (free to use)
SLIDES = [
    {
        "title_en": "Welcome to USH Spa",
        "title_ar": "مرحبا بكم في يو إس إتش سبا",
        "desc_en": "Experience ultimate relaxation with our premium spa services. Book your appointment today.",
        "desc_ar": "استمتع بأقصى درجات الاسترخاء مع خدمات السبا الفاخرة لدينا. احجز موعدك اليوم.",
        "link": "/services",
        "image_url": "https://images.pexels.com/photos/3188585/pexels-photo-3188585.jpeg?auto=compress&cs=tinysrgb&w=1920&h=1080&dpr=1",
    },
    {
        "title_en": "Couples Retreat Package",
        "title_ar": "باقة استرخاء الأزواج",
        "desc_en": "Share a peaceful experience with your loved one. Our couples packages offer the perfect escape.",
        "desc_ar": "شارك تجربة هادئة مع شريك حياتك. باقات الأزواج لدينا توفر الهروب المثالي.",
        "link": "/services/couples",
        "image_url": "https://images.pexels.com/photos/3757942/pexels-photo-3757942.jpeg?auto=compress&cs=tinysrgb&w=1920&h=1080&dpr=1",
    },
    {
        "title_en": "Rejuvenating Massages",
        "title_ar": "مساج تجديد الحيوية",
        "desc_en": "From Swedish to deep tissue, our expert therapists will melt away your stress.",
        "desc_ar": "من المساج السويدي إلى الأنسجة العميقة، معالجونا الخبراء سيذيبون توتركم.",
        "link": "/services/massage",
        "image_url": "https://images.pexels.com/photos/3865676/pexels-photo-3865676.jpeg?auto=compress&cs=tinysrgb&w=1920&h=1080&dpr=1",
    },
    {
        "title_en": "Gift Cards Available",
        "title_ar": "بطاقات الهدايا متاحة",
        "desc_en": "Give the gift of relaxation. Purchase a gift card for someone special.",
        "desc_ar": "قدّم هدية الاسترخاء. اشترِ بطاقة هدية لشخص مميز.",
        "link": "/gift-cards",
        "image_url": "https://images.pexels.com/photos/3997993/pexels-photo-3997993.jpeg?auto=compress&cs=tinysrgb&w=1920&h=1080&dpr=1",
    },
    {
        "title_en": "New Branches Across the Gulf",
        "title_ar": "فروع جديدة في جميع أنحاء الخليج",
        "desc_en": "Visit our newest locations in Qatar, Kuwait, and UAE. Grand opening offers available!",
        "desc_ar": "زوروا فروعنا الجديدة في قطر والكويت والإمارات. عروض الافتتاح الكبير متاحة!",
        "link": "/locations",
        "image_url": "https://images.pexels.com/photos/261102/pexels-photo-261102.jpeg?auto=compress&cs=tinysrgb&w=1920&h=1080&dpr=1",
    },
]


def _download_image(url, timeout=15):
    """Download an image from a URL. Returns bytes or None on failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception:
        return None


class Command(BaseCommand):
    help = "Seed slides for the landing page carousel with real images"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Clear existing slides before seeding")

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing slides...")
            Slide.objects.all().delete()

        for i, s in enumerate(SLIDES, start=1):
            slide, created = Slide.objects.update_or_create(
                title_en=s["title_en"],
                defaults={
                    "title": s["title_en"],
                    "title_ar": s["title_ar"],
                    "description": s["desc_en"],
                    "description_en": s["desc_en"],
                    "description_ar": s["desc_ar"],
                    "link": s["link"],
                    "order": i,
                    "is_active": True,
                },
            )

            # Download and save image if none exists
            if not slide.image and s.get("image_url"):
                self.stdout.write(f"    Downloading image for: {slide.title}...")
                img_data = _download_image(s["image_url"])
                if img_data:
                    fname = f"slide_{slide.id}.jpg"
                    slide.image.save(fname, ContentFile(img_data), save=True)
                    self.stdout.write(f"    📷 Image saved for: {slide.title}")
                else:
                    self.stdout.write(self.style.WARNING(f"    ⚠ Download failed for: {slide.title}"))

            status = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"  {status}: {slide.title}"))

        self.stdout.write(self.style.SUCCESS(f"\n✅ Slides seeding complete! Total: {len(SLIDES)}"))
