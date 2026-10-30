"""
Serializers do two jobs, like a DTO + Bean Validation in Spring:
  1. INPUT: validate untrusted JSON and turn it into clean Python values.
  2. OUTPUT: turn model instances into JSON-ready dicts.
"""
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from accounts.models import User


class UserSerializer(serializers.ModelSerializer):
    """Full read-only representation of a user (used in responses)."""

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "role", "is_active", "date_joined"]
        read_only_fields = fields


class UserSummarySerializer(serializers.ModelSerializer):
    """Small nested representation (no email) embedded in tickets and comments."""

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "role"]
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = ["username", "email", "password", "first_name", "last_name"]
        # `role` is deliberately absent: anyone registering becomes a customer. Mass-assignment protection.

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate(self, attrs):
        # Build a throwaway user so similarity-to-username/email checks can run.
        candidate = User(username=attrs.get("username", ""), email=attrs.get("email", ""))
        try:
            password_validation.validate_password(attrs["password"], candidate)
        except DjangoValidationError as exc:  # translate Django's exception into DRF's
            raise serializers.ValidationError({"password": list(getattr(exc, "messages", [str(exc)]))})
        return attrs

    def create(self, validated_data):
        # create_user hashes the password (PBKDF2 by default). Never assign `password=` directly.
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})


class ProfileSerializer(serializers.ModelSerializer):
    """What a user may change about themselves. Role and username are read-only."""

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "role", "date_joined"]
        read_only_fields = ["id", "username", "role", "date_joined"]

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_password(self, value):
        try:
            password_validation.validate_password(value, self.context["request"].user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    """Admin-only: change a user's role or deactivate the account."""

    class Meta:
        model = User
        fields = ["role", "is_active"]

    def validate(self, attrs):
        request_user = self.context["request"].user
        if self.instance.pk == request_user.pk:
            if "role" in attrs and attrs["role"] != request_user.role:
                raise serializers.ValidationError({"role": "You cannot change your own role."})
            if attrs.get("is_active") is False:
                raise serializers.ValidationError({"is_active": "You cannot deactivate your own account."})
        return attrs
