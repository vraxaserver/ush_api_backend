"""
Base Seed Utilities.

Shared utilities for seed data commands including image downloading.
"""

import requests
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand


# =============================================================================
# Cloud Image URLs (Unsplash - free to use)
# =============================================================================

CLOUD_IMAGES = {
    # Country flags (using flagcdn.com)
    "flags": {
        "UAE": "https://flagcdn.com/w320/ae.png",
        "SAU": "https://flagcdn.com/w320/sa.png",
        "QAT": "https://flagcdn.com/w320/qa.png",
        "KWT": "https://flagcdn.com/w320/kw.png",
        "BHR": "https://flagcdn.com/w320/bh.png",
        "OMN": "https://flagcdn.com/w320/om.png",
    },
    # Specialty icons (using Unsplash)
    "specialties": {
        "swedish_massage": "https://images.unsplash.com/photo-1544161515-4ab6ce6db874?w=200&h=200&fit=crop",
        "deep_tissue": "https://images.unsplash.com/photo-1519824145371-296894a0daa9?w=200&h=200&fit=crop",
        "thai_massage": "https://images.unsplash.com/photo-1600334089648-b0d9d3028eb2?w=200&h=200&fit=crop",
        "hot_stone": "https://images.unsplash.com/photo-1515377905703-c4788e51af15?w=200&h=200&fit=crop",
        "aromatherapy": "https://images.unsplash.com/photo-1507652313519-d4e9174996dd?w=200&h=200&fit=crop",
        "facial": "https://images.unsplash.com/photo-1570172619644-dfd03ed5d881?w=200&h=200&fit=crop",
        "body_scrub": "https://images.unsplash.com/photo-1540555700478-4be289fbecef?w=200&h=200&fit=crop",
        "reflexology": "https://images.unsplash.com/photo-1519823551278-64ac92734fb1?w=200&h=200&fit=crop",
    },
    # Service images (larger versions)
    "services": {
        "swedish_massage": "https://images.unsplash.com/photo-1544161515-4ab6ce6db874?w=800",
        "deep_tissue": "https://images.unsplash.com/photo-1519824145371-296894a0daa9?w=800",
        "thai_massage": "https://images.unsplash.com/photo-1600334089648-b0d9d3028eb2?w=800",
        "hot_stone": "https://images.unsplash.com/photo-1515377905703-c4788e51af15?w=800",
        "aromatherapy": "https://images.unsplash.com/photo-1507652313519-d4e9174996dd?w=800",
        "facial": "https://images.unsplash.com/photo-1570172619644-dfd03ed5d881?w=800",
        "body_scrub": "https://images.unsplash.com/photo-1540555700478-4be289fbecef?w=800",
        "reflexology": "https://images.unsplash.com/photo-1519823551278-64ac92734fb1?w=800",
        "couples": "https://images.unsplash.com/photo-1591343395082-e120087004b4?w=800",
        "sports": "https://images.unsplash.com/photo-1519824145371-296894a0daa9?w=800",
    },
    # Spa center images
    "spa_centers": {
        "spa_1": "https://images.unsplash.com/photo-1540555700478-4be289fbecef?w=800",
        "spa_2": "https://images.unsplash.com/photo-1596178060671-7a80dc8059ea?w=800",
        "spa_3": "https://images.unsplash.com/photo-1544161515-4ab6ce6db874?w=800",
        "spa_4": "https://images.unsplash.com/photo-1600334089648-b0d9d3028eb2?w=800",
        "spa_5": "https://images.unsplash.com/photo-1507652313519-d4e9174996dd?w=800",
    },
    # Employee avatars (diverse portraits)
    "avatars": {
        "female_1": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=200&h=200&fit=crop",
        "female_2": "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=200&h=200&fit=crop",
        "female_3": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200&h=200&fit=crop",
        "female_4": "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=200&h=200&fit=crop",
        "female_5": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=200&h=200&fit=crop",
        "female_6": "https://images.unsplash.com/photo-1487412720507-e7ab37603c6f?w=200&h=200&fit=crop",
        "male_1": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=200&h=200&fit=crop",
        "male_2": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&h=200&fit=crop",
        "male_3": "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=200&h=200&fit=crop",
        "male_4": "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=200&h=200&fit=crop",
    },
}


class BaseSeedCommand(BaseCommand):
    """Base command with shared utilities for seeding data."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.images_downloaded = 0
        self.images_failed = 0

    def download_image(self, url, filename, timeout=15):
        """Download image from URL and return ContentFile."""
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code == 200:
                self.images_downloaded += 1
                return ContentFile(response.content, name=filename)
            else:
                self.images_failed += 1
                self.stdout.write(self.style.WARNING(
                    f"    Failed to download {filename}: HTTP {response.status_code}"
                ))
        except requests.RequestException as e:
            self.images_failed += 1
            self.stdout.write(self.style.WARNING(
                f"    Failed to download {filename}: {e}"
            ))
        return None

    def get_image_url(self, category, key, default=None):
        """Get image URL from configuration."""
        images = CLOUD_IMAGES.get(category, {})
        return images.get(key, default)

    def print_image_stats(self):
        """Print image download statistics."""
        total = self.images_downloaded + self.images_failed
        if total > 0:
            self.stdout.write(f"    Images: {self.images_downloaded} downloaded, {self.images_failed} failed")
