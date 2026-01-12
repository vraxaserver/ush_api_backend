# Spa Center Auth & Management Microservice

A comprehensive Django REST Framework microservice for spa center management with authentication, employee management, spa services, products, therapists, and promotions (vouchers & gift cards).

## Features

### 🔐 Authentication
- **JWT Authentication** with access and refresh tokens
- **Social Authentication** (Google OAuth2, Facebook OAuth2)
- **Email/Phone Registration** with verification codes
- **Password Reset** via email or SMS
- **Role-based Access Control**

### 👥 User Types
- **Admin**: Full system access
- **Branch Manager**: Manages individual spa branches
- **Therapist**: Service provider with scheduling
- **Customer**: Self-registration, booking access

### 🏢 Spa Center Management
- **Countries & Cities**: Multi-location support (GCC region)
- **Spa Branches**: Full branch management with operating hours
- **Services**: Service catalog with categories, pricing, durations
- **Therapists**: Staff profiles with specialties and availability

### 🛍️ Products
- **Product Categories**: Organized product catalog
- **Base Products**: Master product templates
- **Spa Products**: Location-specific stock and pricing

### 🎟️ Promotions
- **Vouchers**: Discount codes (percentage/fixed)
- **Gift Cards**: Prepaid balance cards with transfer support

### 🌐 Multi-language Support
- English (EN) and Arabic (AR) translations
- Translatable fields for all content

---

## Tech Stack

- **Backend**: Django 4.2+, Django REST Framework
- **Authentication**: djangorestframework-simplejwt, dj-rest-auth, django-allauth
- **Database**: PostgreSQL
- **Async Tasks**: Celery + Redis
- **SMS**: Twilio
- **Translations**: django-modeltranslation
- **API Docs**: drf-spectacular (Swagger/ReDoc)

---

## Quick Start

### 1. Clone and Setup Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your configuration
```

### 2. Database Setup

```bash
# Create PostgreSQL database
createdb spa_center_db

# Run migrations
python manage.py migrate

# Setup employee groups
python manage.py setup_groups

# Create admin user
python manage.py create_admin --email=admin@example.com --password=your-secure-password
```

### 3. Seed Demo Data

```bash
# Seed all spa center data (locations, services, branches, therapists, products)
python manage.py seed_all

# Or seed individually:
python manage.py seed_locations      # Countries & cities
python manage.py seed_specialties    # Therapist specialties
python manage.py seed_services       # Spa services
python manage.py seed_branches       # Spa centers & managers
python manage.py seed_therapists     # Therapist profiles
python manage.py seed_products       # Product catalog

# Seed promotions (vouchers & gift cards)
python manage.py seed_promotions

# Clear and reseed
python manage.py seed_all --clear
python manage.py seed_promotions --clear
```

### 4. Run Development Server

```bash
python manage.py runserver
```

### 5. Access API Documentation

- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/

---

## API Endpoints

### Authentication (`/api/v1/auth/`)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/register/` | Register with email/phone | No |
| POST | `/register/phone/` | Register with phone only | No |
| POST | `/login/` | Login with email/phone | No |
| POST | `/logout/` | Logout (blacklist token) | Yes |
| POST | `/token/refresh/` | Refresh access token | No |
| POST | `/social/google/` | Google OAuth login | No |
| POST | `/social/facebook/` | Facebook OAuth login | No |
| POST | `/verify/send/` | Send verification code | Yes |
| POST | `/verify/confirm/` | Verify email/phone | Yes |
| POST | `/password/reset/` | Request password reset | No |
| POST | `/password/reset/confirm/` | Confirm password reset | No |
| POST | `/password/change/` | Change password | Yes |
| GET | `/user/` | Get current user | Yes |
| PUT | `/user/` | Update current user | Yes |

---

### Account Management (`/api/v1/accounts/`)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/employees/` | List employees | Admin |
| POST | `/employees/` | Create employee | Admin |
| GET | `/employees/{id}/` | Get employee details | Admin |
| PUT/PATCH | `/employees/{id}/` | Update employee | Admin |
| DELETE | `/employees/{id}/` | Deactivate employee | Admin |
| POST | `/employees/{id}/activate/` | Reactivate employee | Admin |
| POST | `/employees/{id}/reset_password/` | Reset employee password | Admin |
| GET | `/customers/` | List customers | Admin |
| GET | `/customers/{id}/` | Get customer details | Admin |
| GET | `/users/` | List all users | Admin |
| GET | `/statistics/` | User statistics | Admin |

---

### Profiles (`/api/v1/profiles/`)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/customer/me/` | Get own customer profile | Customer |
| PUT | `/customer/me/` | Update own customer profile | Customer |
| GET | `/employee/me/` | Get own employee profile | Employee |
| PUT | `/employee/me/` | Update own employee profile | Employee |
| GET | `/employee/me/schedules/` | Get own schedules | Employee |
| POST | `/employee/me/schedules/` | Add schedule | Employee |
| GET | `/admin/employees/` | List employee profiles | Admin |
| GET | `/admin/employees/{id}/` | Get employee profile | Admin |
| PUT | `/admin/employees/{id}/` | Update employee profile | Admin |
| POST | `/admin/employees/{id}/assign_manager/` | Assign manager | Admin |
| POST | `/admin/employees/{id}/change_role/` | Change role | Admin |
| GET | `/admin/employees/{id}/team/` | Get team members | Admin |
| GET | `/therapists/` | List available therapists | Public |
| GET | `/therapists/{id}/` | Therapist details | Public |

---

### Spa Center (`/api/v1/spa/`)

#### Countries & Cities

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/countries/` | List all countries | Public |
| GET | `/countries/{id}/` | Get country details | Public |
| GET | `/countries/{id}/cities/` | Get cities in country | Public |
| GET | `/cities/` | List all cities | Public |
| GET | `/cities/?country={code}` | Filter cities by country | Public |
| GET | `/cities/{id}/` | Get city details | Public |

#### Specialties

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/specialties/` | List all specialties | Public |
| GET | `/specialties/{id}/` | Get specialty details | Public |

#### Services

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/services/` | List all services | Public |
| GET | `/services/?country={code}` | Filter by country | Public |
| GET | `/services/?city={uuid}` | Filter by city | Public |
| GET | `/services/?category={name}` | Filter by category | Public |
| GET | `/services/?is_home_service=true` | Home services only | Public |
| GET | `/services/?min_price=50&max_price=200` | Filter by price | Public |
| GET | `/services/{id}/` | Get service details | Public |

#### Spa Branches

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/branches/` | List all spa centers | Public |
| GET | `/branches/?country={code}` | Filter by country | Public |
| GET | `/branches/?city={uuid}` | Filter by city | Public |
| GET | `/branches/?is_active=true` | Active branches only | Public |
| GET | `/branches/{id}/` | Get branch details | Public |
| GET | `/branches/{id}/services/` | Get branch services | Public |
| GET | `/branches/{id}/therapists/` | Get branch therapists | Public |

#### Therapists

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/therapists/` | List all therapists | Public |
| GET | `/therapists/?country={code}` | Filter by country | Public |
| GET | `/therapists/?city={uuid}` | Filter by city | Public |
| GET | `/therapists/?specialty={uuid}` | Filter by specialty | Public |
| GET | `/therapists/?gender={M/F}` | Filter by gender | Public |
| GET | `/therapists/?is_available=true` | Available only | Public |
| GET | `/therapists/{id}/` | Get therapist details | Public |

#### Product Categories

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/product-categories/` | List active categories | Public |
| GET | `/product-categories/{id}/` | Get category details | Public |

#### Products (SpaProduct)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/products/` | List all products | Public |
| GET | `/products/?country={code}` | Filter by country | Public |
| GET | `/products/?city_name={name}` | Filter by city name | Public |
| GET | `/products/?category={name}` | Filter by category | Public |
| GET | `/products/?in_stock=true` | In-stock only | Public |
| GET | `/products/?active=true` | Active products only | Public |
| GET | `/products/{id}/` | Get product details | Public |

---

### Promotions (`/api/v1/promotions/`)

#### Vouchers

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/vouchers/` | List active vouchers | Public |
| GET | `/vouchers/{id}/` | Get voucher details | Public |
| POST | `/vouchers/validate/` | Validate voucher code | Public |
| POST | `/vouchers/apply/` | Apply voucher to order | Yes |
| GET | `/voucher-usage/` | Get user's voucher history | Yes |

**Validate Voucher Request:**
```json
{
    "code": "WELCOME10",
    "amount": 150.00
}
```

**Apply Voucher Request:**
```json
{
    "code": "WELCOME10",
    "amount": 150.00,
    "order_reference": "ORD-123",
    "order_type": "service_booking"
}
```

#### Gift Card Templates

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/gift-card-templates/` | List available templates | Public |
| GET | `/gift-card-templates/{id}/` | Get template details | Public |

#### Gift Cards

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/gift-cards/` | List user's gift cards | Yes |
| POST | `/gift-cards/` | Purchase gift card | Yes |
| GET | `/gift-cards/{id}/` | Get gift card details | Yes |
| POST | `/gift-cards/validate/` | Validate gift card | Public |
| POST | `/gift-cards/check_balance/` | Check balance | Public |
| POST | `/gift-cards/redeem/` | Redeem amount | Yes |
| POST | `/gift-cards/transfer/` | Transfer to user | Yes |
| GET | `/gift-cards/{id}/transactions/` | Transaction history | Yes |
| GET | `/gift-card-transactions/` | All user transactions | Yes |

**Purchase Gift Card Request:**
```json
{
    "template_id": "uuid-here",
    "recipient_email": "friend@example.com",
    "recipient_name": "John Doe",
    "recipient_message": "Happy Birthday!",
    "payment_reference": "PAY-123"
}
```

**Redeem Gift Card Request:**
```json
{
    "code": "ABCD-EFGH-IJKL-MNOP",
    "pin": "1234",
    "amount": 50.00,
    "order_reference": "ORD-456",
    "order_type": "product_order"
}
```

**Transfer Gift Card Request:**
```json
{
    "code": "ABCD-EFGH-IJKL-MNOP",
    "new_owner_email": "newowner@example.com"
}
```

#### Combined Discounts

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/apply-discounts/` | Apply voucher + gift card | Yes |

**Request:**
```json
{
    "amount": 200.00,
    "voucher_code": "SUMMER25",
    "gift_card_code": "ABCD-EFGH-IJKL-MNOP",
    "gift_card_pin": "1234",
    "gift_card_amount": 50.00
}
```

**Response:**
```json
{
    "original_amount": "200.00",
    "voucher_discount": "50.00",
    "gift_card_amount": "50.00",
    "final_amount": "100.00",
    "voucher": {
        "code": "SUMMER25",
        "discount_type": "percentage",
        "discount_value": "25.00"
    },
    "gift_card": {
        "code": "ABCD-EFGH-IJKL-MNOP",
        "balance_before": "100.00",
        "balance_after": "50.00"
    }
}
```

---

## Data Models

### Accounts App
- **User**: Custom user model with email/phone authentication
- **VerificationCode**: Email/phone verification codes

### Profiles App
- **CustomerProfile**: Customer personal information
- **EmployeeProfile**: Employee details, roles, schedules

### Spacenter App
- **Country**: Countries with code, currency, phone code
- **City**: Cities linked to countries
- **Specialty**: Therapist specialties
- **Service**: Spa services with pricing
- **ServiceImage**: Service gallery images
- **SpaCenter**: Spa branch locations
- **SpaCenterOperatingHours**: Branch hours
- **TherapistProfile**: Therapist details
- **ProductCategory**: Product categories
- **BaseProduct**: Master product catalog
- **SpaProduct**: Location-specific stock/pricing

### Promotions App
- **Voucher**: Discount codes
- **VoucherUsage**: Usage tracking
- **GiftCardTemplate**: Gift card denominations
- **GiftCard**: Individual gift cards
- **GiftCardTransaction**: Transaction history

---

## Demo Voucher Codes

| Code | Discount | Description |
|------|----------|-------------|
| `WELCOME10` | 10% (max 50) | First-time users only |
| `SUMMER25` | 25% (max 100) | Services only |
| `PRODUCT15` | 15% | Products only |
| `FLAT50` | 50 QAR fixed | Min purchase 200 |
| `VIP100` | 100 QAR fixed | Services, min 300 |
| `AROMATHERAPY20` | 20% | Aromatherapy & Oils |

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | Required |
| `DEBUG` | Debug mode | `False` |
| `DB_NAME` | Database name | `spa_center_db` |
| `DB_USER` | Database user | `postgres` |
| `DB_PASSWORD` | Database password | Required |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | Optional |
| `GOOGLE_CLIENT_SECRET` | Google OAuth secret | Optional |
| `FACEBOOK_APP_ID` | Facebook App ID | Optional |
| `FACEBOOK_APP_SECRET` | Facebook App secret | Optional |
| `TWILIO_ACCOUNT_SID` | Twilio account SID | Optional |
| `TWILIO_AUTH_TOKEN` | Twilio auth token | Optional |
| `TWILIO_PHONE_NUMBER` | Twilio phone number | Optional |
| `CORS_ALLOW_ALL_ORIGINS` | Allow all CORS | `True` |

### JWT Configuration

```python
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}
```

---

## Project Structure

```
auth_service/
├── config/                     # Project configuration
│   ├── settings.py            # Django settings
│   ├── urls.py                # Main URL routing
│   ├── celery.py              # Celery configuration
│   └── wsgi.py                # WSGI application
├── accounts/                   # Authentication app
│   ├── models.py              # User, VerificationCode
│   ├── serializers.py         # Auth serializers
│   ├── views/                 # Auth views
│   ├── urls/                  # Auth URLs
│   ├── permissions.py         # Custom permissions
│   └── tasks.py               # Celery tasks
├── profiles/                   # User profiles app
│   ├── models.py              # Customer/Employee profiles
│   ├── serializers.py         # Profile serializers
│   ├── views.py               # Profile views
│   └── urls.py                # Profile URLs
├── spacenter/                  # Spa center management app
│   ├── models.py              # All spa models
│   ├── serializers.py         # Spa serializers
│   ├── views.py               # Spa views
│   ├── urls.py                # Spa URLs
│   ├── admin.py               # Admin configuration
│   ├── translation.py         # Translation config
│   └── management/commands/   # Seed commands
│       ├── seed_all.py
│       ├── seed_locations.py
│       ├── seed_services.py
│       ├── seed_branches.py
│       ├── seed_therapists.py
│       ├── seed_products.py
│       └── seed_specialties.py
├── promotions/                 # Vouchers & Gift Cards app
│   ├── models.py              # Voucher, GiftCard models
│   ├── serializers.py         # Promotion serializers
│   ├── views.py               # Promotion views
│   ├── urls.py                # Promotion URLs
│   ├── admin.py               # Admin configuration
│   └── management/commands/
│       └── seed_promotions.py
├── templates/                  # Email templates
├── locale/                     # Translations (en, ar)
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Docker configuration
├── docker-compose.yml         # Docker Compose
├── .env.example               # Environment template
└── README.md                  # This file
```

---

## Docker Deployment

```bash
# Build and run
docker-compose up -d --build

# Run migrations
docker-compose exec web python manage.py migrate

# Seed data
docker-compose exec web python manage.py seed_all
docker-compose exec web python manage.py seed_promotions

# Create admin
docker-compose exec web python manage.py create_admin --email=admin@example.com --password=admin123
```

---

## License

MIT License
