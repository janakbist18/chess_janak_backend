from django.db import models
from django.conf import settings
from django.utils import timezone


class RewardAd(models.Model):
    """Reward Ad that users can watch to earn rewards"""

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('paused', 'Paused'),
    ]

    AD_TYPE_CHOICES = [
        ('video', 'Video'),
        ('banner', 'Banner'),
        ('interstitial', 'Interstitial'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    ad_type = models.CharField(max_length=20, choices=AD_TYPE_CHOICES, default='video')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    # Reward details
    reward_coins = models.IntegerField(default=10)  # In-game currency
    reward_points = models.IntegerField(default=5)  # Experience points

    # Ad details
    duration_seconds = models.IntegerField(default=30)  # Video duration
    impressions_limit = models.IntegerField(null=True, blank=True)  # Max impressions
    daily_limit_per_user = models.IntegerField(default=3)  # Max views per user per day

    # URLs
    ad_url = models.URLField(help_text="URL to the ad video or landing page")
    thumbnail_url = models.URLField(blank=True, help_text="Thumbnail image URL")

    # Tracking
    total_impressions = models.IntegerField(default=0)
    total_completions = models.IntegerField(default=0)
    total_clicks = models.IntegerField(default=0)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Reward Ad"
        verbose_name_plural = "Reward Ads"

    def __str__(self):
        return f"{self.title} - {self.ad_type.upper()}"

    @property
    def is_available(self):
        """Check if ad is available for users"""
        if self.status != 'active':
            return False

        now = timezone.now()
        if self.starts_at and now < self.starts_at:
            return False
        if self.ends_at and now > self.ends_at:
            return False
        if self.impressions_limit and self.total_impressions >= self.impressions_limit:
            return False

        return True


class UserAdReward(models.Model):
    """Track user's ad watching and reward history"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ad_rewards"
    )
    ad = models.ForeignKey(
        RewardAd,
        on_delete=models.CASCADE,
        related_name="user_rewards"
    )

    viewed_at = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Rewards earned
    coins_earned = models.IntegerField(default=0)
    points_earned = models.IntegerField(default=0)

    # Click tracking
    clicked = models.BooleanField(default=False)
    clicked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-viewed_at']
        verbose_name = "User Ad Reward"
        verbose_name_plural = "User Ad Rewards"
        unique_together = ('user', 'ad', 'viewed_at')

    def __str__(self):
        return f"{self.user.email} - {self.ad.title}"

    def mark_completed(self):
        """Mark ad as completed and award rewards"""
        if not self.completed:
            self.completed = True
            self.completed_at = timezone.now()
            self.coins_earned = self.ad.reward_coins
            self.points_earned = self.ad.reward_points
            self.save()

            # Update ad tracking
            self.ad.total_completions += 1
            self.ad.save()

            return {
                'coins': self.coins_earned,
                'points': self.points_earned,
            }
        return None

    def mark_clicked(self):
        """Mark ad as clicked"""
        if not self.clicked:
            self.clicked = True
            self.clicked_at = timezone.now()
            self.save()

            # Update ad tracking
            self.ad.total_clicks += 1
            self.ad.save()


class AdViewerSession(models.Model):
    """Track active ad viewing sessions"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ad_sessions"
    )
    ad = models.ForeignKey(
        RewardAd,
        on_delete=models.CASCADE,
        related_name="sessions"
    )

    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    watch_duration_seconds = models.IntegerField(default=0)

    skipped = models.BooleanField(default=False)
    skipped_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']
        verbose_name = "Ad Viewer Session"
        verbose_name_plural = "Ad Viewer Sessions"

    def __str__(self):
        return f"{self.user.email} watching {self.ad.title}"

    def mark_ended(self, watch_duration_seconds=None):
        """End the viewing session"""
        self.ended_at = timezone.now()
        if watch_duration_seconds:
            self.watch_duration_seconds = watch_duration_seconds
        self.save()

    def mark_skipped(self):
        """Mark ad as skipped"""
        self.skipped = True
        self.skipped_at = timezone.now()
        self.ended_at = timezone.now()
        self.save()
