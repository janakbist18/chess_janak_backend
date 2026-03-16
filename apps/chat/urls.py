from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.chat.views import ConversationViewSet, MessageViewSet

router = DefaultRouter()
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'messages', MessageViewSet, basename='message')


class ChatIndexView(APIView):
    """Index view for chat endpoints"""
    def get(self, request):
        return Response({
            "message": "Chat API",
            "endpoints": {
                "conversations": "GET /api/chat/conversations/",
                "conversations_create": "POST /api/chat/conversations/",
                "conversations_detail": "GET /api/chat/conversations/{id}/",
                "conversations_with_user": "POST /api/chat/conversations/create_with_user/",
                "messages": "GET /api/chat/messages/",
                "messages_create": "POST /api/chat/messages/",
                "messages_mark_read": "POST /api/chat/messages/mark_as_read/",
            }
        })


urlpatterns = [
    path('', ChatIndexView.as_view(), name='chat-index'),
] + router.urls
