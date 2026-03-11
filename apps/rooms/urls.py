from django.urls import path

from apps.rooms.views import (
    CreateRoomView,
    InviteLookupView,
    JoinRoomView,
    MyRoomsView,
    RoomDetailView,
)

urlpatterns = [
    path("create/", CreateRoomView.as_view(), name="create-room"),
    path("join/", JoinRoomView.as_view(), name="join-room"),
    path("mine/", MyRoomsView.as_view(), name="my-rooms"),
    path("invite/<str:invite_code>/", InviteLookupView.as_view(), name="invite-lookup"),
    path("<uuid:room_id>/", RoomDetailView.as_view(), name="room-detail"),
]