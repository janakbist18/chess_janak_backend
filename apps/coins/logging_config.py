"""
Stripe payment logging configuration.
Provides structured logging for security monitoring and debugging.
"""
import logging
import logging.config
from django.conf import settings

# Structured logging configuration
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(timestamp)s %(level)s %(name)s %(message)s'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
        'sensitive_fields': {
            '()': 'apps.coins.logging_filters.SensitiveDataFilter',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'filters': ['sensitive_fields'],
        },
        'stripe_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/stripe_payments.log',
            'maxBytes': 1024 * 1024 * 100,  # 100MB
            'backupCount': 30,
            'formatter': 'json',
            'filters': ['sensitive_fields'],
        },
        'payment_security_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/payment_security.log',
            'maxBytes': 1024 * 1024 * 50,  # 50MB
            'backupCount': 60,
            'formatter': 'json',
        },
        'webhook_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/stripe_webhooks.log',
            'maxBytes': 1024 * 1024 * 100,
            'backupCount': 30,
            'formatter': 'json',
        },
    },
    'loggers': {
        'apps.coins.services.stripe_service': {
            'handlers': ['console', 'stripe_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.coins.views_stripe': {
            'handlers': ['console', 'stripe_file', 'payment_security_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'stripe_webhooks': {
            'handlers': ['console', 'webhook_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}


class SensitiveDataFilter(logging.Filter):
    """Filter to remove sensitive payment data from logs."""
    SENSITIVE_FIELDS = {
        'card', 'cvv', 'secret', 'token', 'password', 'pin',
        'client_secret', 'api_key'
    }

    def filter(self, record):
        """Remove sensitive fields from log records."""
        if isinstance(record.msg, str):
            for field in self.SENSITIVE_FIELDS:
                if field.lower() in record.msg.lower():
                    # Mask sensitive data in message
                    record.msg = self._mask_sensitive_data(record.msg)
        return True

    @staticmethod
    def _mask_sensitive_data(text):
        """Replace sensitive values with asterisks."""
        import re
        # Mask long strings (likely tokens/secrets)
        text = re.sub(r'(sk_|pk_)[a-zA-Z0-9_]{20,}', 'sk_****', text)
        text = re.sub(r'(pi_)[a-zA-Z0-9_]{20,}', 'pi_****', text)
        return text
