from django.urls import path, include
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.chessplay.views import GamesListView, RoomMatchDetailView, RoomMoveHistoryView


class ChessIndexView(APIView):
    """Index view for chess endpoints"""
    def get(self, request):
        return Response({
            "message": "Chess API",
            "endpoints": {
                "games": "GET /api/chess/games/",
                "room_match": "GET /api/chess/room/{room_id}/",
                "room_moves": "GET /api/chess/room/{room_id}/moves/",
                "reward_ads": "GET /api/chess/ads/",
                "my_ad_rewards": "GET /api/chess/my-rewards/",
            }
        })


urlpatterns = [
    path("", ChessIndexView.as_view(), name="chess-index"),
    path("games/", GamesListView.as_view(), name="games-list"),
    path("room/<uuid:room_id>/", RoomMatchDetailView.as_view(), name="room-match-detail"),
    path("room/<uuid:room_id>/moves/", RoomMoveHistoryView.as_view(), name="room-move-history"),
    path("", include("apps.chessplay.urls_ads")),
]