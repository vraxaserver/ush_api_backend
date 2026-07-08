# Spa Center Auth & Management Microservice

A comprehensive Django REST Framework microservice for spa center management with authentication, employee management, spa services, products, therapists, and promotions (gift cards).

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
- **Gift Cards**: Prepaid balance cards with transfer support

### 💳 Payments
- **Stripe Integration**: Full payment processing via Stripe
- **PaymentSheet Support**: React Native mobile payment UI
- **Webhook Handling**: Automatic payment status updates

### 🌐 Multi-language Support
- English (EN) and Arabic (AR) translations
- Translatable fields for all content

---

## Tech Stack

- **Backend**: Django 4.2+, Django REST Framework
- **Authentication**: djangorestframework-simplejwt, dj-rest-auth, django-allauth
- **Database**: PostgreSQL
- **Async Tasks**: AWS SQS / SNS (Direct async dispatch)
- **Payments**: Stripe
- **SMS**: Twilio
- **Translations**: django-modeltranslation
- **API Docs**: drf-spectacular (Swagger/ReDoc)

---

## Running Server Locally

Follow these steps to set up the development environment on your local machine.

### Prerequisites
- Python 3.12+
- PostgreSQL database
- Redis cache server (running locally or via Docker)

### 1. Environment Setup

```bash
# Clone the repository and navigate to the project directory
cd ush_api_backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template file
cp .env.example .env
# Edit .env and supply your local configuration values (DB credentials, Redis connection, etc.)
```

### 2. Database and Cache Configuration

Ensure PostgreSQL and Redis are running. For a quick local setup of PostgreSQL and Redis, you can use Docker:
```bash
# Start Redis cache server using docker-compose helper (or start your local instance)
docker compose up -d redis
```

Configure your `.env` variables accordingly:
```ini
DB_NAME=spa_center_db
DB_USER=postgres
DB_PASSWORD=your_secure_password
DB_HOST=127.0.0.1
DB_PORT=5432

CACHE_REDIS_URL=redis://127.0.0.1:6379/1
```

### 3. Migrations & Initial Setup

```bash
# Run migrations to initialize the database schema
python manage.py migrate

# Setup employee permission groups
python manage.py setup_groups

# Create a superuser / admin account
python manage.py create_admin --email=admin@example.com --password=your-secure-password
```

### 4. Seeding Demo Data

```bash
# Seed all spa center data (countries, cities, specialties, services, branches, therapists, products)
python manage.py seed_all --clear

# Seed promotions/gift cards template data
python manage.py seed_promotions --clear
```

### 5. Running the Development Server

```bash
python manage.py runserver 0.0.0.0:8000
```

Once running, you can access the interactive API docs at:
- **Swagger UI**: [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/)
- **ReDoc**: [http://localhost:8000/api/redoc/](http://localhost:8000/api/redoc/)

---

## Production Deployment

This project is configured for containerized deployment in production using Docker, Gunicorn, and Nginx.

### Docker Multi-Stage Build
The included [Dockerfile](file:///d:/vraxa_projects/ush_spa_projects/ush_api_backend/Dockerfile) uses a multi-stage process:
1. **Builder Stage**: Installs compiler headers, dependencies, and builds wheels.
2. **Production Stage**: Copies the built wheels, installs them, adds a non-root system user (`appuser`), and configures directories for static and media assets.

### Production Environment Settings
Set the following settings in your production `.env` file:
```ini
ENV=prod
DEBUG=False
ALLOWED_HOSTS=api.spaush.com,yourdomain.com
CORS_ALLOW_ALL_ORIGINS=False
CORS_ALLOWED_ORIGINS=https://spaush.com,https://www.spaush.com
```

### Static & Media File Storage (AWS S3)
When `ENV=prod` and `DEBUG=False`, the application automatically uploads and serves static and media assets via AWS S3:
```ini
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_REGION_NAME=me-central-1
```

### Nginx Reverse Proxy & Gunicorn Configuration
Gunicorn runs the application inside the container, bound to port 8000. Use Nginx on the host machine to handle SSL/TLS termination and proxy requests to Gunicorn.
An example Nginx configuration file is provided in [nginx.conf](file:///d:/vraxa_projects/ush_spa_projects/ush_api_backend/nginx.conf):
- Proxies `/` requests to `http://127.0.0.1:8000`.
- Optimizes static/media serving when hosted on local folders.
- Implements security headers like `X-Frame-Options`, `X-Content-Type-Options`, and `Referrer-Policy`.

### Deployment via Docker Compose
To deploy the application stack (web service + Redis container):
```bash
# Build and start services in detached mode
docker compose up -d --build

# Run database migrations inside the web container
docker compose exec web python manage.py migrate --noinput

# Seed initial settings
docker compose exec web python manage.py setup_groups
```

---

## API Endpoints

### 🔑 Authentication (`/api/v1/auth/`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/health/` | Health check for auth microservice | No |
| POST | `/register/` | Register with email & password | No |
| POST | `/register/phone/` | Register with phone number only | No |
| POST | `/login/` | User login (returns JWT access/refresh) | No |
| POST | `/logout/` | Blacklist refresh token to logout | Yes |
| POST | `/token/refresh/` | Obtain new access token | No |
| POST | `/social/google/` | Google OAuth2 social authentication | No |
| POST | `/social/facebook/` | Facebook OAuth2 social authentication | No |
| POST | `/verify/send/` | Trigger phone/email verification code | Yes |
| POST | `/verify/confirm/` | Confirm verification code | Yes |
| POST | `/password/reset/` | Request password reset verification code | No |
| POST | `/password/reset/confirm/` | Confirm password reset | No |
| POST | `/password/change/` | Change password for logged in user | Yes |
| GET | `/user/` | Retrieve current user profile details | Yes |
| PUT/PATCH | `/user/` | Update current user profile details | Yes |
| POST | `/user/delete-request/` | Request data deletion (compliance) | Yes |

---

### 👥 Account Management (`/api/v1/accounts/`)

*Endpoints in this section are restricted to administrators.*

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/customers/` | List customer accounts (supports filters) | Yes (Admin) |
| GET | `/customers/{id}/` | Get customer user details | Yes (Admin) |
| PUT/PATCH | `/customers/{id}/` | Update customer user details | Yes (Admin) |
| GET | `/users/` | List all system users | Yes (Admin) |
| GET | `/statistics/` | Retrieve user registration statistics | Yes (Admin) |

---

### 👤 Profiles (`/api/v1/profiles/`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/customer/me/` | Get current authenticated customer profile | Yes (Customer) |
| PUT/PATCH | `/customer/me/` | Update customer profile parameters | Yes (Customer) |
| GET | `/slides/` | Get active slideshow assets for home page | No |

---

### 🏢 Spa Center Management (`/api/v1/spa/`)

*All catalog endpoints are public.*

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/countries/` | List all operational countries | No |
| GET | `/countries/{id}/` | Get country details | No |
| GET | `/cities/` | List all cities (optional `country` filter) | No |
| GET | `/cities/{id}/` | Get city details | No |
| GET | `/specialties/` | List therapist specialties | No |
| GET | `/specialties/{id}/` | Get specialty details | No |
| GET | `/add-on-services/` | List add-on services | No |
| GET | `/add-on-services/{id}/` | Get add-on service details | No |
| GET | `/services/` | List all services (supports country/city filters) | No |
| GET | `/services/{id}/` | Get service details | No |
| GET | `/branches/` | List all spa branch locations | No |
| GET | `/branches/{id}/` | Get branch operational details | No |
| GET | `/product-categories/` | List catalog product categories | No |
| GET | `/product-categories/{id}/` | Get category details | No |
| GET | `/products/` | List products with localized stock/pricing | No |
| GET | `/products/{id}/` | Get product location stock details | No |
| GET | `/home-services/` | List services offered at home | No |
| GET | `/home-services/{id}/` | Get home service details | No |

---

### 📅 Bookings & Orders (`/api/v1/bookings/`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/upcoming-bookings/` | Get upcoming bookings for customer | Yes |
| GET | `/past-bookings/` | Get past bookings for customer | Yes |
| GET | `/services/{service_id}/arrangements/` | Get arrangements/rooms supporting service | No |
| GET | `/services/{service_id}/availability/` | Get time slot availability for service | No |
| GET/POST | `/` | List or create regular spa bookings | Yes |
| GET/PUT/PATCH/DELETE | `/{id}/` | View, update, or cancel booking | Yes |
| POST | `/{id}/confirm/` | Confirm booking (Staff only) | Yes (Staff) |
| POST | `/{id}/complete/` | Complete booking (Staff only) | Yes (Staff) |
| POST | `/update-payment-status/` | Update status after online payment | Yes |
| GET/POST | `/home-bookings/` | List or request home service bookings | Yes |
| GET/PUT/PATCH/DELETE | `/home-bookings/{id}/` | View, update, or cancel home booking | Yes |
| POST | `/home-bookings/update-payment-status/` | Update payment status for home booking | Yes |
| GET/POST | `/orders/` | List or create product delivery orders | Yes |
| GET/PUT/PATCH/DELETE | `/orders/{id}/` | View or modify product order | Yes |

---

### 🎟️ Promotions & Loyalty Program (`/api/v1/promotions/`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/loyalty-trackers/` | View current user's loyalty program points | Yes |
| GET | `/loyalty-rewards/` | List redeemable loyalty rewards | Yes |
| GET | `/loyalty/status/` | Detailed loyalty tiers and tier points progress | Yes |
| GET | `/gift-cards/` | List all gift cards in the system | Yes (Admin) |
| GET | `/my-gift-cards/` | Get gift cards owned by authenticated user | Yes |
| GET | `/my-sent-gift-cards/` | Get gift cards sent by user to others | Yes |
| POST | `/gift-cards/{public_token}/fulfill/` | Manually fulfill a gift card | Yes (Admin) |

---

### 💳 Payments (`/api/v1/payments/`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/payment-sheet/` | Generate Stripe checkout PaymentSheet parameters | Yes |
| POST | `/webhook/` | Stripe webhook listener (updates payment statuses) | No |

---

### ✉️ Notifications & Contact (`/api/v1/notifications/`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/contact/` | Submit general query contact form | No |
| GET | `/contact/list/` | List submitted queries (Admin/Staff only) | Yes (Staff) |
| GET | `/contact/{id}/` | Retrieve contact query detail (Admin/Staff only)| Yes (Staff) |

---

### 🎁 Public Gift Card Flow (`/gift-cards/`)

*Served outside the standard API namespace for web page rendering & guest checkouts.*

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/public/{public_token}/` | Render HTML template displaying gift card | No |
| GET | `/redeem/{public_token}/` | Render redemption page for guest/customer | No |
| POST | `/api/verify-code/` | Verify gift card code & PIN | No |
| GET | `/api/availability/{public_token}/` | Get availability for redemption | No |
| POST | `/api/redeem-booking/` | Book service using gift card code | No |
| POST | `/api/check-validity/` | Retrieve card validity & balance status | No |
| POST | `/api/redeem/` | Deduct balance from gift card | No |

---

## Data Models

### Accounts App
- **User**: Custom user model supporting email/phone registration, verification codes, and client roles (Customer, Therapist, Branch Manager, Admin).
- **VerificationCode**: Validates registration/login via transient codes.

### Profiles App
- **CustomerProfile**: Extends user credentials with specific customer preference attributes.
- **Slide**: Home screen banner promotional images.

### Spacenter App
- **Country & City**: Geographical setup supporting localized branches.
- **SpaCenter**: Operational branches details (operating hours, default locations).
- **Service**: Service metadata (durations, categories, price structures).
- **ServiceArrangement**: Linkage of rooms/equipment to service execution bounds.
- **TherapistProfile**: Staff schedules and specialization mappings.
- **BaseProduct & SpaProduct**: Inventory control and pricing catalog details.

### Bookings App
- **Booking**: Spa booking records tracking state transitions (`requested`, `payment_pending`, `payment_success`, `confirmed`, `completed`, `canceled`).
- **HomeServiceBooking**: Extended model for bookings executed at client home addresses.
- **TimeSlot**: Booking scheduler allocations.
- **ProductOrder & OrderItem**: Deliverable merchandise order structures.

### Promotions App
- **GiftCardTemplate**: Fixed templates mapping denominations.
- **GiftCard**: Unique active instances (balance, secure token, code/PIN combination).
- **GiftCardTransaction**: Audit records tracking credits, debits, and transfers.
- **LoyaltyTracker & LoyaltyReward**: Points accumulation records and tier benefits.

### Payments App
- **StripeCustomer**: Binds local users with Stripe portal tokens.
- **Payment**: Local records documenting transaction responses.

---

## License

MIT License

