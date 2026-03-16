"""
Models for game invitations and video/audio calls
"""
import secrets
from django.conf import settings
from django.db import models
from django.utils import timezone
from apps.core.models import TimeStampedModel


class GameInvitation(TimeStampedModel):
    """Game invitations with unique join codes"""
    
    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_DECLINED = "declined"
    STATUS_EXPIRED = "expired"
    
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_DECLINED, "Declined"),
        (STATUS_EXPIRED, "Expired"),
    ]
    
    TIME_CONTROL_RAPID = "rapid"  # 10-60 minutes
    TIME_CONTROL_BLITZ = "blitz"  # 3-8 minutes
    TIME_CONTROL_BULLET = "bullet"  # 1-2 minutes
    TIME_CONTROL_CLASSICAL = "classical"  # 8 hours+
    
    TIME_CONTROL_CHOICES = [
        (TIME_CONTROL_RAPID, "Rapid"),
        (TIME_CONTROL_BLITZ, "Blitz"),
        (TIME_CONTROL_BULLET, "Bullet"),
        (TIME_CONTROL_CLASSICAL, "Classical"),
    ]
    
    inviter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_invitations",
    )
    invitee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_invitations",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    
    # Game settings
    time_control = models.CharField(
        max_length=20,
        choices=TIME_CONTROL_CHOICES,
        default=TIME_CONTROL_BLITZ,
    )
    initial_time_minutes = models.PositiveIntegerField(default=5)  # in minutes
    increment_seconds = models.PositiveIntegerField(default=3)  # increment per move
    
    # Invitation details
    join_code = models.CharField(
        max_length=10,
        unique=True,
        editable=False,
        db_index=True,
    )
    message = models.TextField(blank=True, default="")
    expires_at = models.DateTimeField()
    
    # Game room reference
    game_room = models.ForeignKey(
        'rooms.GameRoom',
        on_delete=models.SET_NULL,
        related_name="invitations",
        null=True,
        blank=True,
    )
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "invitee"]),
            models.Index(fields=["join_code"]),
        ]
    
    def save(self, *args, **kwargs):
        if not self.join_code:
            self.join_code = self.generate_join_code()
        if not self.expires_at:
            from datetime import timedelta
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_join_code():
        """Generate unique 8-character join code"""
        while True:
            code = secrets.token_urlsafe(6)[:8]
            if not GameInvitation.objects.filter(join_code=code).exists():
                return code
    
    def __str__(self):
        return f"Invite {self.inviter.username} -> {self.invitee.username}"


class VideoCallSession(TimeStampedModel):
    """Video/Audio call sessions with WebRTC setup"""
    
    STATUS_INITIALIZING = "initializing"
    STATUS_ACTIVE = "active"
    STATUS_ENDED = "ended"
    STATUS_FAILED = "failed"
    
    STATUS_CHOICES = [
        (STATUS_INITIALIZING, "Initializing"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_ENDED, "Ended"),
        (STATUS_FAILED, "Failed"),
    ]
    
    initiator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="video_calls_initiated",
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="video_calls_received",
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_INITIALIZING,
    )
    
    # WebRTC details
    session_id = models.CharField(max_length=100, unique=True, db_index=True)
    offer_sdp = models.TextField(blank=True)  # Session Description Protocol
    answer_sdp = models.TextField(blank=True)
    
    # Call settings
    audio_enabled = models.BooleanField(default=True)
    video_enabled = models.BooleanField(default=True)
    
    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    
    # Game reference
    game_match = models.ForeignKey(
        'chessplay.ChessMatch',
        on_delete=models.SET_NULL,
        related_name="video_calls",
        null=True,
        blank=True,
    )
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["session_id"]),
        ]
    
    def __str__(self):
        return f"Call: {self.initiator.username} <-> {self.receiver.username}"


class ICECandidate(TimeStampedModel):
    """WebRTC ICE candidates for establishing peer connections"""
    
    call_session = models.ForeignKey(
        VideoCallSession,
        on_delete=models.CASCADE,
        related_name="ice_candidates",
    )
    
    # Candidate info
    candidate = models.TextField()
    sdp_mline_index = models.IntegerField()
    sdp_mid = models.CharField(max_length=100, blank=True)
    
    # Who sent the candidate
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ice_candidates_sent",
    )
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ice_candidates_received",
    )
    
    class Meta:
        ordering = ["created_at"]
    
    def __str__(self):
        return f"ICE: {self.call_session.id}"
