from channels.routing import URLRouter
from rtc.routing import websocket_urlpatterns

websocket_urlpatterns = URLRouter(websocket_urlpatterns)