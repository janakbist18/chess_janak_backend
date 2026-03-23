from django.urls import path

from apps.chessplay.views import (
    RoomMatchDetailView,
    RoomMoveHistoryView,
    RoomMakeMoveView,
    BoardVisualizationView,
)

urlpatterns = [
    # Match details
    path("room/<uuid:room_id>/", RoomMatchDetailView.as_view(), name="room-match-detail"),
    path("room/<uuid:room_id>/moves/", RoomMoveHistoryView.as_view(), name="room-move-history"),
    path("room/<uuid:room_id>/board/", BoardVisualizationView.as_view(), name="board-visualization"),

    # Game moves
    path("room/<uuid:room_id>/move/", RoomMakeMoveView.as_view(), name="make-move"),
]