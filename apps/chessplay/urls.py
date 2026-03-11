from django.urls import path

from apps.chessplay.views import RoomMatchDetailView, RoomMoveHistoryView

urlpatterns = [
    path("room/<uuid:room_id>/", RoomMatchDetailView.as_view(), name="room-match-detail"),
    path("room/<uuid:room_id>/moves/", RoomMoveHistoryView.as_view(), name="room-move-history"),
]