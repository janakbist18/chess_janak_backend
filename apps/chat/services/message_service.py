"""
Chat message service - business logic for chat operations.
"""
from django.db.models import Q
from django.contrib.auth import get_user_model
from apps.chat.models import (
    ChatConversation, ChatMessage, MessageReadStatus,
    BlockedUser, TypingIndicator
)

User = get_user_model()


class ChatMessageService:
    """Service class for chat message operations."""

    @staticmethod
    def get_or_create_direct_conversation(user1, user2_id):
        """
        Get or create a direct message conversation between two users.

        Args:
            user1: The requesting user
            user2_id: ID of the other user

        Returns:
            ChatConversation instance
        """
        try:
            user2 = User.objects.get(id=user2_id)
        except User.DoesNotExist:
            raise ValueError(f"User with id {user2_id} not found")

        # Check if users have blocked each other
        if BlockedUser.objects.filter(
            Q(blocker=user1, blocked_user=user2) |
            Q(blocker=user2, blocked_user=user1)
        ).exists():
            raise ValueError("Cannot create conversation with blocked user")

        # Order users to ensure consistent conversation lookup
        if user1.id < user2.id:
            participant1, participant2 = user1, user2
        else:
            participant1, participant2 = user2, user1

        conversation, created = ChatConversation.objects.get_or_create(
            conversation_type='direct',
            participant1=participant1,
            participant2=participant2
        )

        return conversation

    @staticmethod
    def send_message(conversation, sender, message_type, content='', media_file=None, reply_to=None):
        """
        Send a message in a conversation.

        Args:
            conversation: ChatConversation instance
            sender: User sending the message
            message_type: Type of message ('text', 'image', 'file', 'system')
            content: Message text content
            media_file: Optional file upload
            reply_to: Optional message being replied to

        Returns:
            ChatMessage instance
        """
        if not content and not media_file:
            raise ValueError("Message must have content or media file")

        # Check if sender is blocked
        if BlockedUser.objects.filter(
            blocker__in=conversation.get_participants(),
            blocked_user=sender
        ).exists():
            raise ValueError("You are blocked from sending messages in this conversation")

        message = ChatMessage.objects.create(
            conversation=conversation,
            sender=sender,
            message_type=message_type,
            content=content,
            media_file=media_file,
            reply_to=reply_to
        )

        # Update conversation's last message time
        from django.utils import timezone
        conversation.last_message_at = timezone.now()
        conversation.save(update_fields=['last_message_at', 'updated_at'])

        return message

    @staticmethod
    def mark_message_as_read(message, reader):
        """
        Mark a message as read by a user.

        Args:
            message: ChatMessage instance
            reader: User reading the message
        """
        if message.sender == reader:
            return  # Don't mark own messages as read

        MessageReadStatus.objects.get_or_create(
            message=message,
            reader=reader
        )

    @staticmethod
    def mark_messages_as_read(conversation, reader):
        """
        Mark all unread messages in a conversation as read.

        Args:
            conversation: ChatConversation instance
            reader: User reading the messages
        """
        unread_messages = conversation.messages.exclude(
            read_statuses__reader=reader
        ).exclude(
            sender=reader
        )

        read_statuses = [
            MessageReadStatus(message=msg, reader=reader)
            for msg in unread_messages
        ]

        MessageReadStatus.objects.bulk_create(
            read_statuses,
            ignore_conflicts=True
        )

    @staticmethod
    def block_user(blocker, blocked_user_id):
        """
        Block a user from sending messages.

        Args:
            blocker: User doing the blocking
            blocked_user_id: ID of user to block

        Returns:
            BlockedUser instance
        """
        try:
            blocked_user = User.objects.get(id=blocked_user_id)
        except User.DoesNotExist:
            raise ValueError(f"User with id {blocked_user_id} not found")

        if blocker == blocked_user:
            raise ValueError("You cannot block yourself")

        blocked, created = BlockedUser.objects.get_or_create(
            blocker=blocker,
            blocked_user=blocked_user
        )

        return blocked

    @staticmethod
    def unblock_user(blocker, blocked_user_id):
        """
        Unblock a previously blocked user.

        Args:
            blocker: User doing the unblocking
            blocked_user_id: ID of user to unblock
        """
        try:
            blocked = BlockedUser.objects.get(
                blocker=blocker,
                blocked_user_id=blocked_user_id
            )
            blocked.delete()
            return True
        except BlockedUser.DoesNotExist:
            return False

    @staticmethod
    def get_user_blocked_ids(user):
        """
        Get list of user IDs that are blocked by the given user.

        Args:
            user: User instance

        Returns:
            List of blocked user IDs
        """
        return list(
            BlockedUser.objects.filter(blocker=user).values_list(
                'blocked_user_id', flat=True
            )
        )

    @staticmethod
    def get_conversation_blockers(conversation):
        """
        Get list of users who have blocked anyone in the conversation.

        Args:
            conversation: ChatConversation instance

        Returns:
            Dictionary of blocked users by blocker
        """
        participants = conversation.get_participants()
        blocked_map = {}

        for participant in participants:
            blocked_map[participant.id] = ChatMessageService.get_user_blocked_ids(
                participant
            )

        return blocked_map

    @staticmethod
    def start_typing(conversation, user):
        """
        Update or create a typing indicator.

        Args:
            conversation: ChatConversation instance
            user: User who is typing

        Returns:
            TypingIndicator instance
        """
        from django.utils import timezone
        typing_indicator, created = TypingIndicator.objects.update_or_create(
            conversation=conversation,
            user=user,
            defaults={'updated_at': timezone.now()}
        )
        return typing_indicator

    @staticmethod
    def stop_typing(conversation, user):
        """
        Remove typing indicator for a user.

        Args:
            conversation: ChatConversation instance
            user: User who stopped typing
        """
        TypingIndicator.objects.filter(
            conversation=conversation,
            user=user
        ).delete()

    @staticmethod
    def get_typing_users(conversation, exclude_user=None):
        """
        Get list of users currently typing in a conversation.

        Args:
            conversation: ChatConversation instance
            exclude_user: Optional user to exclude

        Returns:
            QuerySet of TypingIndicator instances
        """
        typing_indicators = TypingIndicator.objects.filter(
            conversation=conversation
        ).select_related('user')

        if exclude_user:
            typing_indicators = typing_indicators.exclude(user=exclude_user)

        return typing_indicators

    @staticmethod
    def cleanup_stale_typing_indicators(minutes=2):
        """
        Remove typing indicators older than specified minutes.
        Useful for cleaning up stale indicators from disconnected users.

        Args:
            minutes: How many minutes old to consider stale

        Returns:
            Number of deleted indicators
        """
        from django.utils import timezone
        from datetime import timedelta

        cutoff_time = timezone.now() - timedelta(minutes=minutes)
        deleted_count, _ = TypingIndicator.objects.filter(
            updated_at__lt=cutoff_time
        ).delete()

        return deleted_count

    @staticmethod
    def format_typing_indicator(typing_indicator):
        """
        Format a typing indicator for WebSocket transmission.

        Args:
            typing_indicator: TypingIndicator instance

        Returns:
            Dictionary with typing indicator data
        """
        from apps.accounts.serializers import UserBasicSerializer

        return {
            'id': str(typing_indicator.id),
            'conversation_id': str(typing_indicator.conversation.id),
            'user': UserBasicSerializer(typing_indicator.user).data,
            'started_at': typing_indicator.started_at.isoformat(),
            'updated_at': typing_indicator.updated_at.isoformat(),
        }

    @staticmethod
    def get_conversation_unread_count(conversation, user):
        """
        Get count of unread messages in a conversation for a user.

        Args:
            conversation: ChatConversation instance
            user: User instance

        Returns:
            Integer count of unread messages
        """
        return conversation.messages.exclude(
            read_statuses__reader=user
        ).exclude(
            sender=user
        ).count()

    @staticmethod
    def search_conversations(user, query):
        """
        Search conversations by participant names or room names.

        Args:
            user: User instance
            query: Search query string

        Returns:
            QuerySet of matching conversations
        """
        from django.db.models import Q

        return ChatConversation.objects.filter(
            Q(participant1=user) | Q(participant2=user) | Q(members=user),
            Q(participant1__first_name__icontains=query) |
            Q(participant1__last_name__icontains=query) |
            Q(participant2__first_name__icontains=query) |
            Q(participant2__last_name__icontains=query) |
            Q(room__room_name__icontains=query)
        ).distinct()

    @staticmethod
    def search_messages(conversation, query):
        """
        Search messages in a conversation.

        Args:
            conversation: ChatConversation instance
            query: Search query string

        Returns:
            QuerySet of matching messages
        """
        return conversation.messages.filter(
            content__icontains=query
        ).order_by('-created_at')
