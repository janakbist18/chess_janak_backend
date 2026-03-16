from django.urls import path
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.rooms.views import (
    CreateRoomView,
    InviteLookupView,
    JoinRoomView,
    MyRoomsView,
    RoomDetailView,
)


class RoomsIndexView(APIView):
    """Index view for rooms endpoints"""
    def get(self, request):
        return Response({
            "message": "Rooms API",
            "endpoints": {
                "create": "POST /api/rooms/create/",
                "join": "POST /api/rooms/join/",
                "my_rooms": "GET /api/rooms/mine/",
                "invite_lookup": "GET /api/rooms/invite/{invite_code}/",
                "room_detail": "GET /api/rooms/{room_id}/",
            }
        })


urlpatterns = [
    path("", RoomsIndexView.as_view(), name="rooms-index"),
    path("create/", CreateRoomView.as_view(), name="create-room"),
    path("join/", JoinRoomView.as_view(), name="join-room"),
    path("mine/", MyRoomsView.as_view(), name="my-rooms"),
    path("invite/<str:invite_code>/", InviteLookupView.as_view(), name="invite-lookup"),
    path("<uuid:room_id>/", RoomDetailView.as_view(), name="room-detail"),
]