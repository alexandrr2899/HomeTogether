"""Server-side settings. Credentials are supplied outside the repository."""

import os
from pathlib import Path

from .env_file import load_env_file


BASE_DIR = Path(__file__).resolve().parent.parent
load_env_file(BASE_DIR.parent / ".env")
SECRET_KEY = os.environ.get("HT_DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    raise RuntimeError("HT_DJANGO_SECRET_KEY is required")

DEBUG = os.environ.get("HT_DEBUG", "0") == "1"
ALLOWED_HOSTS = [host.strip() for host in os.environ.get("HT_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if host.strip()]
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.environ.get("HT_CSRF_TRUSTED_ORIGINS", "").split(",") if origin.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "apps.accounts",
    "apps.family",
    "apps.integrations",
    "apps.calendar",
    "apps.lists",
    "apps.home",
    "apps.planning",
    "apps.jaime",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.debug",
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

if os.environ.get("HT_TEST_SQLITE") == "1":
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "test.sqlite3"}}
else:
    DATABASES = {"default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("HT_DB_NAME", "home_together"),
        "USER": os.environ.get("HT_DB_USER", "home_together"),
        "PASSWORD": os.environ.get("HT_DB_PASSWORD", ""),
        "HOST": os.environ.get("HT_DB_HOST", "localhost"),
        "PORT": os.environ.get("HT_DB_PORT", "5432"),
    }}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}

LANGUAGE_CODE = "es"
TIME_ZONE = "America/Tegucigalpa"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT = Path(os.environ.get("HT_PRIVATE_FILES_DIR", BASE_DIR.parent / "private_uploads"))
FILE_UPLOAD_PERMISSIONS = 0o600
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o700
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
LOCAL_OAUTH_HTTP = os.environ.get("HT_LOCAL_OAUTH_HTTP", "0") == "1"
GOOGLE_REDIRECT_URI = os.environ.get(
    "HT_GOOGLE_REDIRECT_URI", "http://127.0.0.1:8005/api/v1/calendar/oauth/callback/"
)
if LOCAL_OAUTH_HTTP and not GOOGLE_REDIRECT_URI.startswith(("http://127.0.0.1:", "http://localhost:")):
    raise RuntimeError("HT_LOCAL_OAUTH_HTTP requires a loopback OAuth redirect")
SESSION_COOKIE_SECURE = not (DEBUG or LOCAL_OAUTH_HTTP)
CSRF_COOKIE_SECURE = not (DEBUG or LOCAL_OAUTH_HTTP)
SECURE_SSL_REDIRECT = os.environ.get("HT_SSL_REDIRECT", "0") == "1"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if os.environ.get("HT_TRUST_PROXY", "0") == "1" else None
SECURE_HSTS_SECONDS = 31536000 if os.environ.get("HT_HSTS", "0") == "1" else 0

# The local OAuth authorization code arrives in a GET query string. Django's
# development server must not write that request line into its access log.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"discard_access_log": {"class": "logging.NullHandler"}},
    "loggers": {
        "django.server": {"handlers": ["discard_access_log"], "propagate": False},
    },
}
