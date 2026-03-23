from apps.rooms.routing import websocket_urlpatterns as room_websocket_urlpatterns
from apps.chat.routing import websocket_urlpatterns as chat_websocket_urlpatterns

websocket_urlpatterns = [
    *room_websocket_urlpatterns,
    *chat_websocket_urlpatterns,
]