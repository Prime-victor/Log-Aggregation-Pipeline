from .base import *  # noqa

DEBUG = True

# Relaxed security for local dev
CORS_ALLOW_ALL_ORIGINS = True

# Show SQL queries in dev (disable in prod)
INSTALLED_APPS += ["debug_toolbar"]
MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]
INTERNAL_IPS = ["127.0.0.1"]

# Use sync email in dev
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"