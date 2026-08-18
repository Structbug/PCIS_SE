from secrets import compare_digest, token_urlsafe
from urllib.parse import urlparse

from django.conf import settings
from rest_framework.exceptions import PermissionDenied

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _normalize_origin(value):
    if not value:
        return None
    parsed = urlparse(value)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"


def request_origin(request):
    """Best-effort Origin of the request: the Origin header, else Referer."""
    origin = request.META.get("HTTP_ORIGIN")
    if origin:
        return _normalize_origin(origin)
    referer = request.META.get("HTTP_REFERER")
    if referer:
        parsed = urlparse(referer)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"
    return None


def trusted_origins(request):
    """Origins a state-changing browser request may legitimately come from.

    Includes the configured CORS allowlist, any CSRF_TRUSTED_ORIGINS, and the
    request's own origin so a same-origin SPA deployment keeps working.
    """
    origins = set(settings.CORS_ALLOWED_ORIGINS)
    origins.update(getattr(settings, "CSRF_TRUSTED_ORIGINS", []))
    scheme = "https" if request.is_secure() else "http"
    origins.add(f"{scheme}://{request.get_host().lower()}")
    return origins


def set_csrf_cookie(request, response):
    """Set the non-httpOnly double-submit CSRF token cookie (H-06)."""
    token = token_urlsafe(32)
    response.set_cookie(
        settings.CSRF_COOKIE_NAME,
        token,
        max_age=None,
        path=settings.CSRF_COOKIE_PATH,
        secure=settings.AUTH_COOKIE_SECURE,
        httponly=False,
        samesite=settings.AUTH_COOKIE_SAMESITE,
    )
    return response


def _validate_csrf_token(request):
    """Double-submit check: the token header must equal the CSRF cookie.

    A cross-site attacker cannot read the (SameSite=Strict, non-httpOnly)
    cookie from another origin, so it cannot reproduce it in a header. This is
    a second line of defence behind the Origin check (H-06).
    """
    submitted = request.META.get("HTTP_X_CSRFTOKEN")
    expected = request.COOKIES.get(settings.CSRF_COOKIE_NAME)
    if not submitted or not expected or not compare_digest(submitted, expected):
        raise PermissionDenied("CSRF check failed")


def enforce_csrf_origin(request, *, require_token=False):
    """Reject state-changing requests that cannot be trusted as browser-origin.

    - Any state-changing request must carry an Origin/Referer that resolves to
      a trusted origin (H-06). A missing header is rejected: browsers always
      attach Origin on cross-origin unsafe requests, and cookie-based sessions
      must never accept an ambiguous request.
    - When `require_token` is set (cookie-authenticated browser requests), the
      double-submit CSRF token is enforced in addition.
    - Requests authenticated via an explicit `Authorization: Bearer` header are
      not run through this check (see CookieOrHeaderJWTAuthentication) because
      they carry an explicit client secret rather than ambient cookies and so
      are not CSRF-able; they may carry *any* Origin.
    """
    if request.method not in UNSAFE_METHODS:
        return
    origin = request_origin(request)
    if origin is None or origin not in trusted_origins(request):
        raise PermissionDenied("Cross-origin request rejected")
    if require_token:
        _validate_csrf_token(request)