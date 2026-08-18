"""Shared test client that emulates the browser/SPA CSRF behaviour.

Django's test client sends no Origin and never echoes the csrf cookie back,
which the hardened backend now requires on state-changing requests (H-06).
This client behaves like a real same-origin SPA: it attaches a trusted Origin
on every request and echoes the `csrftoken` cookie as the `X-CSRFToken` header
(the same double-submit pattern axios implements in the frontend).
"""

from rest_framework.test import APIClient, APITestCase


class CsrfCompliantClient(APIClient):
    trusted_origin = "http://testserver"

    def generic(self, method, path, data="", content_type="application/octet-stream", secure=False, **extra):
        if not extra.get("HTTP_ORIGIN"):
            extra["HTTP_ORIGIN"] = self.trusted_origin
        if not extra.get("HTTP_X_CSRFTOKEN"):
            cookie = self.cookies.get("csrftoken")
            if cookie:
                extra["HTTP_X_CSRFTOKEN"] = cookie.value
        return super().generic(method, path, data, content_type, secure, **extra)


class SecurityAwareAPITestCase(APITestCase):
    client_class = CsrfCompliantClient
