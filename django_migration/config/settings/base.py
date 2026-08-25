import re
from datetime import timedelta
from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)
environ.Env.read_env(BASE_DIR / ".env")


def jwt_lifetime(variable_name, default):
    """Parse the legacy MERN duration syntax: N minutes/hours/days."""
    value = env(variable_name, default=default).strip().lower()
    match = re.fullmatch(r"(\d+)([mhd])", value)
    if not match:
        raise ImproperlyConfigured(
            f"{variable_name} must use the form <number>m, <number>h, or <number>d."
        )
    amount, unit = match.groups()
    keyword = {"m": "minutes", "h": "hours", "d": "days"}[unit]
    return timedelta(**{keyword: int(amount)})


# Secrets must never be empty or a known placeholder: a publicly known signing
# key lets anyone forge JWTs (C1). Kept here so both dev and prod share the rule.
PLACEHOLDER_SECRETS = {
    "",
    "insecure-development-key-change-me",
    "replace-with-a-long-random-value",
}


def _read_secret(env_var: str, fallback: str) -> str:
    """Read a required secret, rejecting empty or known placeholder values."""
    value = env(env_var, default=fallback)
    if value in PLACEHOLDER_SECRETS:
        raise ImproperlyConfigured(
            f"{env_var} is unset or set to a known placeholder value. Generate a "
            'real random secret, e.g.: python -c "import secrets; '
            'print(secrets.token_urlsafe(64))" and set it in the environment.'
        )
    return value


SECRET_KEY = _read_secret("DJANGO_SECRET_KEY", "insecure-development-key-change-me")
ACCESS_TOKEN_SECRET = _read_secret("ACCESS_TOKEN_SECRET", SECRET_KEY)

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "apps.accounts",
    "apps.inventory",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=["http://localhost:5173"])

# Auth cookies. Overridden in production (AUTH_COOKIE_SECURE defaults to True there).
AUTH_COOKIE_NAME_ACCESS = env("AUTH_COOKIE_NAME_ACCESS", default="accessToken")
AUTH_COOKIE_NAME_REFRESH = env("AUTH_COOKIE_NAME_REFRESH", default="refreshToken")
AUTH_COOKIE_PATH = "/"
AUTH_COOKIE_HTTPONLY = True
AUTH_COOKIE_SECURE = env.bool("AUTH_COOKIE_SECURE", default=False)
AUTH_COOKIE_SAMESITE = env("AUTH_COOKIE_SAMESITE", default="strict")

# Keep Django's own session/CSRF cookies consistent with the JWT cookies.
SESSION_COOKIE_SAMESITE = AUTH_COOKIE_SAMESITE
CSRF_COOKIE_SAMESITE = AUTH_COOKIE_SAMESITE

# Double-submit CSRF token cookie (non-httpOnly, readable by the SPA so axios
# can echo it as the X-CSRFToken header). Enforced on cookie-authenticated
# state-changing requests (H-06).
CSRF_COOKIE_NAME = env("CSRF_COOKIE_NAME", default="csrftoken")
CSRF_COOKIE_PATH = AUTH_COOKIE_PATH

# Security headers sent on every response (see prod.py for HSTS/SSL/CSP).
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR.parent / "frontend" / "dist"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kathmandu"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATICFILES_DIRS = [
    BASE_DIR.parent / "frontend" / "dist",
]
FRONTEND_DIR = BASE_DIR.parent / "frontend"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"
APPEND_SLASH = False

REST_FRAMEWORK = {
    "COERCE_DECIMAL_TO_STRING": False,
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apps.accounts.authentication.CookieOrHeaderJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_THROTTLE_CLASSES": ("rest_framework.throttling.AnonRateThrottle",),
    "DEFAULT_THROTTLE_RATES": {
        "anon": env("ANON_THROTTLE_RATE", default="120/min"),
        "login": env("LOGIN_THROTTLE_RATE", default="5/min"),
    },
    "EXCEPTION_HANDLER": "apps.accounts.api.legacy_exception_handler",
}

# Brute-force / account lockout (H-04). After `LOGIN_MAX_FAILED_ATTEMPTS`
# consecutive failures the account is locked for
# `LOGIN_LOCKOUT_BASE_SECONDS * 2 ** consecutive_lockouts` seconds (exponential
# backoff), resetting on a successful login.
LOGIN_MAX_FAILED_ATTEMPTS = env.int("LOGIN_MAX_FAILED_ATTEMPTS", default=5)
LOGIN_LOCKOUT_BASE_SECONDS = env.int("LOGIN_LOCKOUT_BASE_SECONDS", default=30)

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": jwt_lifetime("ACCESS_TOKEN_EXPIRY", "15m"),
    "REFRESH_TOKEN_LIFETIME": jwt_lifetime("REFRESH_TOKEN_EXPIRY", "1d"),
    "SIGNING_KEY": ACCESS_TOKEN_SECRET,
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "_id",
    "CHECK_USER_IS_ACTIVE": True,
}
