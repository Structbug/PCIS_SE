import hashlib

from rest_framework.throttling import SimpleRateThrottle


class LoginRateThrottle(SimpleRateThrottle):
    """Rate-limit login attempts per source IP **and** per target username.

    Keying on the submitted username (as well as the IP) makes brute-forcing a
    single account across many different IPs impractical, stopping short of a
    full distributed attack (H-04).
    """

    scope = "login"

    def get_cache_key(self, request, view):
        # Only throttle the login endpoint itself.
        if getattr(view, "login_throttle", False) is not True:
            return None
        ident = self.get_ident(request)
        username = request.data.get("username") or ""
        return self.cache_format % {"scope": self.scope, "ident": username or ident}