from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.accounts.models import User, UserProfile
from apps.accounts.services.auth_service import generate_tokens_for_user
from apps.accounts.services.google_auth_service import handle_google_login
from apps.accounts.services.otp_service import (
    create_email_verification_otp,
    create_password_reset_otp,
    get_valid_email_otp,
    get_valid_password_reset_otp,
)
from apps.accounts.utils import get_user_by_email_or_username
from apps.accounts.validators import (
    validate_new_passwords,
    validate_password_confirmation,
)


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = (
            "bio",
            "country",
            "games_played",
            "wins",
            "losses",
            "draws",
            "rating",
        )


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    profile_image_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "name",
            "profile_image",
            "profile_image_url",
            "is_verified",
            "is_google_account",
            "online_status",
            "last_seen",
            "profile",
            "date_joined",
        )

    def get_profile_image_url(self, obj):
        request = self.context.get("request")
        if obj.profile_image and request:
            return request.build_absolute_uri(obj.profile_image.url)
        if obj.profile_image:
            return obj.profile_image.url
        return None


class RegisterSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    username = serializers.CharField(max_length=30)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value.lower()

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def validate(self, attrs):
        try:
            validate_password_confirmation(attrs["password"], attrs["confirm_password"])
        except Exception as exc:
            raise serializers.ValidationError({"confirm_password": [str(exc)]})

        validate_password(attrs["password"])
        return attrs

    def create(self, validated_data):
        validated_data.pop("confirm_password")

        user = User.objects.create_user(
            email=validated_data["email"],
            username=validated_data["username"],
            name=validated_data["name"],
            password=validated_data["password"],
            is_active=False,
            is_verified=False,
        )

        create_email_verification_otp(user, purpose="registration")
        return user


class VerifyRegistrationOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp_code = serializers.CharField(max_length=6)

    def validate(self, attrs):
        email = attrs["email"].lower()
        otp_code = attrs["otp_code"]

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            raise serializers.ValidationError({"email": ["User not found."]})

        otp = get_valid_email_otp(user, otp_code, purpose="registration")
        if not otp:
            raise serializers.ValidationError({"otp_code": ["Invalid or expired OTP."]})

        attrs["user"] = user
        attrs["otp"] = otp
        return attrs

    def save(self, **kwargs):
        user = self.validated_data["user"]
        otp = self.validated_data["otp"]

        otp.mark_used()
        user.is_verified = True
        user.is_active = True
        user.save(update_fields=["is_verified", "is_active"])

        tokens = generate_tokens_for_user(user)
        return {
            "user": user,
            "tokens": tokens,
        }


class ResendRegistrationOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate(self, attrs):
        email = attrs["email"].lower()
        user = User.objects.filter(email__iexact=email).first()

        if not user:
            raise serializers.ValidationError({"email": ["User not found."]})

        if user.is_verified:
            raise serializers.ValidationError(
                {"email": ["This account is already verified."]}
            )

        attrs["user"] = user
        return attrs

    def save(self, **kwargs):
        user = self.validated_data["user"]
        create_email_verification_otp(user, purpose="registration")
        return user


class LoginSerializer(serializers.Serializer):
    email_or_username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email_or_username = attrs["email_or_username"]
        password = attrs["password"]

        user = get_user_by_email_or_username(email_or_username)
        if not user:
            raise serializers.ValidationError(
                {"email_or_username": ["Invalid credentials."]}
            )

        if not user.check_password(password):
            raise serializers.ValidationError({"password": ["Invalid credentials."]})

        if not user.is_verified and not user.is_google_account:
            raise serializers.ValidationError(
                {"account": ["Account is not verified. Please verify OTP first."]}
            )

        if not user.is_active:
            raise serializers.ValidationError(
                {"account": ["This account is inactive."]}
            )

        attrs["user"] = user
        return attrs


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate(self, attrs):
        email = attrs["email"].lower()
        user = User.objects.filter(email__iexact=email).first()

        if not user:
            raise serializers.ValidationError({"email": ["User not found."]})

        attrs["user"] = user
        return attrs

    def save(self, **kwargs):
        user = self.validated_data["user"]
        create_password_reset_otp(user)
        return user


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp_code = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        email = attrs["email"].lower()
        otp_code = attrs["otp_code"]
        new_password = attrs["new_password"]
        confirm_password = attrs["confirm_password"]

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            raise serializers.ValidationError({"email": ["User not found."]})

        otp = get_valid_password_reset_otp(user, otp_code)
        if not otp:
            raise serializers.ValidationError({"otp_code": ["Invalid or expired OTP."]})

        try:
            validate_new_passwords(new_password, confirm_password)
        except Exception as exc:
            raise serializers.ValidationError({"confirm_password": [str(exc)]})

        validate_password(new_password, user=user)

        attrs["user"] = user
        attrs["otp"] = otp
        return attrs

    def save(self, **kwargs):
        user = self.validated_data["user"]
        otp = self.validated_data["otp"]
        new_password = self.validated_data["new_password"]

        user.set_password(new_password)
        user.save(update_fields=[])

        otp.mark_used()
        return user


class GoogleSignInSerializer(serializers.Serializer):
    id_token = serializers.CharField()

    def validate(self, attrs):
        id_token_value = attrs["id_token"]

        try:
            result = handle_google_login(id_token_value)
        except Exception as exc:
            raise serializers.ValidationError({"google": [str(exc)]})

        attrs["result"] = result
        return attrs

    def save(self, **kwargs):
        return self.validated_data["result"]