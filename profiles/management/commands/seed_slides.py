"""
Seed slides for the landing page carousel with Arabic translations.
"""

from django.core.management.base import BaseCommand

from profiles.models import Slide


SLIDES = [
    {
        "title_en": "Welcome to USH Spa",
        "title_ar": "مرحبا بكم في يو إس إتش سبا",
        "desc_en": "Experience ultimate relaxation with our premium spa services. Book your appointment today.",
        "desc_ar": "استمتع بأقصى درجات الاسترخاء مع خدمات السبا الفاخرة لدينا. احجز موعدك اليوم.",
        "link": "/services",
    },
    {
        "title_en": "Couples Retreat Package",
        "title_ar": "باقة استرخاء الأزواج",
        "desc_en": "Share a peaceful experience with your loved one. Our couples packages offer the perfect escape.",
        "desc_ar": "شارك تجربة هادئة مع شريك حياتك. باقات الأزواج لدينا توفر الهروب المثالي.",
        "link": "/services/couples",
    },
    {
        "title_en": "Rejuvenating Massages",
        "title_ar": "مساج تجديد الحيوية",
        "desc_en": "From Swedish to deep tissue, our expert therapists will melt away your stress.",
        "desc_ar": "من المساج السويدي إلى الأنسجة العميقة، معالجونا الخبراء سيذيبون توتركم.",
        "link": "/services/massage",
    },
    {
        "title_en": "Gift Cards Available",
        "title_ar": "بطاقات الهدايا متاحة",
        "desc_en": "Give the gift of relaxation. Purchase a gift card for someone special.",
        "desc_ar": "قدّم هدية الاسترخاء. اشترِ بطاقة هدية لشخص مميز.",
        "link": "/gift-cards",
    },
    {
        "title_en": "New Branches Across the Gulf",
        "title_ar": "فروع جديدة في جميع أنحاء الخليج",
        "desc_en": "Visit our newest locations in Qatar, Kuwait, and UAE. Grand opening offers available!",
        "desc_ar": "زوروا فروعنا الجديدة في قطر والكويت والإمارات. عروض الافتتاح الكبير متاحة!",
        "link": "/locations",
    },
]


class Command(BaseCommand):
    help = "Seed slides for the landing page carousel"

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
            status = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"  {status}: {slide.title}"))

        self.stdout.write(self.style.SUCCESS(f"\n✅ Slides seeding complete! Total: {len(SLIDES)}"))
