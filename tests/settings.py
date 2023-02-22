INSTALLED_APPS = (
    "bulk_tracker",
    "tests",
)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}
SECRET_KEY = "dummy"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

USE_TZ = False
