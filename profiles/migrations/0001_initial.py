# Generated migration for profiles app

import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomerProfile',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('avatar', models.ImageField(blank=True, null=True, upload_to='avatars/customers/', verbose_name='avatar')),
                ('bio', models.TextField(blank=True, max_length=500, verbose_name='bio')),
                ('address_line_1', models.CharField(blank=True, max_length=255, verbose_name='address line 1')),
                ('address_line_2', models.CharField(blank=True, max_length=255, verbose_name='address line 2')),
                ('city', models.CharField(blank=True, max_length=100, verbose_name='city')),
                ('state', models.CharField(blank=True, max_length=100, verbose_name='state/province')),
                ('postal_code', models.CharField(blank=True, max_length=20, verbose_name='postal code')),
                ('country', models.CharField(blank=True, max_length=100, verbose_name='country')),
                ('preferred_language', models.CharField(default='en', max_length=10, verbose_name='preferred language')),
                ('notification_preferences', models.JSONField(blank=True, default=dict, verbose_name='notification preferences')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='updated at')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='customer_profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'customer profile',
                'verbose_name_plural': 'customer profiles',
            },
        ),
        migrations.CreateModel(
            name='EmployeeProfile',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('role', models.CharField(choices=[('branch_manager', 'Branch Manager'), ('country_manager', 'Country Manager'), ('therapist', 'Therapist')], db_index=True, default='therapist', max_length=30, verbose_name='role')),
                ('employee_id', models.CharField(blank=True, max_length=50, null=True, unique=True, verbose_name='employee ID')),
                ('department', models.CharField(blank=True, max_length=100, verbose_name='department')),
                ('job_title', models.CharField(blank=True, max_length=100, verbose_name='job title')),
                ('avatar', models.ImageField(blank=True, null=True, upload_to='avatars/employees/', verbose_name='avatar')),
                ('bio', models.TextField(blank=True, max_length=500, verbose_name='bio')),
                ('hire_date', models.DateField(blank=True, null=True, verbose_name='hire date')),
                ('work_location', models.CharField(blank=True, max_length=255, verbose_name='work location')),
                ('branch', models.CharField(blank=True, max_length=100, verbose_name='branch')),
                ('region', models.CharField(blank=True, max_length=100, verbose_name='region')),
                ('country', models.CharField(blank=True, max_length=100, verbose_name='country')),
                ('work_phone', models.CharField(blank=True, max_length=20, verbose_name='work phone')),
                ('work_email', models.EmailField(blank=True, max_length=254, verbose_name='work email')),
                ('certifications', models.JSONField(blank=True, default=list, verbose_name='certifications')),
                ('specializations', models.JSONField(blank=True, default=list, verbose_name='specializations')),
                ('is_available', models.BooleanField(default=True, verbose_name='is available')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='updated at')),
                ('manager', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='direct_reports', to='profiles.employeeprofile', verbose_name='manager')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='employee_profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'employee profile',
                'verbose_name_plural': 'employee profiles',
            },
        ),
        migrations.CreateModel(
            name='EmployeeSchedule',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('day_of_week', models.IntegerField(choices=[(0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday')], verbose_name='day of week')),
                ('start_time', models.TimeField(verbose_name='start time')),
                ('end_time', models.TimeField(verbose_name='end time')),
                ('is_working', models.BooleanField(default=True, verbose_name='is working')),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='schedules', to='profiles.employeeprofile')),
            ],
            options={
                'verbose_name': 'employee schedule',
                'verbose_name_plural': 'employee schedules',
                'ordering': ['day_of_week', 'start_time'],
                'unique_together': {('employee', 'day_of_week')},
            },
        ),
    ]
