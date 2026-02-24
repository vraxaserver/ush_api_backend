"""
Master seed command – runs all seed commands in dependency order.

Usage:
    python manage.py seed_all           # Seed everything (additive)
    python manage.py seed_all --clear   # Clear + re-seed everything
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand


# Ordered list of (app_label.command_name, display_label)
SEED_COMMANDS = [
    ("seed_users", "👤 Users (accounts)"),
    ("seed_spacenter", "🏢 Spa Centers, Services & Products (spacenter)"),
    ("seed_profiles", "📋 Profiles & Schedules (profiles)"),
    ("seed_slides", "🖼️  Slides (profiles)"),
    ("seed_promotions", "🎁 Promotions – Gift Cards"),
    ("seed_bookings", "📅 Bookings & Product Orders"),
    ("seed_payments", "💳 Payments"),
]


class Command(BaseCommand):
    help = "Run all seed commands in dependency order"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing data before seeding (passed to each sub-command)",
        )
        parser.add_argument(
            "--only",
            type=str,
            help="Run only a specific seed command (e.g., --only seed_users)",
        )
        parser.add_argument(
            "--skip",
            type=str,
            nargs="+",
            help="Skip specific seed commands (e.g., --skip seed_payments seed_bookings)",
        )

    def handle(self, *args, **options):
        clear = options["clear"]
        only = options.get("only")
        skip = set(options.get("skip") or [])

        self.stdout.write(
            self.style.HTTP_INFO(
                "\n" + "=" * 60
                + "\n   USH SPA – Database Seeder"
                + "\n" + "=" * 60
            )
        )

        if clear:
            self.stdout.write(
                self.style.WARNING("\n⚠️  Running in CLEAR mode – existing data will be deleted!\n")
            )

        commands_to_run = SEED_COMMANDS
        if only:
            commands_to_run = [(cmd, label) for cmd, label in SEED_COMMANDS if cmd == only]
            if not commands_to_run:
                self.stdout.write(
                    self.style.ERROR(f"Unknown command: {only}")
                )
                self.stdout.write(
                    "Available commands: "
                    + ", ".join(cmd for cmd, _ in SEED_COMMANDS)
                )
                return

        for command_name, label in commands_to_run:
            if command_name in skip:
                self.stdout.write(f"\n⏭️  Skipping: {label}")
                continue

            self.stdout.write(
                self.style.HTTP_INFO(f"\n{'─' * 50}\n{label}\n{'─' * 50}")
            )

            try:
                cmd_args = []
                if clear:
                    cmd_args.append("--clear")

                call_command(command_name, *cmd_args, stdout=self.stdout)

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"\n❌ Error in {command_name}: {e}")
                )
                raise

        self.stdout.write(
            self.style.SUCCESS(
                "\n" + "=" * 60
                + "\n   ✅ All seeding complete!"
                + "\n" + "=" * 60
                + "\n"
            )
        )
