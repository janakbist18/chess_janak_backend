"""
Invitation and Video Call URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.rooms.views_invitations import GameInvitationViewSet, VideoCallViewSet

router = DefaultRouter()
router.register(r'invitations', GameInvitationViewSet, basename='invitation')
router.register(r'calls', VideoCallViewSet, basename='video_call')

urlpatterns = [
    path('', include(router.urls)),
]
