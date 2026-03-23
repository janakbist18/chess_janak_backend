from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import (
    ChatConversation, ChatMessage, MessageReadStatus,
    BlockedUser, TypingIndicator
)
from .serializers import (
    ChatConversationListSerializer, ChatConversationDetailSerializer,
    ChatMessageSerializer, CreateChatMessageSerializer,
    MessageReadStatusSerializer, BlockedUserSerializer,
    TypingIndicatorSerializer
)
from .services.message_service import ChatMessageService
from apps.core.permissions import IsOwnerOrReadOnly


class MessagePagination(PageNumberPagination):
    """Custom pagination for messages."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ChatConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for chat conversations.

    Supports:
    - List all conversations
    - Create direct message conversations
    - Retrieve conversation details
    - Mark messages as read
    - Get conversation members
    """
    serializer_class = ChatConversationListSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['participant1__first_name', 'participant2__first_name', 'room__room_name']
    ordering_fields = ['last_message_at', 'created_at']
    ordering = ['-last_message_at']

    def get_queryset(self):
        """Get conversations for the current user."""
        return ChatConversation.objects.filter(
            Q(participant1=self.request.user) |
            Q(participant2=self.request.user) |
            Q(members=self.request.user)
        ).distinct().prefetch_related(
            'participant1', 'participant2', 'members', 'messages'
        )

    def get_serializer_class(self):
        """Use detail serializer for retrieve action."""
        if self.action == 'retrieve':
            return ChatConversationDetailSerializer
        return ChatConversationListSerializer

    def create(self, request, *args, **kwargs):
        """Create a direct message conversation."""
        other_user_id = request.data.get('other_user_id')
        if not other_user_id:
            return Response(
                {'error': 'other_user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        conversation = ChatMessageService.get_or_create_direct_conversation(
            request.user, other_user_id
        )

        serializer = self.get_serializer(conversation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark all messages in conversation as read."""
        conversation = self.get_object()
        ChatMessageService.mark_messages_as_read(conversation, request.user)
        return Response({'status': 'messages marked as read'})

    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """Get all members of a conversation."""
        conversation = self.get_object()
        participants = conversation.get_participants()
        from apps.accounts.serializers import UserBasicSerializer
        serializer = UserBasicSerializer(participants, many=True)
        return Response(serializer.data)


class ChatMessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for chat messages.

    Supports:
    - List messages in a conversation (paginated)
    - Create new messages
    - Update own messages
    - Delete own messages
    - Mark message as read
    - Search messages
    """
    serializer_class = ChatMessageSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = MessagePagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['content']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """Get messages accessible to the current user."""
        conversation_id = self.request.query_params.get('conversation_id')
        queryset = ChatMessage.objects.all()

        if conversation_id:
            queryset = queryset.filter(conversation_id=conversation_id)

        # Only show messages from conversations the user is part of
        queryset = queryset.filter(
            conversation__in=ChatConversation.objects.filter(
                Q(participant1=self.request.user) |
                Q(participant2=self.request.user) |
                Q(members=self.request.user)
            )
        ).prefetch_related('sender', 'read_statuses')

        return queryset

    def get_serializer_class(self):
        """Use create serializer for create action."""
        if self.action == 'create':
            return CreateChatMessageSerializer
        return ChatMessageSerializer

    def create(self, request, *args, **kwargs):
        """Create a new message."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.save()

        # Mark message as read for sender
        ChatMessageService.mark_message_as_read(message, request.user)

        # Update conversation's last_message_at
        message.conversation.last_message_at = timezone.now()
        message.conversation.save()

        output_serializer = ChatMessageSerializer(
            message, context={'request': request}
        )
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark a specific message as read."""
        message = self.get_object()
        ChatMessageService.mark_message_as_read(message, request.user)
        return Response({'status': 'message marked as read'})

    @action(detail=True, methods=['post'])
    def edit(self, request, pk=None):
        """Edit a message."""
        message = self.get_object()

        if message.sender != request.user:
            return Response(
                {'error': 'You can only edit your own messages'},
                status=status.HTTP_403_FORBIDDEN
            )

        message.content = request.data.get('content', message.content)
        message.mark_as_edited()

        serializer = self.get_serializer(message)
        return Response(serializer.data)

    @action(detail=True, methods=['delete'])
    def soft_delete(self, request, pk=None):
        """Soft delete a message (mark as system message)."""
        message = self.get_object()

        if message.sender != request.user:
            return Response(
                {'error': 'You can only delete your own messages'},
                status=status.HTTP_403_FORBIDDEN
            )

        message.content = '[Message deleted]'
        message.message_type = 'system'
        message.save()

        return Response({'status': 'message deleted'})


class BlockedUserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing blocked users.

    Supports:
    - List blocked users
    - Block a user
    - Unblock a user
    """
    serializer_class = BlockedUserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get users blocked by the current user."""
        return BlockedUser.objects.filter(blocker=self.request.user)

    def create(self, request, *args, **kwargs):
        """Block a user."""
        blocked_user_id = request.data.get('blocked_user')

        if not blocked_user_id:
            return Response(
                {'error': 'blocked_user is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if str(blocked_user_id) == str(request.user.id):
            return Response(
                {'error': 'You cannot block yourself'},
                status=status.HTTP_400_BAD_REQUEST
            )

        obj, created = BlockedUser.objects.get_or_create(
            blocker=request.user,
            blocked_user_id=blocked_user_id
        )

        serializer = self.get_serializer(obj)
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(serializer.data, status=status_code)

    @action(detail=True, methods=['delete'])
    def unblock(self, request, pk=None):
        """Unblock a user."""
        blocked = self.get_object()
        blocked.delete()
        return Response({'status': 'user unblocked'}, status=status.HTTP_204_NO_CONTENT)


class TypingIndicatorViewSet(viewsets.ModelViewSet):
    """
    ViewSet for typing indicators.

    Supports:
    - Create/update typing indicator
    - List typing users in a conversation
    - Delete typing indicator
    """
    serializer_class = TypingIndicatorSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get typing indicators for conversations the user is part of."""
        return TypingIndicator.objects.filter(
            conversation__in=ChatConversation.objects.filter(
                Q(participant1=self.request.user) |
                Q(participant2=self.request.user) |
                Q(members=self.request.user)
            )
        ).prefetch_related('user')

    def create(self, request, *args, **kwargs):
        """Create or update typing indicator."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        typing_indicator = serializer.save()
        return Response(ChatMessageService.format_typing_indicator(typing_indicator))

    @action(detail=False, methods=['get'])
    def by_conversation(self, request):
        """Get typing indicators for a specific conversation."""
        conversation_id = request.query_params.get('conversation_id')
        if not conversation_id:
            return Response(
                {'error': 'conversation_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        typing_indicators = self.get_queryset().filter(
            conversation_id=conversation_id
        ).exclude(user=request.user)

        serializer = self.get_serializer(typing_indicators, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def stop_typing(self, request):
        """Delete typing indicator for a conversation."""
        conversation_id = request.data.get('conversation_id')
        if not conversation_id:
            return Response(
                {'error': 'conversation_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        TypingIndicator.objects.filter(
            conversation_id=conversation_id,
            user=request.user
        ).delete()

        return Response({'status': 'typing indicator removed'})


class MessageReadStatusViewSet(viewsets.ModelViewSet):
    """ViewSet for message read statuses."""
    serializer_class = MessageReadStatusSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get read statuses for messages in user's conversations."""
        return MessageReadStatus.objects.filter(
            message__conversation__in=ChatConversation.objects.filter(
                Q(participant1=self.request.user) |
                Q(participant2=self.request.user) |
                Q(members=self.request.user)
            )
        )

    @action(detail=False, methods=['get'])
    def by_message(self, request):
        """Get all read receipts for a specific message."""
        message_id = request.query_params.get('message_id')
        if not message_id:
            return Response(
                {'error': 'message_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        read_statuses = self.get_queryset().filter(message_id=message_id)
        serializer = self.get_serializer(read_statuses, many=True)
        return Response(serializer.data)
