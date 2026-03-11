from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chessplay.selectors import get_match_by_room_id
from apps.chessplay.serializers import ChessMatchSerializer, ChessMoveSerializer
from apps.chessplay.services.match_service import get_or_create_match_for_room
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