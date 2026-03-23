from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'chat'

router = DefaultRouter()
router.register(r'conversations', views.ChatConversationViewSet, basename='conversation')
router.register(r'messages', views.ChatMessageViewSet, basename='message')
router.register(r'blocked-users', views.BlockedUserViewSet, basename='blocked-user')
router.register(r'typing-indicators', views.TypingIndicatorViewSet, basename='typing-indicator')
router.register(r'read-statuses', views.MessageReadStatusViewSet, basename='read-status')

urlpatterns = [
    path('', include(router.urls)),
]
