# Generated migration for spacenter app with translation support

import uuid
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('profiles', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Country',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='country name')),
                ('name_en', models.CharField(max_length=100, null=True, unique=True, verbose_name='country name')),
                ('name_ar', models.CharField(max_length=100, null=True, unique=True, verbose_name='country name')),
                ('code', models.CharField(help_text='ISO 3166-1 alpha-3 code', max_length=3, unique=True, verbose_name='country code')),
                ('phone_code', models.CharField(blank=True, help_text='International dialing code (e.g., +1, +971)', max_length=10, verbose_name='phone code')),
                ('flag', models.ImageField(blank=True, null=True, upload_to='countries/flags/', verbose_name='flag')),
                ('is_active', models.BooleanField(default=True, verbose_name='active')),
                ('sort_order', models.PositiveIntegerField(default=0, verbose_name='sort order')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='updated at')),
            ],
            options={
                'verbose_name': 'country',
                'verbose_name_plural': 'countries',
                'ordering': ['sort_order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='City',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100, verbose_name='city name')),
                ('name_en', models.CharField(max_length=100, null=True, verbose_name='city name')),
                ('name_ar', models.CharField(max_length=100, null=True, verbose_name='city name')),
                ('state', models.CharField(blank=True, max_length=100, verbose_name='state/province')),
                ('state_en', models.CharField(blank=True, max_length=100, null=True, verbose_name='state/province')),
                ('state_ar', models.CharField(blank=True, max_length=100, null=True, verbose_name='state/province')),
                ('is_active', models.BooleanField(default=True, verbose_name='active')),
                ('sort_order', models.PositiveIntegerField(default=0, verbose_name='sort order')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='updated at')),
                ('country', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cities', to='spacenter.country', verbose_name='country')),
            ],
            options={
                'verbose_name': 'city',
                'verbose_name_plural': 'cities',
                'ordering': ['sort_order', 'name'],
                'unique_together': {('country', 'name')},
            },
        ),
        migrations.CreateModel(
            name='Specialty',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='specialty name')),
                ('name_en', models.CharField(max_length=100, null=True, unique=True, verbose_name='specialty name')),
                ('name_ar', models.CharField(max_length=100, null=True, unique=True, verbose_name='specialty name')),
                ('description', models.TextField(blank=True, verbose_name='description')),
                ('description_en', models.TextField(blank=True, null=True, verbose_name='description')),
                ('description_ar', models.TextField(blank=True, null=True, verbose_name='description')),
                ('icon', models.ImageField(blank=True, null=True, upload_to='specialties/icons/', verbose_name='icon')),
                ('is_active', models.BooleanField(default=True, verbose_name='active')),
                ('sort_order', models.PositiveIntegerField(default=0, verbose_name='sort order')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='updated at')),
            ],
            options={
                'verbose_name': 'specialty',
                'verbose_name_plural': 'specialties',
                'ordering': ['sort_order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='Service',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=150, verbose_name='service name')),
                ('name_en', models.CharField(max_length=150, null=True, verbose_name='service name')),
                ('name_ar', models.CharField(max_length=150, null=True, verbose_name='service name')),
                ('description', models.TextField(blank=True, verbose_name='description')),
                ('description_en', models.TextField(blank=True, null=True, verbose_name='description')),
                ('description_ar', models.TextField(blank=True, null=True, verbose_name='description')),
                ('duration_minutes', models.PositiveIntegerField(default=60, verbose_name='duration (minutes)')),
                ('currency', models.CharField(choices=[('USD', 'US Dollar'), ('AED', 'UAE Dirham'), ('SAR', 'Saudi Riyal'), ('QAR', 'Qatari Riyal'), ('KWD', 'Kuwaiti Dinar'), ('BHD', 'Bahraini Dinar'), ('OMR', 'Omani Rial'), ('EUR', 'Euro'), ('GBP', 'British Pound')], default='AED', max_length=3, verbose_name='currency')),
                ('base_price', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0)], verbose_name='base price')),
                ('discount_price', models.DecimalField(blank=True, decimal_places=2, help_text='Leave blank if no discount', max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(0)], verbose_name='discount price')),
                ('is_home_service', models.BooleanField(default=False, verbose_name='available for home service')),
                ('price_for_home_service', models.DecimalField(blank=True, decimal_places=2, help_text='Leave blank to use base price for home service', max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(0)], verbose_name='price for home service')),
                ('ideal_for', models.CharField(blank=True, help_text="e.g., 'Relaxation', 'Pain Relief', 'Couples'", max_length=255, verbose_name='ideal for')),
                ('ideal_for_en', models.CharField(blank=True, help_text="e.g., 'Relaxation', 'Pain Relief', 'Couples'", max_length=255, null=True, verbose_name='ideal for')),
                ('ideal_for_ar', models.CharField(blank=True, help_text="e.g., 'Relaxation', 'Pain Relief', 'Couples'", max_length=255, null=True, verbose_name='ideal for')),
                ('benefits', models.JSONField(blank=True, default=list, help_text='List of benefits as key-value pairs', verbose_name='benefits')),
                ('is_active', models.BooleanField(default=True, verbose_name='active')),
                ('sort_order', models.PositiveIntegerField(default=0, verbose_name='sort order')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='updated at')),
                ('specialty', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='services', to='spacenter.specialty', verbose_name='specialty')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_services', to=settings.AUTH_USER_MODEL, verbose_name='created by')),
            ],
            options={
                'verbose_name': 'service',
                'verbose_name_plural': 'services',
                'ordering': ['sort_order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='ServiceImage',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('image', models.ImageField(upload_to='services/images/', verbose_name='image')),
                ('alt_text', models.CharField(blank=True, max_length=255, verbose_name='alt text')),
                ('is_primary', models.BooleanField(default=False, verbose_name='primary image')),
                ('sort_order', models.PositiveIntegerField(default=0, verbose_name='sort order')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('service', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='spacenter.service', verbose_name='service')),
            ],
            options={
                'verbose_name': 'service image',
                'verbose_name_plural': 'service images',
                'ordering': ['sort_order', 'created_at'],
            },
        ),
        migrations.CreateModel(
            name='SpaCenter',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200, verbose_name='branch name')),
                ('name_en', models.CharField(max_length=200, null=True, verbose_name='branch name')),
                ('name_ar', models.CharField(max_length=200, null=True, verbose_name='branch name')),
                ('slug', models.SlugField(max_length=200, unique=True, verbose_name='slug')),
                ('description', models.TextField(blank=True, verbose_name='description')),
                ('description_en', models.TextField(blank=True, null=True, verbose_name='description')),
                ('description_ar', models.TextField(blank=True, null=True, verbose_name='description')),
                ('image', models.ImageField(blank=True, null=True, upload_to='spacenters/', verbose_name='image')),
                ('address', models.CharField(max_length=500, verbose_name='address')),
                ('address_en', models.CharField(max_length=500, null=True, verbose_name='address')),
                ('address_ar', models.CharField(max_length=500, null=True, verbose_name='address')),
                ('postal_code', models.CharField(blank=True, max_length=20, verbose_name='postal code')),
                ('latitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True, verbose_name='latitude')),
                ('longitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True, verbose_name='longitude')),
                ('phone', models.CharField(blank=True, max_length=20, verbose_name='phone')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='email')),
                ('website', models.URLField(blank=True, verbose_name='website')),
                ('default_opening_time', models.TimeField(default='09:00', verbose_name='default opening time')),
                ('default_closing_time', models.TimeField(default='21:00', verbose_name='default closing time')),
                ('is_active', models.BooleanField(default=True, verbose_name='active')),
                ('on_service', models.BooleanField(default=True, help_text='Is currently operational', verbose_name='on service')),
                ('sort_order', models.PositiveIntegerField(default=0, verbose_name='sort order')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='updated at')),
                ('branch_manager', models.OneToOneField(blank=True, limit_choices_to={'user_type': 'employee'}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='managed_spa_center', to=settings.AUTH_USER_MODEL, verbose_name='branch manager')),
                ('country', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='spa_centers', to='spacenter.country', verbose_name='country')),
                ('city', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='spa_centers', to='spacenter.city', verbose_name='city')),
                ('services', models.ManyToManyField(blank=True, related_name='spa_centers', to='spacenter.service', verbose_name='services offered')),
            ],
            options={
                'verbose_name': 'spa center',
                'verbose_name_plural': 'spa centers',
                'ordering': ['sort_order', 'country', 'name'],
            },
        ),
        migrations.CreateModel(
            name='SpaCenterOperatingHours',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('day_of_week', models.IntegerField(choices=[(0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday')], verbose_name='day of week')),
                ('opening_time', models.TimeField(verbose_name='opening time')),
                ('closing_time', models.TimeField(verbose_name='closing time')),
                ('is_closed', models.BooleanField(default=False, verbose_name='closed')),
                ('spa_center', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='operating_hours', to='spacenter.spacenter')),
            ],
            options={
                'verbose_name': 'operating hours',
                'verbose_name_plural': 'operating hours',
                'ordering': ['day_of_week'],
                'unique_together': {('spa_center', 'day_of_week')},
            },
        ),
        migrations.CreateModel(
            name='TherapistProfile',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('years_of_experience', models.PositiveIntegerField(default=0, verbose_name='years of experience')),
                ('bio', models.TextField(blank=True, verbose_name='bio')),
                ('bio_en', models.TextField(blank=True, null=True, verbose_name='bio')),
                ('bio_ar', models.TextField(blank=True, null=True, verbose_name='bio')),
                ('is_available', models.BooleanField(default=True, verbose_name='available')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='updated at')),
                ('employee_profile', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='therapist_profile', to='profiles.employeeprofile', verbose_name='employee profile')),
                ('services', models.ManyToManyField(blank=True, related_name='therapists', to='spacenter.service', verbose_name='services can perform')),
                ('spa_center', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='therapists', to='spacenter.spacenter', verbose_name='spa center')),
                ('specialties', models.ManyToManyField(blank=True, related_name='therapists', to='spacenter.specialty', verbose_name='specialties')),
            ],
            options={
                'verbose_name': 'therapist profile',
                'verbose_name_plural': 'therapist profiles',
            },
        ),
    ]
