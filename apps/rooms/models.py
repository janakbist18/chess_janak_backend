import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


class GameRoom(TimeStampedModel):
    STATUS_WAITING = "waiting"
    STATUS_READY = "ready"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_FINISHED = "finished"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_WAITING, "Waiting"),
        (STATUS_READY, "Ready"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_FINISHED, "Finished"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    ROOM_TYPE_PRIVATE = "private"
    ROOM_TYPE_PUBLIC = "public"

    ROOM_TYPE_CHOICES = [
        (ROOM_TYPE_PRIVATE, "Private"),
        (ROOM_TYPE_PUBLIC, "Public"),
    ]

    TIME_CONTROL_BULLET = "bullet"  # <3 minutes
    TIME_CONTROL_BLITZ = "blitz"    # 3-10 minutes
    TIME_CONTROL_RAPID = "rapid"    # 10-60 minutes
    TIME_CONTROL_CLASSICAL = "classical"  # 60+ minutes

    TIME_CONTROL_CHOICES = [
        (TIME_CONTROL_BULLET, "Bullet"),
        (TIME_CONTROL_BLITZ, "Blitz"),
        (TIME_CONTROL_RAPID, "Rapid"),
        (TIME_CONTROL_CLASSICAL, "Classical"),
    ]

    GAME_TYPE_CASUAL = "casual"
    GAME_TYPE_RATED = "rated"

    GAME_TYPE_CHOICES = [
        (GAME_TYPE_CASUAL, "Casual"),
        (GAME_TYPE_RATED, "Rated"),
    ]

    SIDE_WHITE = "white"
    SIDE_BLACK = "black"

    SIDE_CHOICES = [
        (SIDE_WHITE, "White"),
        (SIDE_BLACK, "Black"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room_code = models.CharField(max_length=12, unique=True, db_index=True)
    invite_code = models.CharField(max_length=12, unique=True, db_index=True)
    room_type = models.CharField(
        max_length=20,
        choices=ROOM_TYPE_CHOICES,
        default=ROOM_TYPE_PRIVATE,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_WAITING,
    )
    time_control = models.CharField(
        max_length=20,
        choices=TIME_CONTROL_CHOICES,
        default=TIME_CONTROL_BLITZ,
    )
    game_type = models.CharField(
        max_length=20,
        choices=GAME_TYPE_CHOICES,
        default=GAME_TYPE_CASUAL,
    )
    time_per_side_minutes = models.IntegerField(default=5, help_text="Initial time in minutes")
    increment_seconds = models.IntegerField(default=0, help_text="Increment in seconds per move")
    host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="hosted_rooms",
    )
    player_white = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="white_rooms",
        null=True,
        blank=True,
    )
    player_black = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="black_rooms",
        null=True,
        blank=True,
    )
    winner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="won_rooms",
        null=True,
        blank=True,
    )
    current_turn = models.CharField(
        max_length=10,
        choices=SIDE_CHOICES,
        default=SIDE_WHITE,
    )
    fen = models.TextField(
        default="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    )
    pgn = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    is_public_listed = models.BooleanField(default=True, help_text="Whether room appears in public room list")
    max_spectators = models.IntegerField(default=10, help_text="Maximum allowed spectators")
    allow_spectators = models.BooleanField(default=True, help_text="Whether spectators can join")
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    min_rating = models.IntegerField(null=True, blank=True, help_text="Minimum rating to join (if set)")
    max_rating = models.IntegerField(null=True, blank=True, help_text="Maximum rating to join (if set)")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['room_type', 'status']),
            models.Index(fields=['room_type', 'is_public_listed', 'status']),
            models.Index(fields=['host', 'status']),
            models.Index(fields=['player_white', 'status']),
            models.Index(fields=['player_black', 'status']),
        ]

    def __str__(self) -> str:
        return f"{self.room_code} - {self.status}"

    @property
    def is_full(self) -> bool:
        return bool(self.player_white and self.player_black)

    @property
    def player_count(self) -> int:
        count = 0
        if self.player_white:
            count += 1
        if self.player_black:
            count += 1
        return count

    @property
    def invite_link(self) -> str:
        return f"/join/{self.invite_code}"

    @property
    def spectator_count(self) -> int:
        return self.participants.filter(side=RoomParticipant.SIDE_SPECTATOR).count()

    def can_spectate(self) -> bool:
        """Check if spectators can join this room."""
        if not self.allow_spectators:
            return False
        return self.spectator_count < self.max_spectators

    def can_join(self, user) -> bool:
        """Check if a user can join this room."""
        if self.status in [self.STATUS_FINISHED, self.STATUS_CANCELLED]:
            return False
        if self.player_white == user or self.player_black == user:
            return True
        if self.is_full and not self.can_spectate():
            return False
        if self.min_rating and hasattr(user, 'profile') and user.profile.rating < self.min_rating:
            return False
        if self.max_rating and hasattr(user, 'profile') and user.profile.rating > self.max_rating:
            return False
        return True


class RoomSettings(TimeStampedModel):
    """Advanced configuration settings for game rooms."""
    
    # Game variations
    STARTING_POSITION_STANDARD = "standard"
    STARTING_POSITION_CHESS960 = "chess960"
    STARTING_POSITIONS = [
        (STARTING_POSITION_STANDARD, "Standard Chess"),
        (STARTING_POSITION_CHESS960, "Chess960 (Fischer Random)"),
    ]
    
    # Draw/Resign settings
    RESIGN_RULES_STANDARD = "standard"
    RESIGN_RULES_NO_RESIGN = "no_resign"
    RESIGN_RULES_CHOICES = [
        (RESIGN_RULES_STANDARD, "Standard (Allow)"),
        (RESIGN_RULES_NO_RESIGN, "No Resign"),
    ]
    
    room = models.OneToOneField(GameRoom, on_delete=models.CASCADE, related_name="settings")
    
    # Game variations
    starting_position = models.CharField(
        max_length=20,
        choices=STARTING_POSITIONS,
        default=STARTING_POSITION_STANDARD,
        help_text="Chess variation to play"
    )
    
    # House rules
    resign_allowed = models.BooleanField(
        default=True,
        help_text="Whether players can resign"
    )
    draw_offer_allowed = models.BooleanField(
        default=True,
        help_text="Whether players can offer draws"
    )
    accept_draw_by_agreement = models.BooleanField(
        default=True,
        help_text="Whether draws can be accepted by both players"
    )
    accept_draw_by_repetition = models.BooleanField(
        default=True,
        help_text="Automatic draw by threefold repetition"
    )
    accept_draw_by_fifty_move = models.BooleanField(
        default=True,
        help_text="Automatic draw by 50-move rule"
    )
    
    # Advanced settings
    require_rated_profile = models.BooleanField(
        default=False,
        help_text="Require players to have a rated profile"
    )
    
    handicap_enabled = models.BooleanField(
        default=False,
        help_text="Enable handicap games (e.g., material odds)"
    )
    
    class Meta:
        verbose_name = "Room Settings"
        verbose_name_plural = "Room Settings"
    
    def __str__(self) -> str:
        return f"Settings for {self.room.room_code}"


class MatchmakingQueue(TimeStampedModel):
    """Tracks players waiting for automatic matches in public rooms."""
    
    STATUS_WAITING = "waiting"
    STATUS_MATCHED = "matched"
    STATUS_CANCELLED = "cancelled"
    
    STATUS_CHOICES = [
        (STATUS_WAITING, "Waiting for match"),
        (STATUS_MATCHED, "Match found"),
        (STATUS_CANCELLED, "Cancelled"),
    ]
    
    # Skill tiers for matching (ELO ranges)
    TIER_BEGINNER = "beginner"  # < 1000
    TIER_INTERMEDIATE = "intermediate"  # 1000-1400
    TIER_ADVANCED = "advanced"  # 1400-1800
    TIER_EXPERT = "expert"  # 1800-2200
    TIER_MASTER = "master"  # > 2200
    
    SKILL_TIER_CHOICES = [
        (TIER_BEGINNER, "Beginner (< 1000)"),
        (TIER_INTERMEDIATE, "Intermediate (1000-1400)"),
        (TIER_ADVANCED, "Advanced (1400-1800)"),
        (TIER_EXPERT, "Expert (1800-2200)"),
        (TIER_MASTER, "Master (> 2200)"),
    ]
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="matchmaking_queue"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_WAITING
    )
    
    # Requested game preferences
    time_control = models.CharField(
        max_length=20,
        choices=GameRoom.TIME_CONTROL_CHOICES,
        default=GameRoom.TIME_CONTROL_BLITZ,
        help_text="Requested time control"
    )
    game_type = models.CharField(
        max_length=20,
        choices=GameRoom.GAME_TYPE_CHOICES,
        default=GameRoom.GAME_TYPE_CASUAL,
        help_text="Casual or rated game"
    )
    
    # Skill tier at time of queueing
    skill_tier = models.CharField(
        max_length=20,
        choices=SKILL_TIER_CHOICES,
        help_text="Player's skill tier when joining queue"
    )
    rating_at_queue_time = models.IntegerField(
        help_text="Player's ELO rating when joining queue"
    )
    
    # Match result
    matched_room = models.ForeignKey(
        GameRoom,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="queued_participants"
    )
    matched_with_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="matched_opponents"
    )
    
    # Timestamps
    queue_duration = models.DurationField(
        null=True,
        blank=True,
        help_text="Time spent in queue before match"
    )
    
    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=['status', 'time_control', 'skill_tier']),
            models.Index(fields=['user', 'status']),
        ]
        verbose_name = "Matchmaking Queue Entry"
        verbose_name_plural = "Matchmaking Queue Entries"
    
    def __str__(self) -> str:
        return f"{self.user.username} - {self.status} ({self.time_control})"
    
    @staticmethod
    def get_skill_tier(rating: int) -> str:
        """Determine skill tier from ELO rating."""
        if rating < 1000:
            return MatchmakingQueue.TIER_BEGINNER
        elif rating < 1400:
            return MatchmakingQueue.TIER_INTERMEDIATE
        elif rating < 1800:
            return MatchmakingQueue.TIER_ADVANCED
        elif rating < 2200:
            return MatchmakingQueue.TIER_EXPERT
        else:
            return MatchmakingQueue.TIER_MASTER
    
    @property
    def wait_time(self):
        """Get current wait time in queue."""
        if self.status == self.STATUS_MATCHED and self.queue_duration:
            return self.queue_duration
        elif self.status == self.STATUS_WAITING:
            from django.utils import timezone
            return timezone.now() - self.created_at
        return None


class RoomParticipant(TimeStampedModel):
    ROLE_HOST = "host"
    ROLE_PLAYER = "player"

    ROLE_CHOICES = [
        (ROLE_HOST, "Host"),
        (ROLE_PLAYER, "Player"),
    ]

    PRESENCE_WAITING = "waiting"
    PRESENCE_JOINED = "joined"
    PRESENCE_LEFT = "left"

    PRESENCE_CHOICES = [
        (PRESENCE_WAITING, "Waiting"),
        (PRESENCE_JOINED, "Joined"),
        (PRESENCE_LEFT, "Left"),
    ]

    SIDE_WHITE = "white"
    SIDE_BLACK = "black"
    SIDE_SPECTATOR = "spectator"

    SIDE_CHOICES = [
        (SIDE_WHITE, "White"),
        (SIDE_BLACK, "Black"),
        (SIDE_SPECTATOR, "Spectator"),
    ]

    room = models.ForeignKey(
        GameRoom,
        on_delete=models.CASCADE,
        related_name="participants",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="room_participations",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_PLAYER)
    side = models.CharField(max_length=20, choices=SIDE_CHOICES, default=SIDE_SPECTATOR)
    presence_status = models.CharField(
        max_length=20,
        choices=PRESENCE_CHOICES,
        default=PRESENCE_JOINED,
    )
    is_ready = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    last_ping_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["joined_at"]
        unique_together = ("room", "user")

    def __str__(self) -> str:
        return f"{self.room.room_code} - {self.user.username} - {self.side}"

    def mark_joined(self):
        self.presence_status = self.PRESENCE_JOINED
        self.left_at = None
        self.last_ping_at = timezone.now()
        self.save(update_fields=["presence_status", "left_at", "last_ping_at", "updated_at"])

    def mark_left(self):
        self.presence_status = self.PRESENCE_LEFT
        self.left_at = timezone.now()
        self.save(update_fields=["presence_status", "left_at", "updated_at"])

    def mark_ping(self):
        self.last_ping_at = timezone.now()
        if self.presence_status != self.PRESENCE_JOINED:
            self.presence_status = self.PRESENCE_JOINED
            self.save(update_fields=["last_ping_at", "presence_status", "updated_at"])
        else:
            self.save(update_fields=["last_ping_at", "updated_at"])