"""
WebSocket URL routing for chat application.
"""
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(
        r'ws/chat/(?P<conversation_id>[a-f0-9\-]+)/$',
        consumers.ChatConsumer.as_asgi(),
        name='ws-chat'
    ),
]
