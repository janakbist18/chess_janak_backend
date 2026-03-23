from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.rooms.models import GameRoom
import uuid


class ChatConversation(models.Model):
    """
    Represents a conversation between users.
    Can be:
    - Direct message (peer-to-peer between two users)
    - Room-based (multiple users in a room)
    """
    CONVERSATION_TYPES = [
        ('direct', 'Direct Message'),
        ('room', 'Room Chat'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation_type = models.CharField(
        max_length=20,
        choices=CONVERSATION_TYPES,
        default='direct',
        help_text="Type of conversation: direct (1-to-1) or room-based"
    )

    # For direct messages (peer-to-peer)
    participant1 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='chat_conversations_as_participant1'
    )
    participant2 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='chat_conversations_as_participant2'
    )

    # For room-based conversations (chess room chat)
    room = models.OneToOneField(
        GameRoom,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='chat_conversation'
    )

    # Members in room-based conversations
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='room_conversations'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-last_message_at', '-updated_at']
        indexes = [
            models.Index(fields=['conversation_type', 'created_at']),
            models.Index(fields=['room', 'created_at']),
        ]

    def __str__(self):
        if self.conversation_type == 'direct':
            return f"DM: {self.participant1.get_full_name()} <-> {self.participant2.get_full_name()}"
        else:
            return f"Room Chat: {self.room.room_name if self.room else 'Unknown'}"

    def get_display_name(self):
        """Get a display name for the conversation."""
        if self.conversation_type == 'direct':
            return f"Chat with {self.participant2.get_full_name()}"
        else:
            return self.room.room_name if self.room else "Room Chat"

    def get_participants(self):
        """Get all participants in the conversation."""
        if self.conversation_type == 'direct':
            return [self.participant1, self.participant2]
        else:
            return list(self.members.all())


class ChatMessage(models.Model):
    """
    Represents a single message in a conversation.
    Supports text messages, images, and files.
    """
    MESSAGE_TYPES = [
        ('text', 'Text Message'),
        ('image', 'Image'),
        ('file', 'File'),
        ('system', 'System Message'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        ChatConversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )

    message_type = models.CharField(
        max_length=20,
        choices=MESSAGE_TYPES,
        default='text'
    )
    content = models.TextField(blank=True, help_text="Message text content")

    # For media messages
    media_file = models.FileField(
        upload_to='chat_media/%Y/%m/%d/',
        null=True,
        blank=True
    )

    # Message status
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)

    # Replies/Threading
    reply_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
        ]

    def __str__(self):
        return f"{self.sender.get_full_name()}: {self.content[:50]}"

    def mark_as_edited(self):
        """Mark message as edited."""
        self.is_edited = True
        self.edited_at = timezone.now()
        self.save()


class MessageReadStatus(models.Model):
    """
    Track message read status for delivery confirmation.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(
        ChatMessage,
        on_delete=models.CASCADE,
        related_name='read_statuses'
    )
    reader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='message_read_statuses'
    )

    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('message', 'reader')
        indexes = [
            models.Index(fields=['message', 'reader']),
        ]

    def __str__(self):
        return f"{self.reader.get_full_name()} read message at {self.read_at}"


class BlockedUser(models.Model):
    """
    Track blocked users for messaging.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    blocker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='blocked_users'
    )
    blocked_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='blocked_by_users'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('blocker', 'blocked_user')
        indexes = [
            models.Index(fields=['blocker', 'blocked_user']),
        ]

    def __str__(self):
        return f"{self.blocker.get_full_name()} blocked {self.blocked_user.get_full_name()}"


class TypingIndicator(models.Model):
    """
    Track typing indicators for real-time chat UX.
    Ephemeral data - auto-cleanup can be implemented via management commands.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        ChatConversation,
        on_delete=models.CASCADE,
        related_name='typing_indicators'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='typing_in'
    )

    started_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('conversation', 'user')
        indexes = [
            models.Index(fields=['conversation', 'user']),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} is typing in {self.conversation.get_display_name()}"
