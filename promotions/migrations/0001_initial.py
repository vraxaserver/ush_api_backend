# Generated migration for Vouchers & Gift Cards

import uuid
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('spacenter', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Voucher model
        migrations.CreateModel(
            name='Voucher',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('code', models.CharField(db_index=True, help_text='Unique voucher code', max_length=50, unique=True, verbose_name='voucher code')),
                ('name', models.CharField(help_text='Internal name for this voucher', max_length=200, verbose_name='name')),
                ('description', models.TextField(blank=True, verbose_name='description')),
                ('discount_type', models.CharField(choices=[('percentage', 'Percentage'), ('fixed', 'Fixed Amount')], default='percentage', max_length=20, verbose_name='discount type')),
                ('discount_value', models.DecimalField(decimal_places=2, help_text='Percentage (0-100) or fixed amount', max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))], verbose_name='discount value')),
                ('max_discount_amount', models.DecimalField(blank=True, decimal_places=2, help_text='Cap for percentage discounts (optional)', max_digits=10, null=True, verbose_name='maximum discount')),
                ('applicable_to', models.CharField(choices=[('all', 'All Services & Products'), ('services', 'Services Only'), ('products', 'Products Only'), ('specific', 'Specific Items')], default='all', max_length=20, verbose_name='applicable to')),
                ('specific_service_ids', models.TextField(blank=True, help_text='Comma-separated service UUIDs', verbose_name='specific service IDs')),
                ('specific_product_ids', models.TextField(blank=True, help_text='Comma-separated product UUIDs (BaseProduct)', verbose_name='specific product IDs')),
                ('specific_categories', models.TextField(blank=True, help_text='Comma-separated category names', verbose_name='specific categories')),
                ('minimum_purchase', models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Minimum order amount to use this voucher', max_digits=10, verbose_name='minimum purchase')),
                ('max_uses', models.PositiveIntegerField(blank=True, help_text='Total number of times this voucher can be used', null=True, verbose_name='maximum uses')),
                ('max_uses_per_user', models.PositiveIntegerField(default=1, help_text='How many times a single user can use this voucher', verbose_name='max uses per user')),
                ('current_uses', models.PositiveIntegerField(default=0, editable=False, verbose_name='current uses')),
                ('valid_from', models.DateTimeField(verbose_name='valid from')),
                ('valid_until', models.DateTimeField(verbose_name='valid until')),
                ('first_time_only', models.BooleanField(default=False, help_text="Only for users who haven't made a purchase before", verbose_name='first-time users only')),
                ('status', models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive'), ('expired', 'Expired'), ('exhausted', 'Exhausted')], default='active', max_length=20, verbose_name='status')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='updated at')),
                ('country', models.ForeignKey(blank=True, help_text='Leave blank for all countries', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='vouchers', to='spacenter.country', verbose_name='country')),
                ('city', models.ForeignKey(blank=True, help_text='Leave blank for all cities', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='vouchers', to='spacenter.city', verbose_name='city')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_vouchers', to=settings.AUTH_USER_MODEL, verbose_name='created by')),
            ],
            options={
                'verbose_name': 'voucher',
                'verbose_name_plural': 'vouchers',
                'ordering': ['-created_at'],
            },
        ),
        # VoucherUsage model
        migrations.CreateModel(
            name='VoucherUsage',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('order_reference', models.CharField(blank=True, help_text='Reference to the order/booking', max_length=100, verbose_name='order reference')),
                ('order_type', models.CharField(blank=True, help_text='Type of order: service_booking, product_order, etc.', max_length=50, verbose_name='order type')),
                ('original_amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='original amount')),
                ('discount_amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='discount amount')),
                ('final_amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='final amount')),
                ('used_at', models.DateTimeField(auto_now_add=True, verbose_name='used at')),
                ('voucher', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='usages', to='promotions.voucher', verbose_name='voucher')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='voucher_usages', to=settings.AUTH_USER_MODEL, verbose_name='user')),
            ],
            options={
                'verbose_name': 'voucher usage',
                'verbose_name_plural': 'voucher usages',
                'ordering': ['-used_at'],
            },
        ),
        # GiftCardTemplate model
        migrations.CreateModel(
            name='GiftCardTemplate',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200, verbose_name='name')),
                ('description', models.TextField(blank=True, verbose_name='description')),
                ('image', models.ImageField(blank=True, null=True, upload_to='gift_cards/templates/', verbose_name='image')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('1.00'))], verbose_name='amount')),
                ('currency', models.CharField(default='QAR', max_length=10, verbose_name='currency')),
                ('validity_days', models.PositiveIntegerField(default=365, help_text='Number of days the gift card is valid after purchase', verbose_name='validity days')),
                ('applicable_to_services', models.BooleanField(default=True, verbose_name='applicable to services')),
                ('applicable_to_products', models.BooleanField(default=True, verbose_name='applicable to products')),
                ('is_active', models.BooleanField(default=True, verbose_name='active')),
                ('sort_order', models.PositiveIntegerField(default=0, verbose_name='sort order')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='updated at')),
                ('country', models.ForeignKey(blank=True, help_text='Leave blank for all countries', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='gift_card_templates', to='spacenter.country', verbose_name='country')),
            ],
            options={
                'verbose_name': 'gift card template',
                'verbose_name_plural': 'gift card templates',
                'ordering': ['sort_order', 'amount'],
            },
        ),
        # GiftCard model
        migrations.CreateModel(
            name='GiftCard',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('code', models.CharField(db_index=True, max_length=50, unique=True, verbose_name='gift card code')),
                ('pin', models.CharField(blank=True, help_text='Optional security PIN', max_length=10, verbose_name='PIN')),
                ('initial_amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='initial amount')),
                ('current_balance', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='current balance')),
                ('currency', models.CharField(default='QAR', max_length=10, verbose_name='currency')),
                ('recipient_email', models.EmailField(blank=True, help_text='Email to send the gift card to', max_length=254, verbose_name='recipient email')),
                ('recipient_name', models.CharField(blank=True, max_length=200, verbose_name='recipient name')),
                ('recipient_message', models.TextField(blank=True, help_text='Personal message from purchaser', verbose_name='gift message')),
                ('applicable_to_services', models.BooleanField(default=True, verbose_name='applicable to services')),
                ('applicable_to_products', models.BooleanField(default=True, verbose_name='applicable to products')),
                ('valid_from', models.DateTimeField(verbose_name='valid from')),
                ('valid_until', models.DateTimeField(verbose_name='valid until')),
                ('status', models.CharField(choices=[('pending', 'Pending Activation'), ('active', 'Active'), ('partially_used', 'Partially Used'), ('fully_used', 'Fully Used'), ('expired', 'Expired'), ('cancelled', 'Cancelled')], default='pending', max_length=20, verbose_name='status')),
                ('payment_reference', models.CharField(blank=True, max_length=100, verbose_name='payment reference')),
                ('is_transferable', models.BooleanField(default=True, help_text='Can this gift card be transferred to another user', verbose_name='transferable')),
                ('purchased_at', models.DateTimeField(blank=True, null=True, verbose_name='purchased at')),
                ('activated_at', models.DateTimeField(blank=True, null=True, verbose_name='activated at')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='updated at')),
                ('template', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='gift_cards', to='promotions.giftcardtemplate', verbose_name='template')),
                ('purchased_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='purchased_gift_cards', to=settings.AUTH_USER_MODEL, verbose_name='purchased by')),
                ('owner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='owned_gift_cards', to=settings.AUTH_USER_MODEL, verbose_name='current owner')),
                ('country', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='gift_cards', to='spacenter.country', verbose_name='country')),
            ],
            options={
                'verbose_name': 'gift card',
                'verbose_name_plural': 'gift cards',
                'ordering': ['-created_at'],
            },
        ),
        # GiftCardTransaction model
        migrations.CreateModel(
            name='GiftCardTransaction',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('transaction_type', models.CharField(choices=[('purchase', 'Purchase'), ('activation', 'Activation'), ('redemption', 'Redemption'), ('refund', 'Refund'), ('transfer', 'Transfer'), ('expiry', 'Expiry'), ('adjustment', 'Admin Adjustment')], max_length=20, verbose_name='transaction type')),
                ('amount', models.DecimalField(decimal_places=2, help_text='Positive for credit, negative for debit', max_digits=10, verbose_name='amount')),
                ('balance_after', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='balance after')),
                ('order_reference', models.CharField(blank=True, max_length=100, verbose_name='order reference')),
                ('order_type', models.CharField(blank=True, max_length=50, verbose_name='order type')),
                ('notes', models.TextField(blank=True, verbose_name='notes')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('gift_card', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='promotions.giftcard', verbose_name='gift card')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='gift_card_transactions', to=settings.AUTH_USER_MODEL, verbose_name='user')),
            ],
            options={
                'verbose_name': 'gift card transaction',
                'verbose_name_plural': 'gift card transactions',
                'ordering': ['-created_at'],
            },
        ),
        # Indexes
        migrations.AddIndex(
            model_name='voucher',
            index=models.Index(fields=['code'], name='promotio_vo_code_a1b2c3_idx'),
        ),
        migrations.AddIndex(
            model_name='voucher',
            index=models.Index(fields=['status'], name='promotio_vo_status_d4e5f6_idx'),
        ),
        migrations.AddIndex(
            model_name='voucher',
            index=models.Index(fields=['valid_from', 'valid_until'], name='promotio_vo_valid_f_g7h8i9_idx'),
        ),
        migrations.AddIndex(
            model_name='giftcard',
            index=models.Index(fields=['code'], name='promotio_gi_code_j1k2l3_idx'),
        ),
        migrations.AddIndex(
            model_name='giftcard',
            index=models.Index(fields=['status'], name='promotio_gi_status_m4n5o6_idx'),
        ),
        migrations.AddIndex(
            model_name='giftcard',
            index=models.Index(fields=['owner'], name='promotio_gi_owner_p7q8r9_idx'),
        ),
        migrations.AddIndex(
            model_name='giftcard',
            index=models.Index(fields=['valid_until'], name='promotio_gi_valid_u_s1t2u3_idx'),
        ),
    ]
