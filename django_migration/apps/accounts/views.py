import re
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import hashers
from django.db.models import Q
from django.utils import timezone
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.tokens import RefreshToken

from .api import LegacyAPIError, api_response
from .models import User
from .permissions import IsAdminRole
from .security import enforce_csrf_origin, set_csrf_cookie
from .serializers import (
    PasswordChangeSerializer,
    ProfileSerializer,
    RegisterSerializer,
    UserSerializer,
)
from .throttling import LoginRateThrottle

PAGINATION_LIMIT = 6
OBJECT_ID_PATTERN = re.compile(r"^[0-9a-fA-F]{24}$")

# A bogus hash used purely for timing parity: a login attempt against a
# nonexistent username pays the same password-hashing cost as a wrong-password
# attempt, so account existence is not readable via response time (H-07).
DUMMY_PASSWORD_HASH = hashers.make_password("dummy-hash-for-timing-parity")


def require_object_id(value):
    if not OBJECT_ID_PATTERN.fullmatch(value):
        raise LegacyAPIError(400, f"Invalid ObjectId: {value}")
    return value


def compute_login_lockout_seconds(user, now):
    """Exponential backoff for an account lockout (H-04)."""
    exponent = user.consecutive_lockouts
    seconds = settings.LOGIN_LOCKOUT_BASE_SECONDS * (2**exponent)
    return timedelta(seconds=seconds)


class LoginView(APIView):
    permission_classes = [AllowAny]
    # No DRF authentication: a stale/invalid access cookie (e.g. after the
    # signing key is rotated) must not 401 the login request before the view
    # runs. Origin/Referer is checked explicitly below.
    authentication_classes = []
    throttle_classes = [LoginRateThrottle]
    login_throttle = True

    def post(self, request):
        enforce_csrf_origin(request)
        username = request.data.get("username")
        password = request.data.get("password")
        if not username:
            raise LegacyAPIError(400, "Username is required")
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # Indistinguishable from a wrong password: same status and message,
            # plus a dummy hash check for comparable timing (H-07).
            hashers.check_password(password or "", DUMMY_PASSWORD_HASH)
            raise LegacyAPIError(400, "Invalid User credentials")

        now = timezone.now()
        # Account lockout (H-04): an account locked after repeated failures
        # cannot even be probed until the lock window elapses.
        if user.locked_until and user.locked_until > now:
            raise LegacyAPIError(429, "Too many failed attempts. Try again later.")

        # Generic failure: a deactivated ("deleted") user must not be able to
        # log in, and the message is deliberately generic to avoid revealing
        # account state (H-02 / H-07). Each failure advances the lockout
        # counter (H-04).
        if not user.is_active or not user.check_password(password or ""):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.LOGIN_MAX_FAILED_ATTEMPTS:
                user.locked_until = now + compute_login_lockout_seconds(user, now)
                user.consecutive_lockouts += 1
                user.failed_login_attempts = 0
            user.save(
                update_fields=[
                    "failed_login_attempts",
                    "consecutive_lockouts",
                    "locked_until",
                    "updated_at",
                ]
            )
            raise LegacyAPIError(400, "Invalid User credentials")

        # Successful login: reset the lockout counters.
        if (
            user.failed_login_attempts
            or user.consecutive_lockouts
            or user.locked_until
        ):
            user.failed_login_attempts = 0
            user.consecutive_lockouts = 0
            user.locked_until = None
            user.save(
                update_fields=[
                    "failed_login_attempts",
                    "consecutive_lockouts",
                    "locked_until",
                    "updated_at",
                ]
            )

        refresh = RefreshToken.for_user(user)
        refresh["token_version"] = user.token_version
        access = refresh.access_token
        access["email"] = user.email
        access["role"] = user.role
        access_token, refresh_token = str(access), str(refresh)
        user.refresh_token = refresh_token
        user.save(update_fields=["refresh_token", "updated_at"])
        response = api_response(
            201,
            {
                "accessToken": access_token,
                "refreshToken": refresh_token,
                "user": UserSerializer(user).data,
                "accessTokenExp": access.payload.get("exp"),
                "refreshTokenExp": refresh.payload.get("exp"),
            },
            "User logged in successfully",
        )
        response.set_cookie(
            settings.AUTH_COOKIE_NAME_ACCESS,
            access_token,
            httponly=settings.AUTH_COOKIE_HTTPONLY,
            secure=settings.AUTH_COOKIE_SECURE,
            samesite=settings.AUTH_COOKIE_SAMESITE,
            path=settings.AUTH_COOKIE_PATH,
        )
        response.set_cookie(
            settings.AUTH_COOKIE_NAME_REFRESH,
            refresh_token,
            httponly=settings.AUTH_COOKIE_HTTPONLY,
            secure=settings.AUTH_COOKIE_SECURE,
            samesite=settings.AUTH_COOKIE_SAMESITE,
            path=settings.AUTH_COOKIE_PATH,
        )
        # Issue the double-submit CSRF token cookie used by the SPA on
        # subsequent state-changing requests (H-06).
        set_csrf_cookie(request, response)
        return response


class RegisterView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def post(self, request):
        required_fields = ("username", "email", "password", "role", "phone_number")
        if any(
            not isinstance(request.data.get(field), str)
            or not request.data[field].strip()
            for field in required_fields
        ):
            raise LegacyAPIError(403, "All fields are compulsory.")
        username, email = request.data["username"], request.data["email"]
        existing = User.objects.filter(Q(email=email) | Q(username=username)).first()
        if existing:
            message = "Duplicate entry: "
            if existing.username == username:
                message += "Username is already taken."
            if existing.email == email:
                message += "Email address already exists."
            raise LegacyAPIError(409, message)
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save(created_by=request.user)
        return api_response(201, UserSerializer(user).data, "User registered successfully")


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.user.refresh_token = None
        # Bump the token version so every outstanding access/refresh token is
        # rejected immediately, making logout revoke all sessions (H-03).
        request.user.token_version += 1
        request.user.save(
            update_fields=["refresh_token", "token_version", "updated_at"]
        )
        response = api_response(
            201, UserSerializer(request.user).data, "User logged out successfully."
        )
        # set_cookie(..., max_age=0) so the clearing cookie carries the same
        # Secure/SameSite attributes as the original (delete_cookie() cannot).
        response.set_cookie(
            settings.AUTH_COOKIE_NAME_ACCESS,
            "",
            max_age=0,
            path=settings.AUTH_COOKIE_PATH,
            secure=settings.AUTH_COOKIE_SECURE,
            httponly=settings.AUTH_COOKIE_HTTPONLY,
            samesite=settings.AUTH_COOKIE_SAMESITE,
        )
        response.set_cookie(
            settings.AUTH_COOKIE_NAME_REFRESH,
            "",
            max_age=0,
            path=settings.AUTH_COOKIE_PATH,
            secure=settings.AUTH_COOKIE_SECURE,
            httponly=settings.AUTH_COOKIE_HTTPONLY,
            samesite=settings.AUTH_COOKIE_SAMESITE,
        )
        return response


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data, context={"user": request.user}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if data["new_password"] != data["confirmed_newpassword"]:
            raise LegacyAPIError(400, "New password and confirmed password dont match.")
        if data["current_password"] == data["new_password"]:
            raise LegacyAPIError(
                400, "Current password and new password are the same.Nothing to update"
            )
        if not request.user.check_password(data["current_password"]):
            raise LegacyAPIError(400, "Current password is incorrect.")
        request.user.set_password(data["new_password"])
        # Bump the token version so every previously issued access/refresh
        # token (on all devices) is rejected (M3).
        request.user.token_version += 1
        request.user.save(update_fields=["password", "token_version", "updated_at"])
        return api_response(201, {}, "Password changed Successfully.")


class EditProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        serializer = ProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data.get("email")
        phone_number = serializer.validated_data.get("phone_number")
        if not (email or phone_number):
            raise LegacyAPIError(401, "Provide at least one of the editable profile parameters")
        if email and User.objects.filter(email=email).exclude(pk=request.user.pk).exists():
            raise LegacyAPIError(409, "Email already in use.")
        if phone_number and User.objects.filter(phone_number=phone_number).exclude(
            pk=request.user.pk
        ).exists():
            raise LegacyAPIError(409, "Phone number already in use.")
        if email:
            request.user.email = email
        if phone_number:
            request.user.phone_number = phone_number
        request.user.save(update_fields=["email", "phone_number", "updated_at"])
        return api_response(
            201,
            UserSerializer(request.user).data,
            "Profile editing successful.",
            payload_status_code=200,
        )


class DeleteUserView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def delete(self, request, user_id):
        user_id = require_object_id(user_id.strip())
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            raise LegacyAPIError(404, "User deletion unsuccessful")
        if not user.is_active:
            raise LegacyAPIError(400, "User has already been removed.")
        user.is_active = False
        # Revoke every outstanding session: bump the token version so all
        # previously issued access/refresh tokens are rejected, and drop the
        # stored refresh token (H-02).
        user.token_version += 1
        user.refresh_token = None
        user.save(
            update_fields=["is_active", "token_version", "refresh_token", "updated_at"]
        )
        return api_response(
            200,
            {"_id": user.pk, "username": user.username, "isActive": user.is_active},
            "User deleted successfully.",
        )


class ActiveUsersView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request, page, username=None):
        try:
            page_number = int(page) or 1
        except ValueError:
            page_number = 1
        page_number = max(page_number, 1)
        users = User.objects.filter(is_active=True)
        if username is not None:
            users = users.filter(username__icontains=username)
        total_users = users.count()
        users = users.order_by("username")[
            (page_number - 1) * PAGINATION_LIMIT : page_number * PAGINATION_LIMIT
        ]
        data = {"totalUsers": total_users, "users": UserSerializer(users, many=True).data}
        if total_users == 0:
            return api_response(200, data, "Active users fetched successfully")
        suffix = f"matching {username} " if username is not None else ""
        return api_response(201, data, f"Active users {suffix}fetched successfully")


class RefreshView(APIView):
    # No DRF authentication: the browser sends the (possibly expired) access
    # cookie alongside the refresh cookie, and auth failure would abort the
    # request before we can rotate. Origin/Referer is checked explicitly.
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        # The SPA relies on the httpOnly cookie; body-based refresh is kept for
        # API clients (legacy contract).
        refresh_cookie = request.COOKIES.get(settings.AUTH_COOKIE_NAME_REFRESH)
        refresh_token = refresh_cookie
        if not refresh_token:
            refresh_token = request.data.get("refresh")
        if not refresh_token:
            raise LegacyAPIError(401, "Refresh token missing")
        # Cookie-driven refresh is a browser session, so require the trusted
        # Origin AND the double-submit CSRF token (H-06). A body-supplied
        # refresh token is an explicit client secret a cross-site page cannot
        # read, so it only needs the Origin check.
        enforce_csrf_origin(request, require_token=bool(refresh_cookie))
        try:
            refresh = RefreshToken(refresh_token)
        except Exception:
            raise LegacyAPIError(401, "Invalid refresh token")
        user_id = refresh.get(jwt_settings.USER_ID_CLAIM)
        try:
            user = User.objects.get(pk=user_id)
        except (User.DoesNotExist, TypeError):
            raise LegacyAPIError(401, "Invalid refresh token")
        # Reject tokens for deactivated users (H-02): a removed user must not
        # be able to mint fresh tokens or extend their session.
        if not user.is_active:
            raise LegacyAPIError(401, "Token has been revoked")
        # Reject tokens issued before a password change (M3).
        if refresh.get("token_version", 0) != user.token_version:
            raise LegacyAPIError(401, "Token has been revoked")
        # Only the currently stored refresh token may be rotated. Logout clears
        # it (so post-logout reuse fails) and rotation supersedes older tokens
        # (so replay of a previously used refresh token fails) (H-03).
        if not user.refresh_token or refresh_token != user.refresh_token:
            raise LegacyAPIError(401, "Token has been revoked")

        # Rotate: issue a fresh refresh token and stamp the access token.
        new_refresh = RefreshToken.for_user(user)
        new_refresh["token_version"] = user.token_version
        access = new_refresh.access_token
        access["email"] = user.email
        access["role"] = user.role
        user.refresh_token = str(new_refresh)
        user.save(update_fields=["refresh_token", "updated_at"])

        response = Response(
            {"access": str(access), "refresh": str(new_refresh)},
            status=200,
        )
        response.set_cookie(
            settings.AUTH_COOKIE_NAME_ACCESS,
            str(access),
            httponly=settings.AUTH_COOKIE_HTTPONLY,
            secure=settings.AUTH_COOKIE_SECURE,
            samesite=settings.AUTH_COOKIE_SAMESITE,
            path=settings.AUTH_COOKIE_PATH,
        )
        response.set_cookie(
            settings.AUTH_COOKIE_NAME_REFRESH,
            str(new_refresh),
            httponly=settings.AUTH_COOKIE_HTTPONLY,
            secure=settings.AUTH_COOKIE_SECURE,
            samesite=settings.AUTH_COOKIE_SAMESITE,
            path=settings.AUTH_COOKIE_PATH,
        )
        set_csrf_cookie(request, response)
        return response


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
        refresh_token = request.COOKIES.get(settings.AUTH_COOKIE_NAME_REFRESH)
        access_exp = None
        refresh_exp = None
        if refresh_token:
            try:
                refresh = RefreshToken(refresh_token)
                refresh_exp = refresh.payload.get("exp")
            except Exception:
                pass
        access_token = request.COOKIES.get(settings.AUTH_COOKIE_NAME_ACCESS)
        if access_token:
            try:
                access = AccessToken(access_token)
                access_exp = access.payload.get("exp")
            except Exception:
                pass
        return api_response(
            201,
            {
                "user": UserSerializer(request.user).data,
                "accessTokenExp": access_exp,
                "refreshTokenExp": refresh_exp,
            },
            "Current user fetched successfully",
        )
