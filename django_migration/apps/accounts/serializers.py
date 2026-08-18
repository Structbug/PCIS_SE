from django.contrib.auth.password_validation import (
    validate_password as django_validate_password,
)
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import RegexValidator
from rest_framework import serializers

from .models import AccessRequest, BlockedRequester, User

USERNAME_REGEX = RegexValidator(
    regex=r"^[\w.@+-]+$",
    message="Username may only contain letters, digits, and @/./+/-/_ characters.",
)
PHONE_REGEX = RegexValidator(
    regex=r"^[0-9+\-() ]+$",
    message="Phone number may only contain digits, spaces, and + - ( ) characters.",
)


class UserSerializer(serializers.ModelSerializer):
    _id = serializers.CharField(source="pk", read_only=True)
    createdBy = serializers.CharField(source="created_by_id", read_only=True, allow_null=True)
    isActive = serializers.BooleanField(source="is_active", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = User
        fields = (
            "_id",
            "username",
            "email",
            "phone_number",
            "role",
            "createdBy",
            "isActive",
            "createdAt",
            "updatedAt",
        )


class RegisterSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        max_length=150, validators=[USERNAME_REGEX]
    )
    email = serializers.EmailField(max_length=254)
    phone_number = serializers.CharField(
        max_length=20, validators=[PHONE_REGEX]
    )
    password = serializers.CharField(write_only=True, min_length=8, max_length=128)

    class Meta:
        model = User
        fields = ("username", "email", "password", "phone_number", "role")

    def validate_password(self, value):
        # Run the full Django password validation chain (H-09), including the
        # UserAttributeSimilarityValidator against the credentials being
        # registered. `initial_data` is used because validated_data is not yet
        # available at field-validation time.
        user = User(
            username=self.initial_data.get("username", ""),
            email=self.initial_data.get("email", ""),
        )
        try:
            django_validate_password(value, user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class ProfileSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_blank=True, max_length=254)
    phone_number = serializers.CharField(
        required=False, allow_blank=True, max_length=20, validators=[PHONE_REGEX]
    )


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField()
    new_password = serializers.CharField()
    confirmed_newpassword = serializers.CharField()

    def validate_new_password(self, value):
        # Enforce the same Django password policy on password change (H-09).
        try:
            django_validate_password(value, user=self.context.get("user"))
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)
        return value


class CurrentUserSerializer(serializers.ModelSerializer):
    _id = serializers.CharField(source="pk", read_only=True)

    class Meta:
        model = User
        fields = ("_id", "username", "email", "role")


class AccessRequestSerializer(serializers.ModelSerializer):
    _id = serializers.CharField(source="pk", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = AccessRequest
        fields = (
            "_id",
            "fullName",
            "email",
            "department",
            "rollNo",
            "description",
            "status",
            "createdAt",
            "updatedAt",
        )


class BlockedRequesterSerializer(serializers.ModelSerializer):
    _id = serializers.CharField(source="pk", read_only=True)
    createdBy = serializers.CharField(source="created_by_id", read_only=True, allow_null=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = BlockedRequester
        fields = ("_id", "email", "createdBy", "createdAt", "updatedAt")
