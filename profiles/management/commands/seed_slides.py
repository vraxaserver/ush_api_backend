"""
Seed slides for the landing page carousel.
"""

from django.core.management.base import BaseCommand

from profiles.models import Slide


class Command(BaseCommand):
    help = "Seed slides for the landing page carousel"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing slides before seeding",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing slides...")
            Slide.objects.all().delete()

        slides_data = [
            {
                "title": "Welcome to Serenity Spa",
                "description": "Experience ultimate relaxation with our premium spa services. Book your appointment today.",
                "link": "/services",
                "order": 1,
                "is_active": True,
            },
            {
                "title": "Couples Retreat Package",
                "description": "Share a peaceful experience with your loved one. Our couples packages offer the perfect escape.",
                "link": "/services/couples",
                "order": 2,
                "is_active": True,
            },
            {
                "title": "Rejuvenating Massages",
                "description": "From Swedish to deep tissue, our expert therapists will melt away your stress.",
                "link": "/services/massage",
                "order": 3,
                "is_active": True,
            },
            {
                "title": "Gift Cards Available",
                "description": "Give the gift of relaxation. Purchase a gift card for someone special.",
                "link": "/gift-cards",
                "order": 4,
                "is_active": True,
            },
            {
                "title": "New Branch Opening",
                "description": "Visit our newest location in The Pearl. Grand opening special offers available!",
                "link": "/locations",
                "order": 5,
                "is_active": True,
            },
        ]

        created_count = 0
        for slide_info in slides_data:
            slide, created = Slide.objects.update_or_create(
                title=slide_info["title"],
                defaults=slide_info,
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"  Created slide: {slide.title}")
                )
            else:
                self.stdout.write(f"  Updated slide: {slide.title}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSlides seeding complete. Created: {created_count}, Total: {len(slides_data)}"
            )
        )
