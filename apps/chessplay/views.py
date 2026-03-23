from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
import chess

from apps.chessplay.selectors import get_match_by_room_id
from apps.chessplay.serializers import ChessMatchSerializer, ChessMoveSerializer
from apps.chessplay.services.match_service import get_or_create_match_for_room
from apps.chessplay.services.chess_engine_service import apply_move, ChessMoveError
from apps.rooms.models import GameRoom


class RoomMatchDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, room_id):
        room = GameRoom.objects.filter(id=room_id).first()
        if not room:
            return Response(
                {"message": "Room not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if request.user.id not in [room.host_id, room.player_white_id, room.player_black_id]:
            return Response(
                {"message": "Access denied."},
                status=status.HTTP_403_FORBIDDEN,
            )

        match = get_or_create_match_for_room(room)
        serializer = ChessMatchSerializer(match, context={"request": request})
        return Response({"match": serializer.data}, status=status.HTTP_200_OK)


class RoomMoveHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, room_id):
        room = GameRoom.objects.filter(id=room_id).first()
        if not room:
            return Response(
                {"message": "Room not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if request.user.id not in [room.host_id, room.player_white_id, room.player_black_id]:
            return Response(
                {"message": "Access denied."},
                status=status.HTTP_403_FORBIDDEN,
            )

        match = get_match_by_room_id(room_id)
        if not match:
            return Response(
                {"moves": []},
                status=status.HTTP_200_OK,
            )

        serializer = ChessMoveSerializer(match.moves.order_by("move_number"), many=True, context={"request": request})
        return Response({"moves": serializer.data}, status=status.HTTP_200_OK)


class RoomMakeMoveView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, room_id):
        room = GameRoom.objects.filter(id=room_id).first()
        if not room:
            return Response(
                {"detail": "Room not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if request.user.id not in [room.host_id, room.player_white_id, room.player_black_id]:
            return Response(
                {"detail": "Access denied."},
                status=status.HTTP_403_FORBIDDEN,
            )

        from_square = request.data.get("from_square")
        to_square = request.data.get("to_square")
        promotion = request.data.get("promotion")

        if not from_square or not to_square:
            return Response(
                {"detail": "from_square and to_square are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = apply_move(room, request.user, from_square, to_square, promotion)
            return Response(result, status=status.HTTP_200_OK)
        except ChessMoveError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class BoardVisualizationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, room_id):
        """Get board visualization in ASCII format and JSON"""
        room = GameRoom.objects.filter(id=room_id).first()
        if not room:
            return Response(
                {"detail": "Room not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if request.user.id not in [room.host_id, room.player_white_id, room.player_black_id]:
            return Response(
                {"detail": "Access denied."},
                status=status.HTTP_403_FORBIDDEN,
            )

        match = get_or_create_match_for_room(room)
        board = chess.Board(match.current_fen)

        # ASCII representation
        ascii_board = str(board)

        # Board position as dictionary
        board_dict = {}
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece:
                square_name = chess.square_name(square)
                board_dict[square_name] = {
                    "symbol": piece.symbol(),
                    "name": piece.name,
                    "color": "white" if piece.color == chess.WHITE else "black",
                }

        # Legal moves
        legal_moves = [move.uci() for move in board.legal_moves]

        return Response(
            {
                "board_ascii": ascii_board,
                "board_position": board_dict,
                "current_fen": match.current_fen,
                "legal_moves": legal_moves,
                "is_check": board.is_check(),
                "is_checkmate": board.is_checkmate(),
                "is_stalemate": board.is_stalemate(),
                "is_game_over": board.is_game_over(),
                "current_turn": "white" if board.turn == chess.WHITE else "black",
                "halfmove_clock": board.halfmove_clock,
                "fullmove_number": board.fullmove_number,
                "match": ChessMatchSerializer(match, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )