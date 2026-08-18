from django.conf import settings


class SecurityHeadersMiddleware:
    """Apply Content-Security-Policy and Permissions-Policy headers.

    Intended for production (added to MIDDLEWARE in config/settings/prod.py);
    no-ops when the settings are unset.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        csp = getattr(settings, "SECURITY_CSP", None)
        if csp:
            response["Content-Security-Policy"] = csp
        permissions = getattr(settings, "SECURITY_PERMISSIONS_POLICY", None)
        if permissions:
            response["Permissions-Policy"] = permissions
        return response
