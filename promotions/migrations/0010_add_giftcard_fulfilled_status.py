import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("promotions", "0009_alter_giftcard_service_arrangement"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Add new FULFILLED choice to status field
        migrations.AlterField(
            model_name="giftcard",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending_payment", "Pending Payment"),
                    ("active", "Active"),
                    ("redeemed", "Redeemed"),
                    ("fulfilled", "Service Fulfilled"),
                    ("expired", "Expired"),
                    ("cancelled", "Cancelled"),
                ],
                default="pending_payment",
                max_length=20,
                verbose_name="status",
            ),
        ),
        # Add fulfilled_at timestamp
        migrations.AddField(
            model_name="giftcard",
            name="fulfilled_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Timestamp when the recipient visited the spa and enjoyed the service",
                null=True,
                verbose_name="fulfilled at",
            ),
        ),
        # Add fulfilled_by FK to User
        migrations.AddField(
            model_name="giftcard",
            name="fulfilled_by",
            field=models.ForeignKey(
                blank=True,
                help_text="Staff member who marked the service as fulfilled",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="fulfilled_gift_cards",
                to=settings.AUTH_USER_MODEL,
                verbose_name="fulfilled by",
            ),
        ),
    ]
