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
