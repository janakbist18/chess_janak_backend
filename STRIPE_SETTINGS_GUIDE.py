"""
Stripe Payment Integration - Django Settings Configuration Guide

Add these settings to your Django settings.py file.
"""

# ============================================================================
# STRIPE PAYMENT CONFIGURATION
# ============================================================================

import os
from pathlib import Path

# Get from environment variables for security (NEVER hardcode in settings!)
STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY', 'pk_test_...')
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', 'sk_test_...')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', 'whsec_...')
STRIPE_API_VERSION = '2023-10-16'

# ============================================================================
# REST FRAMEWORK CONFIGURATION
# ============================================================================

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
}

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(level)s %(name)s %(message)s'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'stripe_payments': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'stripe_payments.log'),
            'maxBytes': 1024 * 1024 * 100,  # 100MB
            'backupCount': 30,
            'formatter': 'json',
        },
        'payment_security': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'payment_security.log'),
            'maxBytes': 1024 * 1024 * 50,  # 50MB
            'backupCount': 60,
            'formatter': 'json',
        },
    },
    'loggers': {
        'apps.coins.services.stripe_service': {
            'handlers': ['console', 'stripe_payments'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.coins.views_stripe': {
            'handlers': ['console', 'stripe_payments', 'payment_security'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# ============================================================================
# INSTALLED APPS - Add these
# ============================================================================

# In your INSTALLED_APPS list, add:
# 'apps.coins',
# 'rest_framework',
# 'django_filters',

# ============================================================================
# MIDDLEWARE - Add if using rate limiting
# ============================================================================

# Optional: Add rate limiting middleware
# MIDDLEWARE = [
#     # ... other middleware ...
#     'django_ratelimit.middleware.RatelimitMiddleware',
# ]

# ============================================================================
# RATE LIMITING CONFIGURATION (Optional)
# ============================================================================

# Prevent brute force attacks on payment endpoints
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'

# ============================================================================
# CORS CONFIGURATION (if needed for frontend)
# ============================================================================

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "https://yourdomain.com",
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'stripe-signature',  # Important for webhooks
]

# ============================================================================
# SECURITY SETTINGS (Production)
# ============================================================================

if not DEBUG:
    # HTTPS/TLS Enforcement
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    # Content Security Policy
    SECURE_CONTENT_SECURITY_POLICY = {
        'default-src': ("'self'",),
        'script-src': ("'self'", 'js.stripe.com'),
        'style-src': ("'self'", "'unsafe-inline'"),
        'connect-src': ("'self'", 'api.stripe.com'),
    }

# ============================================================================
# URL CONFIGURATION
# ============================================================================

# In your main urls.py, add this to urlpatterns:
# from apps.coins import urls_stripe
# urlpatterns = [
#     # ... other patterns ...
#     path('api/coins/', include(urls_stripe.urlpatterns)),
# ]

# Final URL structure will be:
# POST   /api/coins/stripe/create-payment-intent/     - Create payment intent
# GET    /api/coins/stripe/payment-status/            - Check payment status
# GET    /api/coins/stripe/packages/                  - List packages
# GET    /api/coins/stripe/history/                   - Payment history
# POST   /api/coins/stripe/webhook/                   - Webhook endpoint
