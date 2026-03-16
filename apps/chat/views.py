from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from apps.chat.models import Conversation, Message
from apps.chat.serializers import (
    ConversationListSerializer,
    ConversationDetailSerializer,
    MessageSerializer,
)


class ConversationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing conversations"""

    permission_classes = [IsAuthenticated]
    serializer_class = ConversationListSerializer
    queryset = Conversation.objects.all()

    def get_queryset(self):
        """Return conversations for the current user"""
        return Conversation.objects.filter(
            participants=self.request.user
        ).prefetch_related('participants', 'messages')

    def get_serializer_class(self):
        """Use different serializer for detail view"""
        if self.action == 'retrieve':
            return ConversationDetailSerializer
        return ConversationListSerializer

    @action(detail=False, methods=['post'])
    def create_with_user(self, request):
        """Create or get conversation with a specific user"""
        other_user_id = request.data.get('other_user_id')

        if not other_user_id:
            return Response(
                {'error': 'other_user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Find or create conversation
        conversation = Conversation.objects.filter(
            participants=request.user
        ).filter(
            participants__id=other_user_id
        ).distinct().first()

        if not conversation:
            conversation = Conversation.objects.create()
            conversation.participants.add(request.user)
            conversation.participants.add(other_user_id)

        serializer = ConversationDetailSerializer(conversation)
        return Response(serializer.data)


class MessageViewSet(viewsets.ModelViewSet):
    """ViewSet for managing messages"""

    permission_classes = [IsAuthenticated]
    serializer_class = MessageSerializer
    queryset = Message.objects.all()

    def get_queryset(self):
        """Return messages for conversations the user is in"""
        return Message.objects.filter(
            conversation__participants=self.request.user
        )

    def perform_create(self, serializer):
        """Create message with current user as sender"""
        serializer.save(sender=self.request.user)

    @action(detail=False, methods=['post'])
    def mark_as_read(self, request):
        """Mark messages as read"""
        conversation_id = request.data.get('conversation_id')

        if not conversation_id:
            return Response(
                {'error': 'conversation_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        messages = Message.objects.filter(
            conversation_id=conversation_id,
            is_read=False
        ).exclude(sender=request.user)

        count = 0
        for message in messages:
            message.mark_as_read()
            count += 1

        return Response(
            {'marked_as_read': count},
            status=status.HTTP_200_OK
        )
