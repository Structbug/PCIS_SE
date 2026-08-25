import os
import tempfile
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.test import override_settings
from django.test import SimpleTestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch

from .models import User
from .testutils import SecurityAwareAPITestCase
from .throttling import LoginRateThrottle


class UserResourceTests(SecurityAwareAPITestCase):
    def setUp(self):
        self.admin_password = "correct-horse-battery-staple"
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password=self.admin_password,
            phone_number="9800000000",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        self.user = User.objects.create_user(
            username="inventory-user",
            email="user@example.com",
            password="another-safe-password",
            phone_number="9811111111",
            role=User.Role.USER,
        )

    def assert_legacy_error(self, response, expected_status):
        self.assertEqual(response.status_code, expected_status)
        self.assertEqual(response.data["statusCode"], expected_status)
        self.assertFalse(response.data["success"])
        self.assertIsNone(response.data["data"])

    def login(self, username="admin", password=None):
        response = self.client.post(
            "/api/v1/users/login",
            {"username": username, "password": password or self.admin_password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["statusCode"], status.HTTP_201_CREATED)
        self.assertIn("accessToken", response.data["data"])
        self.assertIn("refreshToken", response.data["data"])
        self.assertIn("accessToken", response.cookies)
        return response

    def authenticate_as_admin(self):
        response = self.login()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['data']['accessToken']}")
        return response

    def test_model_matches_mongoose_user_shape(self):
        self.assertEqual(len(self.admin.pk), 24)
        self.assertTrue(self.admin.is_active)
        self.assertIsNone(self.admin.refresh_token)
        self.assertIsNone(self.admin.created_by)
        self.assertTrue(self.admin.check_password(self.admin_password))
        self.assertEqual(User._meta.get_field("created_by").remote_field.on_delete.__name__, "SET_NULL")

    def test_login_returns_mern_shape_and_errors(self):
        successful = self.login()
        self.assertEqual(successful.data["data"]["accessToken"].count("."), 2)
        self.assert_legacy_error(
            self.client.post("/api/v1/users/login", {"password": "x"}, format="json"),
            status.HTTP_400_BAD_REQUEST,
        )
        self.assert_legacy_error(
            self.client.post(
                "/api/v1/users/login",
                {"username": "missing", "password": "x"},
                format="json",
            ),
            status.HTTP_400_BAD_REQUEST,
        )
        self.assert_legacy_error(
            self.client.post(
                "/api/v1/users/login",
                {"username": "admin", "password": "wrong"},
                format="json",
            ),
            status.HTTP_400_BAD_REQUEST,
        )

    def test_missing_username_and_wrong_password_are_indistinguishable(self):
        # H-07: a nonexistent username must produce the same response (status,
        # message, payload) as a wrong password so usernames cannot be enumerated.
        missing = self.client.post(
            "/api/v1/users/login",
            {"username": "definitely-not-a-user", "password": "whatever"},
            format="json",
        )
        wrong_pw = self.client.post(
            "/api/v1/users/login",
            {"username": "admin", "password": "wrong"},
            format="json",
        )
        self.assertEqual(missing.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(wrong_pw.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(missing.data["message"], wrong_pw.data["message"])
        self.assertEqual(missing.data["statusCode"], wrong_pw.data["statusCode"])
        self.assertEqual(missing.data["data"], wrong_pw.data["data"])
        self.assertEqual(missing.data["message"], "Invalid User credentials")

    def test_admin_registers_user_and_duplicate_and_required_errors_match(self):
        unauthenticated = self.client.post("/api/v1/users/register", {}, format="json")
        self.assert_legacy_error(unauthenticated, status.HTTP_401_UNAUTHORIZED)
        self.authenticate_as_admin()
        incomplete = self.client.post(
            "/api/v1/users/register", {"username": "only-name"}, format="json"
        )
        self.assert_legacy_error(incomplete, status.HTTP_403_FORBIDDEN)
        duplicate = self.client.post(
            "/api/v1/users/register",
            {
                "username": "inventory-user",
                "email": "new@example.com",
                "password": "safe-password-123",
                "phone_number": "9822222222",
                "role": "User",
            },
            format="json",
        )
        self.assert_legacy_error(duplicate, status.HTTP_409_CONFLICT)
        response = self.client.post(
            "/api/v1/users/register",
            {
                "username": "created-user",
                "email": "created@example.com",
                "password": "safe-password-123",
                "phone_number": "9833333333",
                "role": "User",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["username"], "created-user")
        self.assertEqual(response.data["data"]["createdBy"], self.admin.pk)
        self.assertNotIn("password", response.data["data"])

    def test_non_admin_cannot_register_or_list_or_delete_users(self):
        login = self.client.post(
            "/api/v1/users/login",
            {"username": self.user.username, "password": "another-safe-password"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['data']['accessToken']}")
        self.assert_legacy_error(
            self.client.get("/api/v1/users/active/1"), status.HTTP_403_FORBIDDEN
        )
        self.assert_legacy_error(
            self.client.delete(f"/api/v1/users/{self.admin.pk}"), status.HTTP_403_FORBIDDEN
        )

    def test_change_password_matches_success_and_validation_errors(self):
        self.authenticate_as_admin()
        mismatch = self.client.patch(
            "/api/v1/users/change-password",
            {
                "current_password": self.admin_password,
                "new_password": "new-admin-password",
                "confirmed_newpassword": "different-password",
            },
            format="json",
        )
        self.assert_legacy_error(mismatch, status.HTTP_400_BAD_REQUEST)
        success = self.client.patch(
            "/api/v1/users/change-password",
            {
                "current_password": self.admin_password,
                "new_password": "new-admin-password",
                "confirmed_newpassword": "new-admin-password",
            },
            format="json",
        )
        self.assertEqual(success.status_code, status.HTTP_201_CREATED)
        self.assertEqual(success.data["data"], {})
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password("new-admin-password"))

    def test_edit_profile_keeps_original_http_and_payload_status_mismatch(self):
        self.authenticate_as_admin()
        empty = self.client.patch("/api/v1/users/edit-profile", {}, format="json")
        self.assert_legacy_error(empty, status.HTTP_401_UNAUTHORIZED)
        success = self.client.patch(
            "/api/v1/users/edit-profile",
            {"email": "changed@example.com"},
            format="json",
        )
        self.assertEqual(success.status_code, status.HTTP_201_CREATED)
        self.assertEqual(success.data["statusCode"], status.HTTP_200_OK)
        self.assertEqual(success.data["data"]["email"], "changed@example.com")

    def test_logout_clears_stored_refresh_token_and_returns_user(self):
        self.authenticate_as_admin()
        self.admin.refresh_from_db()
        self.assertIsNotNone(self.admin.refresh_token)
        response = self.client.post("/api/v1/users/logout")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["_id"], self.admin.pk)
        self.admin.refresh_from_db()
        self.assertIsNone(self.admin.refresh_token)

    def test_delete_user_is_soft_delete_with_original_edge_cases(self):
        self.authenticate_as_admin()
        invalid = self.client.delete("/api/v1/users/not-an-object-id")
        self.assert_legacy_error(invalid, status.HTTP_400_BAD_REQUEST)
        success = self.client.delete(f"/api/v1/users/{self.user.pk}")
        self.assertEqual(success.status_code, status.HTTP_200_OK)
        self.assertFalse(success.data["data"]["isActive"])
        already_deleted = self.client.delete(f"/api/v1/users/{self.user.pk}")
        self.assert_legacy_error(already_deleted, status.HTTP_400_BAD_REQUEST)

    def test_active_list_search_and_current_user_routes(self):
        self.authenticate_as_admin()
        listed = self.client.get("/api/v1/users/active/1")
        self.assertEqual(listed.status_code, status.HTTP_201_CREATED)
        self.assertEqual(listed.data["data"]["totalUsers"], 2)
        searched = self.client.get("/api/v1/users/admin/1")
        self.assertEqual(searched.status_code, status.HTTP_201_CREATED)
        self.assertEqual(searched.data["data"]["users"][0]["username"], "admin")
        empty_search = self.client.get("/api/v1/users/no-match/1")
        self.assertEqual(empty_search.status_code, status.HTTP_200_OK)
        self.assertEqual(empty_search.data["data"], {"totalUsers": 0, "users": []})
        current = self.client.get("/api/v1/users/current-user")
        self.assertEqual(current.status_code, status.HTTP_201_CREATED)
        self.assertEqual(current.data["data"]["user"]["role"], "Admin")

    def test_refresh_endpoint_from_auth_foundation_remains_working(self):
        login = self.login()
        refreshed = self.client.post(
            "/api/v1/users/refresh",
            {"refresh": login.data["data"]["refreshToken"]},
            format="json",
        )
        self.assertEqual(refreshed.status_code, status.HTTP_200_OK)
        self.assertIn("access", refreshed.data)


class SecurityHeaderAndCSRFTests(SecurityAwareAPITestCase):
    def setUp(self):
        self.admin_password = "correct-horse-battery-staple"
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password=self.admin_password,
            phone_number="9800000000",
            role=User.Role.ADMIN,
            is_staff=True,
        )

    def login(self):
        response = self.client.post(
            "/api/v1/users/login",
            {"username": "admin", "password": self.admin_password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response

    def assert_legacy_error(self, response, expected_status):
        self.assertEqual(response.status_code, expected_status)
        self.assertEqual(response.data["statusCode"], expected_status)
        self.assertFalse(response.data["success"])
        self.assertIsNone(response.data["data"])

    def test_login_cookies_are_httponly_samesite_strict(self):
        response = self.login()
        access = response.cookies["accessToken"]
        refresh = response.cookies["refreshToken"]
        for cookie in (access, refresh):
            self.assertEqual(cookie["httponly"], True)
            self.assertEqual(cookie["samesite"], "strict")
            self.assertEqual(cookie["path"], "/")

    def test_cross_origin_cookie_authenticated_write_is_rejected(self):
        self.login()
        response = self.client.patch(
            "/api/v1/users/edit-profile",
            {"email": "evil@example.com"},
            HTTP_ORIGIN="https://evil.example.com",
            format="json",
        )
        self.assert_legacy_error(response, status.HTTP_403_FORBIDDEN)

    def test_trusted_origin_cookie_authenticated_write_is_allowed(self):
        self.login()
        response = self.client.patch(
            "/api/v1/users/edit-profile",
            {"email": "fine@example.com"},
            HTTP_ORIGIN="http://localhost:5173",
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["email"], "fine@example.com")

    def test_authorization_header_cross_origin_write_is_allowed(self):
        login = self.login()
        response = self.client.patch(
            "/api/v1/users/edit-profile",
            {"email": "header@example.com"},
            HTTP_AUTHORIZATION=f"Bearer {login.data['data']['accessToken']}",
            HTTP_ORIGIN="https://evil.example.com",
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["email"], "header@example.com")

    def test_login_rejects_cross_site_origin(self):
        response = self.client.post(
            "/api/v1/users/login",
            {"username": "admin", "password": self.admin_password},
            HTTP_ORIGIN="https://evil.example.com",
            format="json",
        )
        self.assert_legacy_error(response, status.HTTP_403_FORBIDDEN)

    def test_login_without_origin_is_rejected(self):
        from rest_framework.test import APIClient as RawAPIClient

        response = RawAPIClient().post(
            "/api/v1/users/login",
            {"username": "admin", "password": self.admin_password},
            format="json",
        )
        self.assert_legacy_error(response, status.HTTP_403_FORBIDDEN)

    def test_cookie_auth_write_without_origin_is_rejected(self):
        from rest_framework.test import APIClient as RawAPIClient

        self.login()
        raw = RawAPIClient()
        for key, morsel in self.client.cookies.items():
            raw.cookies[key] = morsel
        response = raw.patch(
            "/api/v1/users/edit-profile",
            {"email": "noorigin@example.com"},
            format="json",
        )
        self.assert_legacy_error(response, status.HTTP_403_FORBIDDEN)

    def test_cookie_auth_write_with_forged_csrf_token_is_rejected(self):
        self.login()
        response = self.client.patch(
            "/api/v1/users/edit-profile",
            {"email": "forged@example.com"},
            HTTP_ORIGIN="http://localhost:5173",
            HTTP_X_CSRFTOKEN="forged-token-value",
            format="json",
        )
        self.assert_legacy_error(response, status.HTTP_403_FORBIDDEN)

    def test_cookie_auth_write_without_csrf_token_is_rejected(self):
        self.login()
        self.client.cookies.pop("csrftoken", None)
        response = self.client.patch(
            "/api/v1/users/edit-profile",
            {"email": "notoken@example.com"},
            HTTP_ORIGIN="http://localhost:5173",
            format="json",
        )
        self.assert_legacy_error(response, status.HTTP_403_FORBIDDEN)

    def test_login_sets_non_httponly_csrf_cookie(self):
        response = self.login()
        csrf = response.cookies["csrftoken"]
        self.assertFalse(csrf["httponly"])
        self.assertEqual(csrf["samesite"], "strict")
        self.assertTrue(csrf.value)

    def test_security_headers_middleware_sets_csp_and_permissions_policy(self):
        from django.http import JsonResponse
        from django.test import RequestFactory, override_settings

        from .middleware import SecurityHeadersMiddleware

        request = RequestFactory().get("/")
        middleware = SecurityHeadersMiddleware(lambda r: JsonResponse({}))
        with override_settings(
            SECURITY_CSP="default-src 'self'",
            SECURITY_PERMISSIONS_POLICY="geolocation=()",
        ):
            response = middleware(request)
        self.assertEqual(response["Content-Security-Policy"], "default-src 'self'")
        self.assertEqual(response["Permissions-Policy"], "geolocation=()")


class TokenVersionAndRefreshTests(SecurityAwareAPITestCase):
    def setUp(self):
        self.admin_password = "correct-horse-battery-staple"
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password=self.admin_password,
            phone_number="9800000000",
            role=User.Role.ADMIN,
            is_staff=True,
        )

    def login(self):
        response = self.client.post(
            "/api/v1/users/login",
            {"username": "admin", "password": self.admin_password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response

    def change_password(self):
        self.client.patch(
            "/api/v1/users/change-password",
            {
                "current_password": self.admin_password,
                "new_password": "a-new-admin-password",
                "confirmed_newpassword": "a-new-admin-password",
            },
            format="json",
        )
        self.admin.refresh_from_db()

    def test_password_change_revokes_existing_access_token(self):
        login = self.login()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['data']['accessToken']}")
        self.change_password()
        current = self.client.get("/api/v1/users/current-user")
        self.assertEqual(current.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(current.data["statusCode"], status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(current.data["success"])

    def test_password_change_revokes_refresh_token(self):
        login = self.login()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['data']['accessToken']}")
        self.change_password()
        self.client.cookies.clear()
        refreshed = self.client.post(
            "/api/v1/users/refresh",
            {"refresh": login.data["data"]["refreshToken"]},
            format="json",
        )
        self.assertEqual(refreshed.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(refreshed.data["statusCode"], status.HTTP_401_UNAUTHORIZED)

    def test_refresh_reads_token_from_cookie_and_rotates(self):
        login = self.login()
        refreshed = self.client.post("/api/v1/users/refresh", {}, format="json")
        self.assertEqual(refreshed.status_code, status.HTTP_200_OK)
        self.assertIn("access", refreshed.data)
        self.assertNotEqual(refreshed.data["refresh"], login.data["data"]["refreshToken"])
        self.assertIn("accessToken", refreshed.cookies)
        self.assertIn("refreshToken", refreshed.cookies)
        current = self.client.get("/api/v1/users/current-user")
        self.assertEqual(current.status_code, status.HTTP_201_CREATED)

    def test_refresh_body_fallback_when_no_cookie(self):
        login = self.login()
        self.client.cookies.clear()
        refreshed = self.client.post(
            "/api/v1/users/refresh",
            {"refresh": login.data["data"]["refreshToken"]},
            format="json",
        )
        self.assertEqual(refreshed.status_code, status.HTTP_200_OK)
        self.assertIn("access", refreshed.data)
        self.assertIn("refresh", refreshed.data)

    def test_refresh_missing_token_returns_401(self):
        response = self.client.post("/api/v1/users/refresh", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["statusCode"], status.HTTP_401_UNAUTHORIZED)

    def test_refresh_works_even_when_access_cookie_is_expired(self):
        from datetime import timedelta

        from django.utils import timezone
        from rest_framework_simplejwt.tokens import AccessToken

        login = self.login()
        expired_access = AccessToken.for_user(self.admin)
        expired_access["exp"] = int((timezone.now() - timedelta(hours=1)).timestamp())
        self.client.cookies[settings.AUTH_COOKIE_NAME_ACCESS] = str(expired_access)
        refreshed = self.client.post("/api/v1/users/refresh", {}, format="json")
        self.assertEqual(refreshed.status_code, status.HTTP_200_OK)
        self.assertIn("access", refreshed.data)
        current = self.client.get("/api/v1/users/current-user")
        self.assertEqual(current.status_code, status.HTTP_201_CREATED)


class DeactivatedUserRevocationTests(SecurityAwareAPITestCase):
    """H-02: a deactivated ("deleted") user must lose all access immediately."""

    def setUp(self):
        self.admin_password = "correct-horse-battery-staple"
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password=self.admin_password,
            phone_number="9800000000",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        self.user_password = "another-safe-password"
        self.user = User.objects.create_user(
            username="inventory-user",
            email="user@example.com",
            password=self.user_password,
            phone_number="9811111111",
            role=User.Role.USER,
        )

    def assert_legacy_error(self, response, expected_status):
        self.assertEqual(response.status_code, expected_status)
        self.assertFalse(response.data["success"])

    def test_inactive_user_cannot_log_in(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        response = self.client.post(
            "/api/v1/users/login",
            {"username": self.user.username, "password": self.user_password},
            format="json",
        )
        self.assert_legacy_error(response, status.HTTP_400_BAD_REQUEST)

    def test_deactivate_revokes_already_issued_access_and_refresh_tokens(self):
        self.admin_login = self.client.post(
            "/api/v1/users/login",
            {"username": "admin", "password": self.admin_password},
            format="json",
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.admin_login.data['data']['accessToken']}"
        )
        victim_login = self.client.post(
            "/api/v1/users/login",
            {"username": self.user.username, "password": self.user_password},
            format="json",
        )
        old_access = victim_login.data["data"]["accessToken"]
        old_refresh = victim_login.data["data"]["refreshToken"]

        response = self.client.delete(f"/api/v1/users/{self.user.pk}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertIsNone(self.user.refresh_token)
        self.assertEqual(self.user.token_version, 1)

        # Clear stored admin credentials; the victim's old access token must now
        # be rejected.
        self.client.credentials()
        current = self.client.get(
            "/api/v1/users/current-user",
            HTTP_AUTHORIZATION=f"Bearer {old_access}",
        )
        self.assertEqual(current.status_code, status.HTTP_401_UNAUTHORIZED)

        # Refresh of the old token must be rejected.
        self.client.cookies.clear()
        refreshed = self.client.post(
            "/api/v1/users/refresh",
            {"refresh": old_refresh},
            format="json",
        )
        self.assert_legacy_error(refreshed, status.HTTP_401_UNAUTHORIZED)


class LogoutRevocationTests(SecurityAwareAPITestCase):
    """H-03: logout must invalidate the outstanding refresh token."""

    def setUp(self):
        self.password = "correct-horse-battery-staple"
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password=self.password,
            phone_number="9800000000",
            role=User.Role.ADMIN,
            is_staff=True,
        )

    def login(self):
        return self.client.post(
            "/api/v1/users/login",
            {"username": "admin", "password": self.password},
            format="json",
        )

    def test_logout_revokes_refresh_token_reuse(self):
        login = self.login()
        refresh = login.data["data"]["refreshToken"]
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login.data['data']['accessToken']}"
        )
        logout = self.client.post("/api/v1/users/logout")
        self.assertEqual(logout.status_code, status.HTTP_201_CREATED)
        self.admin.refresh_from_db()
        self.assertIsNone(self.admin.refresh_token)
        self.assertEqual(self.admin.token_version, 1)
        self.client.cookies.clear()
        reused = self.client.post(
            "/api/v1/users/refresh", {"refresh": refresh}, format="json"
        )
        self.assertEqual(reused.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(reused.data["success"])

    def test_refresh_token_cannot_be_replayed_after_rotation(self):
        login = self.login()
        first_refresh = login.data["data"]["refreshToken"]
        rotated = self.client.post(
            "/api/v1/users/refresh", {"refresh": first_refresh}, format="json"
        )
        self.assertEqual(rotated.status_code, status.HTTP_200_OK)
        self.client.cookies.clear()
        replayed = self.client.post(
            "/api/v1/users/refresh", {"refresh": first_refresh}, format="json"
        )
        self.assertEqual(replayed.status_code, status.HTTP_401_UNAUTHORIZED)


class LoginRateLimitAndLockoutTests(SecurityAwareAPITestCase):
    """H-04: login throttling (429) and account lockout/backoff."""

    def setUp(self):
        self.password = "correct-horse-battery-staple"
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password=self.password,
            phone_number="9800000000",
            role=User.Role.ADMIN,
            is_staff=True,
        )

    def attempt(self, password="wrong-password"):
        return self.client.post(
            "/api/v1/users/login",
            {"username": "admin", "password": password},
            format="json",
        )

    def test_rapid_login_requests_are_throttled_with_429(self):
        # DRF caches THROTTLE_RATES as a class attribute at import time, so the
        # rate is tuned by patching it rather than override_settings. Clear the
        # shared LocMemCache first so earlier logins (same username key) don't
        # skew the window.
        cache.clear()
        with patch.object(LoginRateThrottle, "THROTTLE_RATES", {"login": "2/min"}):
            self.assertEqual(self.attempt().status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(self.attempt().status_code, status.HTTP_400_BAD_REQUEST)
            throttled = self.attempt()
            self.assertEqual(throttled.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
            self.assertFalse(throttled.data["success"])

    def test_account_locks_after_max_failed_attempts(self):
        with override_settings(
            LOGIN_MAX_FAILED_ATTEMPTS=3,
            LOGIN_LOCKOUT_BASE_SECONDS=3600,
        ):
            for _ in range(3):
                self.assertIn(self.attempt().status_code, (400, 429))
            locked = self.attempt(self.password)
            self.assertEqual(locked.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.consecutive_lockouts, 1)
        self.assertFalse(self.admin.failed_login_attempts)
        self.assertIsNotNone(self.admin.locked_until)

    def test_successful_login_resets_lockout_counters(self):
        with override_settings(LOGIN_MAX_FAILED_ATTEMPTS=3):
            self.attempt()
            self.attempt()
            ok = self.client.post(
                "/api/v1/users/login",
                {"username": "admin", "password": self.password},
                format="json",
            )
            self.assertEqual(ok.status_code, status.HTTP_201_CREATED)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.failed_login_attempts, 0)
        self.assertEqual(self.admin.consecutive_lockouts, 0)
        self.assertIsNone(self.admin.locked_until)


class PasswordValidationTests(SecurityAwareAPITestCase):
    """H-09: the configured Django password validators run on register and
    change-password, so weak passwords like `password` are rejected."""

    def setUp(self):
        self.admin_password = "correct-horse-battery-staple"
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password=self.admin_password,
            phone_number="9800000000",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        login = self.client.post(
            "/api/v1/users/login",
            {"username": "admin", "password": self.admin_password},
            format="json",
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login.data['data']['accessToken']}"
        )

    def register(self, password):
        return self.client.post(
            "/api/v1/users/register",
            {
                "username": "new-user",
                "email": "new@example.com",
                "password": password,
                "phone_number": "9822222222",
                "role": "User",
            },
            format="json",
        )

    def assert_weak_password_rejected(self, response):
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_register_rejects_short_password(self):
        self.assert_weak_password_rejected(self.register("1234567"))

    def test_register_accepts_numeric_password(self):
        response = self.register("12345678")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_register_accepts_password_similar_to_username(self):
        response = self.client.post(
            "/api/v1/users/register",
            {
                "username": "user1",
                "email": "user1@example.com",
                "password": "user1234",
                "phone_number": "9831214356",
                "role": "User",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_change_password_accepts_common_password(self):
        response = self.client.patch(
            "/api/v1/users/change-password",
            {
                "current_password": self.admin_password,
                "new_password": "password",
                "confirmed_newpassword": "password",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password("password"))

    def test_change_password_accepts_strong_password(self):
        ok = self.client.patch(
            "/api/v1/users/change-password",
            {
                "current_password": self.admin_password,
                "new_password": "a-unique-strong-pw-987",
                "confirmed_newpassword": "a-unique-strong-pw-987",
            },
            format="json",
        )
        self.assertEqual(ok.status_code, status.HTTP_201_CREATED)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password("a-unique-strong-pw-987"))


class SettingsModuleSelectionTests(SimpleTestCase):
    """H-10: DJANGO_SETTINGS_MODULE must be chosen explicitly; booting must
    never silently fall back to the DEBUG=True dev module."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from config import load_settings as loader

        cls.loader = loader

    def test_explicit_env_var_wins(self):
        with patch.dict(os.environ, {"DJANGO_SETTINGS_MODULE": "config.settings.prod"}, clear=True):
            self.assertEqual(
                self.loader.resolve_settings_module(), "config.settings.prod"
            )

    def test_dotenv_supplies_module_when_env_var_unset(self):
        with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False) as fh:
            fh.write("DJANGO_SETTINGS_MODULE=config.settings.test\n")
            dotenv_path = fh.name
        try:
            with patch.dict(os.environ, {}, clear=True):
                with patch.object(self.loader, "ENV_FILE", Path(dotenv_path)):
                    self.assertEqual(
                        self.loader.resolve_settings_module(), "config.settings.test"
                    )
        finally:
            Path(dotenv_path).unlink(missing_ok=True)

    def test_missing_module_fails_loudly(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(self.loader, "ENV_FILE", Path("/nonexistent-na/.env")):
                with patch("sys.argv", ["manage.py", "runserver"]):
                    with self.assertRaises(SystemExit) as ctx:
                        self.loader.resolve_settings_module()
                    self.assertEqual(ctx.exception.code, 1)

    def test_settings_flag_is_left_to_django(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("sys.argv", ["manage.py", "runserver", "--settings", "config.settings.test"]):
                self.assertEqual(self.loader.resolve_settings_module(), "")
