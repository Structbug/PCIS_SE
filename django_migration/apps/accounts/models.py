from django.contrib.auth.models import UserManager as DjangoUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from secrets import token_hex


def generate_object_id():
    """Generate a 24-character hexadecimal identifier compatible with Mongo ObjectIds."""
    return token_hex(12)


class UserManager(DjangoUserManager):
    def create_superuser(self, username=None, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.ADMIN)
        return super().create_superuser(username, email, password, **extra_fields)


class AccessRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "Pending", "Pending"
        APPROVED = "Approved", "Approved"
        DENIED = "Denied", "Denied"

    id = models.CharField(
        primary_key=True, max_length=24, default=generate_object_id, editable=False
    )
    fullName = models.TextField()
    email = models.EmailField()
    department = models.TextField()
    rollNo = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "access_requests"
        ordering = ["-created_at"]


class BlockedRequester(models.Model):
    """Admins can blacklist an email from submitting further access requests.

    The email is stored normalized (lower-cased, stripped) so the uniqueness
    check in the create view matches regardless of case or surrounding spaces.
    """

    id = models.CharField(
        primary_key=True, max_length=24, default=generate_object_id, editable=False
    )
    email = models.EmailField(unique=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="blocked_requesters",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "blocked_requesters"
        ordering = ["-created_at"]


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "Admin", "Admin"
        USER = "User", "User"

    id = models.CharField(
        primary_key=True, max_length=24, default=generate_object_id, editable=False
    )
    username = models.TextField(unique=True)
    email = models.TextField(unique=True)
    phone_number = models.TextField(unique=True)
    role = models.CharField(max_length=5, choices=Role.choices, default=Role.USER)
    created_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_users",
    )
    is_active = models.BooleanField(default=True, db_column="isActive")
    refresh_token = models.TextField(null=True, blank=True)
    token_version = models.IntegerField(default=0)
    failed_login_attempts = models.IntegerField(default=0)
    consecutive_lockouts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    def __str__(self):
        return self.username
