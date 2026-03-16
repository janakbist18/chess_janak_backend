from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.accounts.managers import UserManager
from apps.core.constants import USER_STATUS_CHOICES, USER_STATUS_OFFLINE
from apps.core.models import TimeStampedModel
from apps.core.validators import validate_username_format


class User(AbstractUser):
    first_name = None
    last_name = None

    email = models.EmailField(unique=True)
    username = models.CharField(
        max_length=30,
        unique=True,
        validators=[validate_username_format],
    )
    name = models.CharField(max_length=150)
    profile_image = models.ImageField(
        upload_to="profiles/",
        null=True,
        blank=True,
    )
    google_picture_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
    )
    is_verified = models.BooleanField(default=False)
    is_google_account = models.BooleanField(default=False)
    online_status = models.CharField(
        max_length=20,
        choices=USER_STATUS_CHOICES,
        default=USER_STATUS_OFFLINE,
    )
    last_seen = models.DateTimeField(null=True, blank=True)

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "name"]

    objects = UserManager()

    class Meta:
        ordering = ["-date_joined"]

    def __str__(self) -> str:
        return f"{self.username} ({self.email})"


class UserProfile(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    bio = models.TextField(blank=True, default="")
    country = models.CharField(max_length=120, blank=True, default="")
    games_played = models.PositiveIntegerField(default=0)
    wins = models.PositiveIntegerField(default=0)
    losses = models.PositiveIntegerField(default=0)
    draws = models.PositiveIntegerField(default=0)
    rating = models.PositiveIntegerField(
        default=1200,
        validators=[MinValueValidator(100)],
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Profile - {self.user.username}"


class EmailOTP(TimeStampedModel):
    PURPOSE_REGISTRATION = "registration"
    PURPOSE_LOGIN = "login"
    PURPOSE_EMAIL_VERIFY = "email_verify"

    PURPOSE_CHOICES = [
        (PURPOSE_REGISTRATION, "Registration"),
        (PURPOSE_LOGIN, "Login"),
        (PURPOSE_EMAIL_VERIFY, "Email Verify"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_otps",
    )
    email = models.EmailField()
    otp_code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=30, choices=PURPOSE_CHOICES)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email", "purpose"]),
            models.Index(fields=["otp_code"]),
        ]

    def __str__(self) -> str:
        return f"{self.email} - {self.purpose} - {self.otp_code}"

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    def mark_used(self) -> None:
        self.is_used = True
        self.save(update_fields=["is_used"])


class PasswordResetOTP(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_reset_otps",
    )
    email = models.EmailField()
    otp_code = models.CharField(max_length=6)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["otp_code"]),
        ]

    def __str__(self) -> str:
        return f"PasswordResetOTP - {self.email} - {self.otp_code}"

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    def mark_used(self) -> None:
        self.is_used = True
        self.save(update_fields=["is_used"])