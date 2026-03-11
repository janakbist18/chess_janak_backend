from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel
from apps.rooms.models import GameRoom


class ChessMatch(TimeStampedModel):
    STATUS_WAITING = "waiting"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_FINISHED = "finished"

    STATUS_CHOICES = [
        (STATUS_WAITING, "Waiting"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_FINISHED, "Finished"),
    ]

    RESULT_CHECKMATE = "checkmate"
    RESULT_STALEMATE = "stalemate"
    RESULT_RESIGNATION = "resignation"
    RESULT_DRAW_AGREED = "draw_agreed"
    RESULT_INSUFFICIENT_MATERIAL = "insufficient_material"
    RESULT_FIFTY_MOVE = "fifty_move_rule"
    RESULT_THREEFOLD = "threefold_repetition"

    RESULT_TYPE_CHOICES = [
        (RESULT_CHECKMATE, "Checkmate"),
        (RESULT_STALEMATE, "Stalemate"),
        (RESULT_RESIGNATION, "Resignation"),
        (RESULT_DRAW_AGREED, "Draw Agreed"),
        (RESULT_INSUFFICIENT_MATERIAL, "Insufficient Material"),
        (RESULT_FIFTY_MOVE, "Fifty Move Rule"),
        (RESULT_THREEFOLD, "Threefold Repetition"),
    ]

    RESULT_WHITE_WIN = "1-0"
    RESULT_BLACK_WIN = "0-1"
    RESULT_DRAW = "1/2-1/2"
    RESULT_PENDING = "*"

    RESULT_CHOICES = [
        (RESULT_WHITE_WIN, "White Win"),
        (RESULT_BLACK_WIN, "Black Win"),
        (RESULT_DRAW, "Draw"),
        (RESULT_PENDING, "Pending"),
    ]

    room = models.OneToOneField(
        GameRoom,
        on_delete=models.CASCADE,
        related_name="match",
    )
    white_player = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="matches_as_white",
        null=True,
        blank=True,
    )
    black_player = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="matches_as_black",
        null=True,
        blank=True,
    )
    winner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="matches_won",
        null=True,
        blank=True,
    )
    draw_offered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="draw_offers_made",
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_WAITING,
    )
    result = models.CharField(
        max_length=10,
        choices=RESULT_CHOICES,
        default=RESULT_PENDING,
    )
    result_type = models.CharField(
        max_length=30,
        choices=RESULT_TYPE_CHOICES,
        null=True,
        blank=True,
    )
    initial_fen = models.TextField(
        default="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    )
    current_fen = models.TextField(
        default="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    )
    pgn = models.TextField(blank=True, default="")
    halfmove_clock = models.PositiveIntegerField(default=0)
    fullmove_number = models.PositiveIntegerField(default=1)
    is_check = models.BooleanField(default=False)
    is_checkmate = models.BooleanField(default=False)
    is_stalemate = models.BooleanField(default=False)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Match #{self.id} - {self.room.room_code}"


class ChessMove(TimeStampedModel):
    SIDE_WHITE = "white"
    SIDE_BLACK = "black"

    SIDE_CHOICES = [
        (SIDE_WHITE, "White"),
        (SIDE_BLACK, "Black"),
    ]

    match = models.ForeignKey(
        ChessMatch,
        on_delete=models.CASCADE,
        related_name="moves",
    )
    move_number = models.PositiveIntegerField()
    player = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="chess_moves",
        null=True,
        blank=True,
    )
    side = models.CharField(max_length=10, choices=SIDE_CHOICES)
    from_square = models.CharField(max_length=2)
    to_square = models.CharField(max_length=2)
    uci = models.CharField(max_length=10)
    san = models.CharField(max_length=20)
    promotion_piece = models.CharField(max_length=10, blank=True, default="")
    fen_after = models.TextField()
    is_capture = models.BooleanField(default=False)
    is_check = models.BooleanField(default=False)
    is_checkmate = models.BooleanField(default=False)

    class Meta:
        ordering = ["move_number", "created_at"]
        unique_together = ("match", "move_number")

    def __str__(self) -> str:
        return f"Match {self.match_id} Move {self.move_number} {self.uci}"