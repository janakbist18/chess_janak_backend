from apps.rooms.routing import websocket_urlpatterns as room_websocket_urlpatterns

websocket_urlpatterns = [
    *room_websocket_urlpatterns,
]