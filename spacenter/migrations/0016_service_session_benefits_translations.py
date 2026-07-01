from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('spacenter', '0015_remove_historicalservicearrangement_room_count_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalservice',
            name='session_benefits_en',
            field=models.TextField(blank=True, default=None, help_text='Free-text description of session benefits', null=True, verbose_name='session benefits'),
        ),
        migrations.AddField(
            model_name='historicalservice',
            name='session_benefits_ar',
            field=models.TextField(blank=True, default=None, help_text='Free-text description of session benefits', null=True, verbose_name='session benefits'),
        ),
        migrations.AddField(
            model_name='service',
            name='session_benefits_en',
            field=models.TextField(blank=True, default=None, help_text='Free-text description of session benefits', null=True, verbose_name='session benefits'),
        ),
        migrations.AddField(
            model_name='service',
            name='session_benefits_ar',
            field=models.TextField(blank=True, default=None, help_text='Free-text description of session benefits', null=True, verbose_name='session benefits'),
        ),
    ]
