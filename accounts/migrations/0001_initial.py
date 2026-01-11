# Generated migration for accounts app

import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import phonenumber_field.modelfields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('email', models.EmailField(blank=True, db_index=True, max_length=254, null=True, unique=True, verbose_name='email address')),
                ('phone_number', phonenumber_field.modelfields.PhoneNumberField(blank=True, db_index=True, max_length=128, null=True, region=None, unique=True, verbose_name='phone number')),
                ('first_name', models.CharField(max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(max_length=150, verbose_name='last name')),
                ('date_of_birth', models.DateField(blank=True, null=True, verbose_name='date of birth')),
                ('user_type', models.CharField(choices=[('admin', 'Admin'), ('employee', 'Employee'), ('customer', 'Customer')], db_index=True, default='customer', max_length=20, verbose_name='user type')),
                ('is_email_verified', models.BooleanField(default=False, verbose_name='email verified')),
                ('is_phone_verified', models.BooleanField(default=False, verbose_name='phone verified')),
                ('is_active', models.BooleanField(default=True, verbose_name='active')),
                ('is_staff', models.BooleanField(default=False, verbose_name='staff status')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='updated at')),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'ordering': ['-date_joined'],
            },
        ),
        migrations.CreateModel(
            name='VerificationCode',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('code', models.CharField(max_length=10, verbose_name='verification code')),
                ('verification_type', models.CharField(choices=[('email', 'Email'), ('phone', 'Phone'), ('password_reset', 'Password Reset')], max_length=20, verbose_name='verification type')),
                ('is_used', models.BooleanField(default=False, verbose_name='is used')),
                ('attempts', models.PositiveIntegerField(default=0, verbose_name='attempts')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('expires_at', models.DateTimeField(verbose_name='expires at')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='verification_codes', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'verification code',
                'verbose_name_plural': 'verification codes',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SocialAuthProvider',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('provider', models.CharField(choices=[('google', 'Google'), ('facebook', 'Facebook')], max_length=20, verbose_name='provider')),
                ('provider_user_id', models.CharField(max_length=255, verbose_name='provider user ID')),
                ('access_token', models.TextField(blank=True, verbose_name='access token')),
                ('refresh_token', models.TextField(blank=True, verbose_name='refresh token')),
                ('token_expires_at', models.DateTimeField(null=True, verbose_name='token expires at')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='updated at')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='social_providers', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'social auth provider',
                'verbose_name_plural': 'social auth providers',
                'unique_together': {('user', 'provider')},
            },
        ),
        migrations.AddConstraint(
            model_name='user',
            constraint=models.CheckConstraint(check=models.Q(('email__isnull', False)) | models.Q(('phone_number__isnull', False)), name='email_or_phone_required'),
        ),
    ]
