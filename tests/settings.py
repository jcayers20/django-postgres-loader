"""Minimal Django settings for the test suite."""

import os

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("PGDATABASE", "postgres"),
        "USER": os.environ.get("PGUSER", ""),
        "PASSWORD": os.environ.get("PGPASSWORD", ""),
        "HOST": os.environ.get("PGHOST", "localhost"),
        "PORT": os.environ.get("PGPORT", "5432"),
    },
}

INSTALLED_APPS = [
    "tests",
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
