from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("spacenter", "0012_add_session_benefits_to_service"),
    ]

    operations = [
        migrations.AddField(
            model_name="service",
            name="booking_count",
            field=models.PositiveIntegerField(
                db_index=True,
                default=0,
                help_text="Total number of successful paid bookings for this service.",
                verbose_name="booking count",
            ),
        ),
        migrations.AddField(
            model_name="historicalservice",
            name="booking_count",
            field=models.PositiveIntegerField(
                db_index=True,
                default=0,
                help_text="Total number of successful paid bookings for this service.",
                verbose_name="booking count",
            ),
        ),
    ]
