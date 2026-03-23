from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.accounts.serializers import UserBasicSerializer
from .models import ChatConversation, ChatMessage, MessageReadStatus, BlockedUser, TypingIndicator

User = get_user_model()


class ChatMessageSerializer(serializers.ModelSerializer):
    """Serializer for chat messages."""
    sender = UserBasicSerializer(read_only=True)
    reply_to_id = serializers.SerializerMethodField()
    is_read = serializers.SerializerMethodField()
    read_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = [
            'id', 'conversation', 'sender', 'message_type', 'content',
            'media_file', 'is_edited', 'edited_at', 'reply_to', 'reply_to_id',
            'created_at', 'updated_at', 'is_read', 'read_count'
        ]
        read_only_fields = ['id', 'sender', 'created_at', 'updated_at', 'is_edited', 'edited_at']

    def get_reply_to_id(self, obj):
        """Get the ID of the message being replied to."""
        return str(obj.reply_to.id) if obj.reply_to else None

    def get_is_read(self, obj):
        """Check if message has been read by current user."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.read_statuses.filter(reader=request.user).exists()

    def get_read_count(self, obj):
        """Get count of users who have read this message."""
        return obj.read_statuses.count()


class CreateChatMessageSerializer(serializers.ModelSerializer):
    """Serializer for creating new chat messages."""

    class Meta:
        model = ChatMessage
        fields = ['conversation', 'message_type', 'content', 'media_file', 'reply_to']
        extra_kwargs = {
            'content': {'required': True},
        }

    def validate(self, data):
        """Ensure message has content or media."""
        if not data.get('content') and not data.get('media_file'):
            raise serializers.ValidationError("Message must have text content or a media file.")
        return data

    def create(self, validated_data):
        """Create message with sender from request."""
        validated_data['sender'] = self.context['request'].user
        return super().create(validated_data)


class ChatConversationListSerializer(serializers.ModelSerializer):
    """Serializer for listing conversations."""
    display_name = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    other_participant = serializers.SerializerMethodField()

    class Meta:
        model = ChatConversation
        fields = [
            'id', 'conversation_type', 'display_name', 'last_message',
            'last_message_at', 'created_at', 'updated_at', 'unread_count',
            'other_participant'
        ]

    def get_display_name(self, obj):
        """Get the display name for the conversation."""
        return obj.get_display_name()

    def get_last_message(self, obj):
        """Get the last message in the conversation."""
        last_msg = obj.messages.last()
        if last_msg:
            return {
                'id': str(last_msg.id),
                'content': last_msg.content[:100],
                'sender': last_msg.sender.get_full_name(),
                'created_at': last_msg.created_at
            }
        return None

    def get_unread_count(self, obj):
        """Get count of unread messages for current user."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 0

        # Count messages not read by current user
        return obj.messages.exclude(
            read_statuses__reader=request.user
        ).exclude(
            sender=request.user
        ).count()

    def get_other_participant(self, obj):
        """Get the other participant in a direct message conversation."""
        request = self.context.get('request')
        if not request or obj.conversation_type != 'direct':
            return None

        if obj.participant1 == request.user:
            return UserBasicSerializer(obj.participant2).data
        else:
            return UserBasicSerializer(obj.participant1).data


class ChatConversationDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for a single conversation."""
    messages = ChatMessageSerializer(many=True, read_only=True)
    participants = serializers.SerializerMethodField()

    class Meta:
        model = ChatConversation
        fields = [
            'id', 'conversation_type', 'participant1', 'participant2', 'room',
            'members', 'created_at', 'updated_at', 'last_message_at',
            'messages', 'participants'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_message_at']

    def get_participants(self, obj):
        """Get all participants in the conversation."""
        participants = obj.get_participants()
        return UserBasicSerializer(participants, many=True).data


class MessageReadStatusSerializer(serializers.ModelSerializer):
    """Serializer for message read status."""
    reader = UserBasicSerializer(read_only=True)

    class Meta:
        model = MessageReadStatus
        fields = ['id', 'message', 'reader', 'read_at']
        read_only_fields = ['id', 'read_at']


class BlockedUserSerializer(serializers.ModelSerializer):
    """Serializer for blocked users."""
    blocked_user_detail = UserBasicSerializer(source='blocked_user', read_only=True)

    class Meta:
        model = BlockedUser
        fields = ['id', 'blocked_user', 'blocked_user_detail', 'created_at']
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        """Create a blocked user entry."""
        validated_data['blocker'] = self.context['request'].user
        return super().create(validated_data)


class TypingIndicatorSerializer(serializers.ModelSerializer):
    """Serializer for typing indicators."""
    user = UserBasicSerializer(read_only=True)

    class Meta:
        model = TypingIndicator
        fields = ['id', 'conversation', 'user', 'started_at', 'updated_at']
        read_only_fields = ['id', 'started_at', 'updated_at']

    def create(self, validated_data):
        """Create or update typing indicator."""
        validated_data['user'] = self.context['request'].user
        obj, created = TypingIndicator.objects.update_or_create(
            conversation=validated_data['conversation'],
            user=validated_data['user'],
            defaults={'updated_at': timezone.now()}
        )
        return obj


# Add missing import
from django.utils import timezone
