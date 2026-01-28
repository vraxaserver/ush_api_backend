"""
Django settings for Auth Microservice.

Authentication and Employee Profile Management Service
Supports JWT, Social Auth (Google/Facebook), and role-based access.
"""

import os
import warnings
from datetime import timedelta
from pathlib import Path

from decouple import Csv, config

# Suppress django-allauth deprecation warnings from dj-rest-auth
warnings.filterwarnings("ignore", message="app_settings.*is deprecated")

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config("SECRET_KEY", default="your-secret-key-change-in-production")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())


# ============================================================================
# CORS Configuration
# ============================================================================
# For development/mobile apps - Allow all origins
CORS_ALLOW_ALL_ORIGINS = config("CORS_ALLOW_ALL_ORIGINS", default=True, cast=bool)

# For production - Specify allowed origins (used when CORS_ALLOW_ALL_ORIGINS is False)
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000,http://127.0.0.1:3000",
    cast=Csv(),
)

# Allow credentials (cookies, authorization headers)
CORS_ALLOW_CREDENTIALS = True

# Allow all headers from mobile apps
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "accept-language",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "x-api-key",
    "x-device-id",
    "x-device-type",
    "x-app-version",
    "x-platform",
    "cache-control",
    "pragma",
]

# Allow all HTTP methods
CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

# Expose these headers to the client
CORS_EXPOSE_HEADERS = [
    "content-type",
    "x-total-count",
    "x-page-count",
    "x-current-page",
    "x-per-page",
]

# Cache preflight requests for 1 hour (3600 seconds)
CORS_PREFLIGHT_MAX_AGE = 3600

# Allow requests from null origin (mobile apps, file://, etc.)
CORS_ALLOW_PRIVATE_NETWORK = True


# ----------------------------
# Reverse proxy / HTTPS headers
# ----------------------------
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ----------------------------
# CSRF trusted origins (required for Django 4+)
# ----------------------------
CSRF_TRUSTED_ORIGINS = [
    "http://api.spaush.com",
    "https://api.spaush.com",
    "http://ushapi.charlicoder.com",
    "https://ushapi.charlicoder.com",
]

# If admin uses cookies cross-site (rare), keep defaults; otherwise:
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SAMESITE = "Lax"

CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

# Application definition
DJANGO_APPS = [
    "modeltranslation",  # Must be before admin for translation support
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework.authtoken",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "drf_spectacular",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.facebook",
    "dj_rest_auth",
    "dj_rest_auth.registration",
    "phonenumber_field",
    "django_celery_beat",
    "django_filters",
    "admin_searchable_dropdown"
]

LOCAL_APPS = [
    "accounts",
    "profiles",
    "spacenter",
    "promotions",
    "bookings",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",  # For multi-language support
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="auth_service_db"),
        "USER": config("DB_USER", default="postgres"),
        "PASSWORD": config("DB_PASSWORD", default="postgres"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Custom User Model
AUTH_USER_MODEL = "accounts.User"

# Internationalization
LANGUAGE_CODE = "en"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Multi-language support (English, Arabic)
LANGUAGES = [
    ("en", "English"),
    ("ar", "Arabic"),
]

# Default language for modeltranslation
MODELTRANSLATION_DEFAULT_LANGUAGE = "en"
MODELTRANSLATION_LANGUAGES = ("en", "ar")

# Fallback to default language if translation not available
MODELTRANSLATION_FALLBACK_LANGUAGES = ("en",)

# Locale paths for translation files
LOCALE_PATHS = [
    BASE_DIR / "locale",
]

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Only use STATICFILES_DIRS for local development if you really need it
# (recommended: remove it in production container images)
if DEBUG:
    STATICFILES_DIRS = [BASE_DIR / "static"]
else:
    STATICFILES_DIRS = []

# Media files (user uploads)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "mediafiles"



# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Site ID for django-allauth
SITE_ID = 1

# ============================================================================
# REST Framework Configuration
# ============================================================================
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        # SessionAuthentication removed - causes CSRF issues for API clients
        # If you need session auth for browsable API, add it back and handle CSRF
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
    },
}

# ============================================================================
# JWT Configuration
# ============================================================================
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=7),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
}

# ============================================================================
# Django-Allauth Configuration
# ============================================================================
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# Custom adapters to disable allauth email sending
ACCOUNT_ADAPTER = "accounts.adapters.CustomAccountAdapter"
SOCIALACCOUNT_ADAPTER = "accounts.adapters.CustomSocialAccountAdapter"

# New django-allauth settings format (v0.60+)
ACCOUNT_LOGIN_METHODS = {"email"}  # Login via email only
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]  # Required signup fields
ACCOUNT_UNIQUE_EMAIL = True

# Completely disable allauth's email verification - we use our own verification code system
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 1
ACCOUNT_CONFIRM_EMAIL_ON_GET = False
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = False
ACCOUNT_USER_MODEL_USERNAME_FIELD = None

# Disable allauth email sending entirely
ACCOUNT_EMAIL_NOTIFICATIONS = False

# Social Account Settings
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": config("GOOGLE_CLIENT_ID", default=""),
            "secret": config("GOOGLE_CLIENT_SECRET", default=""),
            "key": "",
        },
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
    },
    "facebook": {
        "APP": {
            "client_id": config("FACEBOOK_APP_ID", default=""),
            "secret": config("FACEBOOK_APP_SECRET", default=""),
            "key": "",
        },
        "METHOD": "oauth2",
        "SCOPE": ["email", "public_profile"],
        "AUTH_PARAMS": {"auth_type": "reauthenticate"},
        "FIELDS": [
            "id",
            "first_name",
            "last_name",
            "email",
        ],
        "VERSION": "v13.0",
    },
}

SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True

# ============================================================================
# dj-rest-auth Configuration
# ============================================================================
REST_AUTH = {
    "USE_JWT": True,
    "JWT_AUTH_HTTPONLY": False,
    "JWT_AUTH_COOKIE": "access_token",
    "JWT_AUTH_REFRESH_COOKIE": "refresh_token",
    "SESSION_LOGIN": False,  # Disable session login - use JWT only
    "REGISTER_SERIALIZER": "accounts.serializers.CustomRegisterSerializer",
    "USER_DETAILS_SERIALIZER": "accounts.serializers.UserSerializer",
    "LOGIN_SERIALIZER": "accounts.serializers.CustomLoginSerializer",
}

# ============================================================================
# Email Configuration
# ============================================================================
EMAIL_BACKEND = config(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="contact@spaush.com")

# ============================================================================
# SMS Configuration (AWS SNS)
# ============================================================================
AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID", default="")
AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY", default="")
AWS_REGION_NAME = config("AWS_REGION_NAME", default="me-center-1")
# SMS Sender ID (optional, up to 11 alphanumeric characters)
AWS_SNS_SENDER_ID = config("AWS_SNS_SENDER_ID", default="AuthService")
# SMS Type: Promotional or Transactional
AWS_SNS_SMS_TYPE = config("AWS_SNS_SMS_TYPE", default="Transactional")

# ============================================================================
# Phone Number Field Configuration
# ============================================================================
PHONENUMBER_DEFAULT_REGION = "US"
PHONENUMBER_DB_FORMAT = "E164"

# ============================================================================
# CORS Configuration
# ============================================================================
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000,http://127.0.0.1:3000",
    cast=Csv(),
)
CORS_ALLOW_CREDENTIALS = True

# ============================================================================
# API Documentation (drf-spectacular)
# ============================================================================
SPECTACULAR_SETTINGS = {
    "TITLE": "Auth Microservice API",
    "DESCRIPTION": "Authentication and Employee Profile Management API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": r"/api/v1",
}

# ============================================================================
# Celery Configuration (for async email/SMS)
# ============================================================================
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = config(
    "CELERY_RESULT_BACKEND", default="redis://localhost:6379/0"
)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# ============================================================================
# Verification Settings
# ============================================================================
VERIFICATION_CODE_LENGTH = 6
VERIFICATION_CODE_EXPIRY_MINUTES = 10
MAX_VERIFICATION_ATTEMPTS = 5

# ============================================================================
# Logging Configuration
# ============================================================================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": config("DJANGO_LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
        "accounts": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
