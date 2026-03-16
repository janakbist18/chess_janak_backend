"""
User preferences and settings models (theme, sound, etc.)
"""
from django.conf import settings
from django.db import models
from apps.core.models import TimeStampedModel


class UserPreferences(TimeStampedModel):
    """User preferences like theme, sound, notifications"""
    
    THEME_LIGHT = "light"
    THEME_DARK = "dark"
    THEME_AUTO = "auto"
    
    THEME_CHOICES = [
        (THEME_LIGHT, "Light"),
        (THEME_DARK, "Dark"),
        (THEME_AUTO, "Auto"),
    ]
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="preferences",
    )
    theme = models.CharField(
        max_length=20,
        choices=THEME_CHOICES,
        default=THEME_AUTO,
    )
    sound_enabled = models.BooleanField(default=True)
    move_sound = models.BooleanField(default=True)
    capture_sound = models.BooleanField(default=True)
    check_sound = models.BooleanField(default=True)
    victory_sound = models.BooleanField(default=True)
    defeat_sound = models.BooleanField(default=True)
    
    notifications_enabled = models.BooleanField(default=True)
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)
    
    # Game preferences
    show_coordinates = models.BooleanField(default=True)
    show_legal_moves = models.BooleanField(default=True)
    show_last_move = models.BooleanField(default=True)
    
    # Privacy
    show_online_status = models.BooleanField(default=True)
    allow_friend_requests = models.BooleanField(default=True)
    
    language = models.CharField(max_length=20, default="en")
    
    class Meta:
        verbose_name = "User Preferences"
        verbose_name_plural = "User Preferences"
    
    def __str__(self):
        return f"Preferences - {self.user.username}"


class SoundSettings(TimeStampedModel):
    """Custom sound settings for chess pieces and moves"""
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sound_settings",
    )
    move_sound_url = models.URLField(null=True, blank=True)
    capture_sound_url = models.URLField(null=True, blank=True)
    check_sound_url = models.URLField(null=True, blank=True)
    victory_sound_url = models.URLField(null=True, blank=True)
    defeat_sound_url = models.URLField(null=True, blank=True)
    
    sound_volume = models.IntegerField(default=100)  # 0-100
    
    class Meta:
        verbose_name = "Sound Settings"
        verbose_name_plural = "Sound Settings"
    
    def __str__(self):
        return f"Sound Settings - {self.user.username}"
