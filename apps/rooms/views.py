from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.rooms.models import GameRoom
from apps.rooms.selectors import get_room_by_invite_code, get_room_for_user, get_user_rooms
from apps.rooms.serializers import CreateRoomSerializer, GameRoomSerializer, JoinRoomSerializer
from apps.rooms.services.room_service import create_room_for_user, join_room_for_user


class CreateRoomView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CreateRoomSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        room = create_room_for_user(request.user)

        return Response(
            {
                "message": "Room created successfully.",
                "room": GameRoomSerializer(room, context={"request": request}).data,
            },
            status=status.HTTP_201_CREATED,
        )


class JoinRoomView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = JoinRoomSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        invite_code = serializer.validated_data.get("invite_code")
        room_id = serializer.validated_data.get("room_id")

        room = None
        if invite_code:
            room = get_room_by_invite_code(invite_code)
        elif room_id:
            room = GameRoom.objects.filter(id=room_id, is_active=True).first()

        if not room:
            return Response(
                {"message": "Room not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            room, participant, created = join_room_for_user(room, request.user)
        except ValueError as exc:
            return Response(
                {"message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "message": "Room joined successfully." if created else "Already joined this room.",
                "room": GameRoomSerializer(room, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )


class RoomDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, room_id):
        room = get_room_for_user(room_id, request.user)
        if not room:
            return Response(
                {"message": "Room not found or access denied."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "room": GameRoomSerializer(room, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )


class MyRoomsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        rooms = get_user_rooms(request.user)
        serializer = GameRoomSerializer(rooms, many=True, context={"request": request})
        return Response(
            {
                "count": len(serializer.data),
                "rooms": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class InviteLookupView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, invite_code):
        room = get_room_by_invite_code(invite_code)
        if not room:
            return Response(
                {"message": "Room not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "room": GameRoomSerializer(room, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )