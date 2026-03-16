"""
Chess game URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.chessplay.views_game import ChessGameViewSet

router = DefaultRouter()
router.register(r'games', ChessGameViewSet, basename='chess_game')

urlpatterns = [
    path('', include(router.urls)),
]
