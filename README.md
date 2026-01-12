# Auth Microservice

A comprehensive Django REST Framework microservice for authentication and employee profile management with JWT, social authentication (Google/Facebook), and role-based access control.

## Features

### Authentication
- **JWT Authentication** with access and refresh tokens
- **Social Authentication** (Google OAuth2, Facebook OAuth2)
- **Email/Phone Registration** with verification codes
- **Password Reset** via email or SMS

### User Types
- **Admin**: Full system access, can create employees
- **Employee**: Staff access with role-based permissions
- **Customer**: Self-registration, limited access

### Employee Roles
- **Branch Manager**: Manages individual branches
- **Country Manager**: Oversees all branches in a country
- **Therapist**: Service provider with scheduling

### Profiles
- **Customer Profile**: Personal info, address, preferences
- **Employee Profile**: Role, department, qualifications, scheduling

## Tech Stack

- Django 4.2+
- Django REST Framework
- djangorestframework-simplejwt
- dj-rest-auth with django-allauth
- PostgreSQL
- Celery + Redis (async tasks)
- Twilio (SMS verification)

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
createdb auth_service_db

# Run migrations
python manage.py migrate

# Setup employee groups
python manage.py setup_groups

# Create admin user
python manage.py create_admin --email=admin@gmail.com --password=Mamun@123
```

### 3. Run Development Server

```bash
python manage.py runserver
```

### 4. (Optional) Run Celery Worker

```bash
celery -A config worker -l info
```

## API Endpoints

### Authentication (`/api/v1/auth/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/register/` | Register with email/phone |
| POST | `/register/phone/` | Register with phone only |
| POST | `/login/` | Login with email/phone |
| POST | `/logout/` | Logout (blacklist token) |
| POST | `/token/refresh/` | Refresh access token |
| POST | `/social/google/` | Google OAuth login |
| POST | `/social/facebook/` | Facebook OAuth login |
| POST | `/verify/send/` | Send verification code |
| POST | `/verify/confirm/` | Verify email/phone |
| POST | `/password/reset/` | Request password reset |
| POST | `/password/reset/confirm/` | Confirm password reset |
| POST | `/password/change/` | Change password |
| GET/PUT | `/user/` | Get/update user profile |

### Account Management (`/api/v1/accounts/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/employees/` | List employees (admin) |
| POST | `/employees/` | Create employee (admin) |
| GET | `/employees/{id}/` | Get employee details |
| PUT/PATCH | `/employees/{id}/` | Update employee |
| DELETE | `/employees/{id}/` | Deactivate employee |
| POST | `/employees/{id}/activate/` | Reactivate employee |
| POST | `/employees/{id}/reset_password/` | Reset employee password |
| GET | `/customers/` | List customers (admin) |
| GET | `/customers/{id}/` | Get customer details |
| GET | `/users/` | List all users (admin) |
| GET | `/statistics/` | User statistics (admin) |

### Profiles (`/api/v1/profiles/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/PUT | `/customer/me/` | Customer's own profile |
| GET/PUT | `/employee/me/` | Employee's own profile |
| GET/POST | `/employee/me/schedules/` | Employee schedules |
| GET | `/admin/employees/` | Admin: list employee profiles |
| GET/PUT | `/admin/employees/{id}/` | Admin: manage employee profile |
| POST | `/admin/employees/{id}/assign_manager/` | Assign manager |
| POST | `/admin/employees/{id}/change_role/` | Change role |
| GET | `/admin/employees/{id}/team/` | Get team members |
| GET | `/therapists/` | List available therapists (public) |
| GET | `/therapists/{id}/` | Therapist details (public) |

### API Documentation

- Swagger UI: `/api/docs/`
- ReDoc: `/api/redoc/`
- Schema: `/api/schema/`

## Usage Examples

### Register a Customer

```bash
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "customer@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "date_of_birth": "1990-01-15",
    "password1": "securepassword123",
    "password2": "securepassword123"
  }'
```

### Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "customer@example.com",
    "password": "securepassword123"
  }'
```

### Create Employee (Admin Only)

```bash
curl -X POST http://localhost:8000/api/v1/accounts/employees/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "email": "therapist@example.com",
    "first_name": "Jane",
    "last_name": "Smith",
    "password": "securepassword123",
    "role": "therapist"
  }'
```

### Verify Email

```bash
# Request verification code
curl -X POST http://localhost:8000/api/v1/auth/verify/send/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"verification_type": "email"}'

# Verify with code
curl -X POST http://localhost:8000/api/v1/auth/verify/confirm/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"code": "123456", "verification_type": "email"}'
```

## Social Authentication Setup

### Google OAuth2

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URI: `http://localhost:8000/accounts/google/login/callback/`
6. Add client ID and secret to `.env`

### Facebook OAuth2

1. Go to [Facebook Developers](https://developers.facebook.com/)
2. Create a new app
3. Add Facebook Login product
4. Add `http://localhost:8000/accounts/facebook/login/callback/` to Valid OAuth Redirect URIs
5. Add app ID and secret to `.env`

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | Required |
| `DEBUG` | Debug mode | `False` |
| `DB_NAME` | Database name | `auth_service_db` |
| `DB_USER` | Database user | `postgres` |
| `DB_PASSWORD` | Database password | Required |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | Optional |
| `GOOGLE_CLIENT_SECRET` | Google OAuth secret | Optional |
| `FACEBOOK_APP_ID` | Facebook App ID | Optional |
| `FACEBOOK_APP_SECRET` | Facebook App secret | Optional |
| `TWILIO_ACCOUNT_SID` | Twilio account SID | Optional |
| `TWILIO_AUTH_TOKEN` | Twilio auth token | Optional |
| `TWILIO_PHONE_NUMBER` | Twilio phone number | Optional |

### JWT Configuration

Access tokens expire in 30 minutes, refresh tokens in 7 days. Configure in `settings.py`:

```python
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    ...
}
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=accounts --cov=profiles

# Run specific test file
pytest accounts/tests/test_auth.py
```

## Project Structure

```
auth_service/
├── config/                 # Project configuration
│   ├── settings.py        # Django settings
│   ├── urls.py            # Main URL configuration
│   ├── celery.py          # Celery configuration
│   └── wsgi.py            # WSGI application
├── accounts/              # User authentication app
│   ├── models.py          # User, VerificationCode models
│   ├── serializers.py     # DRF serializers
│   ├── views/             # Authentication views
│   ├── urls/              # URL configurations
│   ├── permissions.py     # Custom permissions
│   ├── tasks.py           # Celery tasks
│   ├── signals.py         # Django signals
│   └── admin.py           # Admin configuration
├── profiles/              # User profiles app
│   ├── models.py          # CustomerProfile, EmployeeProfile
│   ├── serializers.py     # Profile serializers
│   ├── views.py           # Profile views
│   └── urls.py            # Profile URLs
├── templates/             # Email templates
├── requirements.txt       # Python dependencies
├── manage.py             # Django management script
└── README.md             # This file
```

## License

MIT License
