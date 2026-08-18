from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from .security import enforce_csrf_origin


class CookieOrHeaderJWTAuthentication(JWTAuthentication):
    """Accept the MERN Bearer header or its accessToken HTTP-only cookie."""

    def authenticate(self, request):
        header = self.get_header(request)
        raw_token = self.get_raw_token(header) if header else None
        from_cookie = False
        if raw_token is None:
            raw_token = request.COOKIES.get(settings.AUTH_COOKIE_NAME_ACCESS)
            if raw_token is not None:
                raw_token = raw_token.encode("utf-8")
                from_cookie = True
        if raw_token is None:
            return None
        validated_token = self.get_validated_token(raw_token)
        user = self.get_user(validated_token)
        # A request authenticated from the cookie can be driven by a cross-site
        # page, so enforce Origin/Referer validation and the double-submit CSRF
        # token (header auth cannot be forged cross-site and is exempt).
        if from_cookie:
            enforce_csrf_origin(request, require_token=True)
        # Tokens issued before a password change carry an older token_version
        # and must be rejected (M3).
        if validated_token.get("token_version", 0) != user.token_version:
            raise AuthenticationFailed("Token has been revoked")
        return user, validated_token
