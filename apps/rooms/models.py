import uuid

from django.conf import settings
from django.db import models

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

    ROOM_TYPE_CHOICES = [
        (ROOM_TYPE_PRIVATE, "Private"),
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
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

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

    class Meta:
        ordering = ["joined_at"]
        unique_together = ("room", "user")

    def __str__(self) -> str:
        return f"{self.room.room_code} - {self.user.username} - {self.side}"