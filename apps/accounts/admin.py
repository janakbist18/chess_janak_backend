from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.accounts.models import EmailOTP, PasswordResetOTP, User, UserProfile


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = (
        "id",
        "email",
        "username",
        "name",
        "is_verified",
        "is_google_account",
        "online_status",
        "is_active",
        "is_staff",
        "date_joined",
    )
    list_filter = (
        "is_verified",
        "is_google_account",
        "online_status",
        "is_active",
        "is_staff",
        "is_superuser",
    )
    search_fields = ("email", "username", "name")
    ordering = ("-date_joined",)

    fieldsets = (
        (None, {"fields": ("email", "username", "password")}),
        (
            "Personal Info",
            {"fields": ("name", "profile_image", "online_status", "last_seen")},
        ),
        (
            "Verification",
            {"fields": ("is_verified", "is_google_account")},
        ),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        (
            "Important Dates",
            {"fields": ("last_login", "date_joined")},
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "username", "name", "password1", "password2", "is_staff", "is_superuser"),
            },
        ),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "games_played",
        "wins",
        "losses",
        "draws",
        "rating",
        "created_at",
    )
    search_fields = ("user__email", "user__username", "user__name")


@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "email",
        "otp_code",
        "purpose",
        "expires_at",
        "is_used",
        "created_at",
    )
    list_filter = ("purpose", "is_used")
    search_fields = ("email", "user__email", "user__username", "otp_code")


@admin.register(PasswordResetOTP)
class PasswordResetOTPAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "email",
        "otp_code",
        "expires_at",
        "is_used",
        "created_at",
    )
    list_filter = ("is_used",)
    search_fields = ("email", "user__email", "user__username", "otp_code")