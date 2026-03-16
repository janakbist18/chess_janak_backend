from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def api_root(request):
    return JsonResponse(
        {
            "project": "chess_janak_backend",
            "status": "running",
            "admin_url": "/admin/",
            "auth_base_url": "/api/auth/",
            "rooms_base_url": "/api/rooms/",
            "chess_base_url": "/api/chess/",
            "chat_base_url": "/api/chat/",
            "calls_base_url": "/api/calls/",
        }
    )


urlpatterns = [
    path("", api_root, name="api-root"),
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/rooms/", include("apps.rooms.urls")),
    path("api/chess/", include("apps.chessplay.urls")),
    path("api/chat/", include("apps.chat.urls")),
    path("api/calls/", include("apps.calls.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)