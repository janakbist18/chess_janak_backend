from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.chat.models import Conversation, Message

User = get_user_model()


class UserSimpleSerializer(serializers.ModelSerializer):
    """Simple user serializer for chat context"""

    class Meta:
        model = User
        fields = ['id', 'email', 'username']


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for chat messages"""

    sender = UserSimpleSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'conversation', 'sender', 'content', 'created_at', 'is_read', 'read_at']
        read_only_fields = ['id', 'created_at', 'is_read', 'read_at']


class ConversationListSerializer(serializers.ModelSerializer):
    """Serializer for conversation list view"""

    participants = UserSimpleSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'participants', 'last_message', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_last_message(self, obj):
        last_message = obj.messages.first()
        if last_message:
            return MessageSerializer(last_message).data
        return None


class ConversationDetailSerializer(serializers.ModelSerializer):
    """Serializer for conversation detail view with messages"""

    participants = UserSimpleSerializer(many=True, read_only=True)
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ['id', 'participants', 'messages', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']