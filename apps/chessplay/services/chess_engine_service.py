from django.db import transaction
from django.utils import timezone
import chess
import chess.pgn

from apps.chessplay.models import ChessMatch, ChessMove
from apps.chessplay.services.match_service import get_or_create_match_for_room
from apps.rooms.models import GameRoom


class ChessMoveError(Exception):
    pass


def get_user_side(room: GameRoom, user) -> str | None:
    if room.player_white_id == user.id:
        return "white"
    if room.player_black_id == user.id:
        return "black"
    return None


def build_match_snapshot(match: ChessMatch) -> dict:
    return {
        "id": match.id,
        "room_id": str(match.room_id),
        "status": match.status,
        "result": match.result,
        "result_type": match.result_type,
        "current_fen": match.current_fen,
        "pgn": match.pgn,
        "halfmove_clock": match.halfmove_clock,
        "fullmove_number": match.fullmove_number,
        "is_check": match.is_check,
        "is_checkmate": match.is_checkmate,
        "is_stalemate": match.is_stalemate,
        "winner_id": match.winner_id,
        "draw_offered_by_id": match.draw_offered_by_id,
        "started_at": match.started_at.isoformat() if match.started_at else None,
        "ended_at": match.ended_at.isoformat() if match.ended_at else None,
    }


def build_move_snapshot(move: ChessMove) -> dict:
    return {
        "id": move.id,
        "move_number": move.move_number,
        "player_id": move.player_id,
        "side": move.side,
        "from_square": move.from_square,
        "to_square": move.to_square,
        "uci": move.uci,
        "san": move.san,
        "promotion_piece": move.promotion_piece,
        "fen_after": move.fen_after,
        "is_capture": move.is_capture,
        "is_check": move.is_check,
        "is_checkmate": move.is_checkmate,
        "created_at": move.created_at.isoformat() if move.created_at else None,
    }


@transaction.atomic
def apply_move(room: GameRoom, user, from_square: str, to_square: str, promotion: str | None = None) -> dict:
    room = GameRoom.objects.select_for_update().select_related(
        "player_white",
        "player_black",
        "host",
    ).get(id=room.id)

    if room.status in [GameRoom.STATUS_FINISHED, GameRoom.STATUS_CANCELLED]:
        raise ChessMoveError("This game is already finished.")

    if not room.player_white or not room.player_black:
        raise ChessMoveError("Both players must join before moves can be made.")

    user_side = get_user_side(room, user)
    if not user_side:
        raise ChessMoveError("You are not a player in this room.")

    if room.current_turn != user_side:
        raise ChessMoveError("It is not your turn.")

    match = get_or_create_match_for_room(room)

    if match.status == ChessMatch.STATUS_FINISHED:
        raise ChessMoveError("This match is already finished.")

    board = chess.Board(match.current_fen)

    promotion_suffix = ""
    if promotion:
        promotion_suffix = promotion.lower()

    uci = f"{from_square}{to_square}{promotion_suffix}"
    try:
        move = chess.Move.from_uci(uci)
    except ValueError:
        raise ChessMoveError("Invalid move format.")

    if move not in board.legal_moves:
        raise ChessMoveError("Illegal move.")

    is_capture = board.is_capture(move)
    san = board.san(move)

    board.push(move)

    move_count = match.moves.count() + 1

    move_obj = ChessMove.objects.create(
        match=match,
        move_number=move_count,
        player=user,
        side=user_side,
        from_square=from_square,
        to_square=to_square,
        uci=uci,
        san=san,
        promotion_piece=promotion_suffix,
        fen_after=board.fen(),
        is_capture=is_capture,
        is_check=board.is_check(),
        is_checkmate=board.is_checkmate(),
    )

    game = chess.pgn.Game()
    replay_board = chess.Board()
    node = game

    for existing_move in match.moves.order_by("move_number"):
        replay_move = chess.Move.from_uci(existing_move.uci)
        node = node.add_variation(replay_move)
        replay_board.push(replay_move)

    exporter = chess.pgn.StringExporter(headers=False, variations=False, comments=False)
    pgn_text = game.accept(exporter).strip()

    match.current_fen = board.fen()
    match.pgn = pgn_text
    match.halfmove_clock = board.halfmove_clock
    match.fullmove_number = board.fullmove_number
    match.is_check = board.is_check()
    match.is_checkmate = board.is_checkmate()
    match.is_stalemate = board.is_stalemate()
    match.draw_offered_by = None

    room.fen = match.current_fen
    room.pgn = match.pgn

    if board.turn == chess.WHITE:
        room.current_turn = GameRoom.SIDE_WHITE
    else:
        room.current_turn = GameRoom.SIDE_BLACK

    if board.is_checkmate():
        match.status = ChessMatch.STATUS_FINISHED
        match.result_type = ChessMatch.RESULT_CHECKMATE
        match.ended_at = timezone.now()
        room.status = GameRoom.STATUS_FINISHED
        room.finished_at = timezone.now()

        winner = room.player_white if user_side == "white" else room.player_black
        match.winner = winner
        room.winner = winner

        if user_side == "white":
            match.result = ChessMatch.RESULT_WHITE_WIN
        else:
            match.result = ChessMatch.RESULT_BLACK_WIN

    elif board.is_stalemate():
        match.status = ChessMatch.STATUS_FINISHED
        match.result = ChessMatch.RESULT_DRAW
        match.result_type = ChessMatch.RESULT_STALEMATE
        match.ended_at = timezone.now()
        room.status = GameRoom.STATUS_FINISHED
        room.finished_at = timezone.now()
        match.winner = None
        room.winner = None

    elif board.is_insufficient_material():
        match.status = ChessMatch.STATUS_FINISHED
        match.result = ChessMatch.RESULT_DRAW
        match.result_type = ChessMatch.RESULT_INSUFFICIENT_MATERIAL
        match.ended_at = timezone.now()
        room.status = GameRoom.STATUS_FINISHED
        room.finished_at = timezone.now()
        match.winner = None
        room.winner = None

    elif board.can_claim_fifty_moves():
        match.status = ChessMatch.STATUS_FINISHED
        match.result = ChessMatch.RESULT_DRAW
        match.result_type = ChessMatch.RESULT_FIFTY_MOVE
        match.ended_at = timezone.now()
        room.status = GameRoom.STATUS_FINISHED
        room.finished_at = timezone.now()
        match.winner = None
        room.winner = None

    elif board.can_claim_threefold_repetition():
        match.status = ChessMatch.STATUS_FINISHED
        match.result = ChessMatch.RESULT_DRAW
        match.result_type = ChessMatch.RESULT_THREEFOLD
        match.ended_at = timezone.now()
        room.status = GameRoom.STATUS_FINISHED
        room.finished_at = timezone.now()
        match.winner = None
        room.winner = None

    else:
        if match.status == ChessMatch.STATUS_WAITING:
            match.status = ChessMatch.STATUS_IN_PROGRESS
            if not match.started_at:
                match.started_at = timezone.now()

        if room.status in [GameRoom.STATUS_WAITING, GameRoom.STATUS_READY]:
            room.status = GameRoom.STATUS_IN_PROGRESS
            if not room.started_at:
                room.started_at = timezone.now()

    match.save()
    room.save()

    return {
        "move": build_move_snapshot(move_obj),
        "match": build_match_snapshot(match),
        "room_status": room.status,
        "room_current_turn": room.current_turn,
        "room_fen": room.fen,
        "room_pgn": room.pgn,
        "winner_id": room.winner_id,
    }


@transaction.atomic
def resign_match(room: GameRoom, user) -> dict:
    room = GameRoom.objects.select_for_update().select_related(
        "player_white",
        "player_black",
    ).get(id=room.id)
    match = get_or_create_match_for_room(room)

    if match.status == ChessMatch.STATUS_FINISHED:
        raise ChessMoveError("Match already finished.")

    user_side = get_user_side(room, user)
    if not user_side:
        raise ChessMoveError("You are not a player in this room.")

    winner = room.player_black if user_side == "white" else room.player_white

    match.status = ChessMatch.STATUS_FINISHED
    match.result_type = ChessMatch.RESULT_RESIGNATION
    match.ended_at = timezone.now()
    match.winner = winner
    match.draw_offered_by = None

    if user_side == "white":
        match.result = ChessMatch.RESULT_BLACK_WIN
    else:
        match.result = ChessMatch.RESULT_WHITE_WIN

    room.status = GameRoom.STATUS_FINISHED
    room.finished_at = timezone.now()
    room.winner = winner

    match.save()
    room.save()

    return {
        "match": build_match_snapshot(match),
        "winner_id": winner.id if winner else None,
        "room_status": room.status,
    }


@transaction.atomic
def offer_draw(room: GameRoom, user) -> dict:
    room = GameRoom.objects.select_for_update().select_related(
        "player_white",
        "player_black",
    ).get(id=room.id)
    match = get_or_create_match_for_room(room)

    if match.status == ChessMatch.STATUS_FINISHED:
        raise ChessMoveError("Match already finished.")

    user_side = get_user_side(room, user)
    if not user_side:
        raise ChessMoveError("You are not a player in this room.")

    opponent_id = room.player_black_id if user_side == "white" else room.player_white_id
    if not opponent_id:
        raise ChessMoveError("Opponent has not joined yet.")

    match.draw_offered_by = user
    match.save(update_fields=["draw_offered_by", "updated_at"])

    return {
        "match": build_match_snapshot(match),
        "offered_by_id": user.id,
    }


@transaction.atomic
def respond_draw(room: GameRoom, user, accepted: bool) -> dict:
    room = GameRoom.objects.select_for_update().select_related(
        "player_white",
        "player_black",
    ).get(id=room.id)
    match = get_or_create_match_for_room(room)

    if match.status == ChessMatch.STATUS_FINISHED:
        raise ChessMoveError("Match already finished.")

    user_side = get_user_side(room, user)
    if not user_side:
        raise ChessMoveError("You are not a player in this room.")

    if not match.draw_offered_by_id:
        raise ChessMoveError("There is no active draw offer.")

    if match.draw_offered_by_id == user.id:
        raise ChessMoveError("You cannot respond to your own draw offer.")

    if accepted:
        match.status = ChessMatch.STATUS_FINISHED
        match.result = ChessMatch.RESULT_DRAW
        match.result_type = ChessMatch.RESULT_DRAW_AGREED
        match.ended_at = timezone.now()
        match.winner = None
        room.status = GameRoom.STATUS_FINISHED
        room.finished_at = timezone.now()
        room.winner = None

    match.draw_offered_by = None
    match.save()
    room.save()

    return {
        "accepted": accepted,
        "match": build_match_snapshot(match),
        "room_status": room.status,
    }