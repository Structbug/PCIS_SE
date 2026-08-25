from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

DEBUG = False

_MIN_SECRET_LENGTH = 32


def _require_strong_secret(name, value):
    if value in PLACEHOLDER_SECRETS or len(value) < _MIN_SECRET_LENGTH:
        raise ImproperlyConfigured(
            f"{name} must be a strong random secret (>= {_MIN_SECRET_LENGTH} chars, "
            "not a placeholder). Generate one with: "
            'python -c "import secrets; print(secrets.token_urlsafe(64))"'
        )


_require_strong_secret("DJANGO_SECRET_KEY", SECRET_KEY)  # noqa: F405
_require_strong_secret("ACCESS_TOKEN_SECRET", ACCESS_TOKEN_SECRET)  # noqa: F405

# The container health check connects directly to Gunicorn rather than through
# Coolify's HTTPS proxy.  These loopback hosts make that internal request
# valid without widening the application's public hostname configuration.
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS") + ["localhost", "127.0.0.1"]  # noqa: F405
DATABASES = {"default": env.db("DATABASE_URL")}  # noqa: F405

# Never fall back to the development origins in production. When the SPA is
# served same-origin by Django, an empty allowlist is correct; otherwise set
# CORS_ALLOWED_ORIGINS explicitly in the environment.
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])  # noqa: F405

SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)  # noqa: F405
# Docker checks readiness over HTTP on the loopback interface.  Keep the
# public site HTTPS-only while allowing this data-free local readiness probe.
SECURE_REDIRECT_EXEMPT = [r"^healthz$"]
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# Trust the X-Forwarded-Proto header from TLS-terminating proxies so that
# request.is_secure() and the Secure cookie flag behave correctly.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")  # noqa: F405
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)  # noqa: F405
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Auth/JWT cookies must be Secure and SameSite=Strict in production.
AUTH_COOKIE_SECURE = env.bool("AUTH_COOKIE_SECURE", default=True)  # noqa: F405
AUTH_COOKIE_SAMESITE = env("AUTH_COOKIE_SAMESITE", default="strict")  # noqa: F405
SESSION_COOKIE_SAMESITE = AUTH_COOKIE_SAMESITE
CSRF_COOKIE_SAMESITE = AUTH_COOKIE_SAMESITE

# Content-Security-Policy / Permissions-Policy via a small custom middleware.
MIDDLEWARE.append("apps.accounts.middleware.SecurityHeadersMiddleware")  # noqa: F405
SECURITY_CSP = env.str(  # noqa: F405
    "SECURITY_CSP",
    default=(
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "frame-ancestors 'self'; "
        "base-uri 'self'; "
        "form-action 'self'"
    ),
)
SECURITY_PERMISSIONS_POLICY = env.str(  # noqa: F405
    "SECURITY_PERMISSIONS_POLICY",
    default="geolocation=(), microphone=(), camera=()",
)
