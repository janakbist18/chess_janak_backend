"""
WebSocket consumers for real-time chat functionality.
Handles message sending, read receipts, typing indicators, and presence.
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from apps.chat.models import (
    ChatConversation, ChatMessage, MessageReadStatus,
    BlockedUser, TypingIndicator
)
from apps.chat.serializers import (
    ChatMessageSerializer, TypingIndicatorSerializer
)

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for direct chat messaging.

    Supports:
    - Sending messages
    - Receiving messages
    - Read receipts
    - Typing indicators
    - User presence
    """

    async def connect(self):
        """Handle WebSocket connection."""
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.conversation_group_name = f'chat_{self.conversation_id}'
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        # Join conversation group
        await self.channel_layer.group_add(
            self.conversation_group_name,
            self.channel_name
        )
        await self.accept()

        # Mark conversation as read
        await self.mark_conversation_read()

        # Notify others that user joined
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                'type': 'user_joined',
                'user_id': str(self.user.id),
                'username': self.user.get_full_name(),
            }
        )

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Remove typing indicator
        await self.remove_typing_indicator()

        # Notify others that user left
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                'type': 'user_left',
                'user_id': str(self.user.id),
                'username': self.user.get_full_name(),
            }
        )

        # Leave conversation group
        await self.channel_layer.group_discard(
            self.conversation_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'chat_message':
                await self.handle_chat_message(data)
            elif message_type == 'read_receipt':
                await self.handle_read_receipt(data)
            elif message_type == 'typing_start':
                await self.handle_typing_start(data)
            elif message_type == 'typing_stop':
                await self.handle_typing_stop(data)
            elif message_type == 'mark_read':
                await self.handle_mark_as_read(data)
            else:
                await self.send_error(f"Unknown message type: {message_type}")

        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
        except Exception as e:
            await self.send_error(f"Error processing message: {str(e)}")

    async def handle_chat_message(self, data):
        """Handle incoming chat message."""
        content = data.get('content', '').strip()
        message_type = data.get('message_type', 'text')
        reply_to_id = data.get('reply_to_id')

        if not content:
            await self.send_error("Message content is required")
            return

        # Create message in database
        message = await self.save_message(content, message_type, reply_to_id)

        if message:
            # Broadcast to group
            await self.channel_layer.group_send(
                self.conversation_group_name,
                {
                    'type': 'chat_message',
                    'message': await self.serialize_message(message),
                }
            )

            # Remove typing indicator after sending
            await self.remove_typing_indicator()

    async def handle_read_receipt(self, data):
        """Handle read receipt for a message."""
        message_id = data.get('message_id')

        if message_id:
            await self.mark_message_read(message_id)
            await self.channel_layer.group_send(
                self.conversation_group_name,
                {
                    'type': 'message_read',
                    'message_id': message_id,
                    'user_id': str(self.user.id),
                }
            )

    async def handle_typing_start(self, data):
        """Handle typing indicator start."""
        typing_indicator = await self.set_typing_indicator()

        if typing_indicator:
            await self.channel_layer.group_send(
                self.conversation_group_name,
                {
                    'type': 'user_typing',
                    'typing_indicator': await self.serialize_typing_indicator(typing_indicator),
                }
            )

    async def handle_typing_stop(self, data):
        """Handle typing indicator stop."""
        await self.remove_typing_indicator()
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                'type': 'user_stopped_typing',
                'user_id': str(self.user.id),
            }
        )

    async def handle_mark_as_read(self, data):
        """Handle marking all messages as read."""
        await self.mark_conversation_read()
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                'type': 'conversation_read',
                'user_id': str(self.user.id),
            }
        )

    # Message handlers for group events
    async def chat_message(self, event):
        """Send chat message to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'data': event['message'],
        }))

    async def message_read(self, event):
        """Send read receipt to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'message_read',
            'message_id': event['message_id'],
            'user_id': event['user_id'],
        }))

    async def user_typing(self, event):
        """Send typing indicator to WebSocket."""
        # Don't send typing indicator back to the typing user
        if event['typing_indicator']['user']['id'] != str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'user_typing',
                'data': event['typing_indicator'],
            }))

    async def user_stopped_typing(self, event):
        """Send stopped typing notification to WebSocket."""
        if event['user_id'] != str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'user_stopped_typing',
                'user_id': event['user_id'],
            }))

    async def user_joined(self, event):
        """Send user joined notification."""
        if event['user_id'] != str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'user_joined',
                'user_id': event['user_id'],
                'username': event['username'],
            }))

    async def user_left(self, event):
        """Send user left notification."""
        if event['user_id'] != str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'user_left',
                'user_id': event['user_id'],
                'username': event['username'],
            }))

    async def conversation_read(self, event):
        """Send conversation read notification."""
        if event['user_id'] != str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'conversation_read',
                'user_id': event['user_id'],
            }))

    async def connection_error(self, event):
        """Send connection error to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': event['message'],
        }))

    async def send_error(self, message):
        """Send error message to client."""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message,
        }))

    # Database operations
    @database_sync_to_async
    def save_message(self, content, message_type='text', reply_to_id=None):
        """Save a message to the database."""
        try:
            conversation = ChatConversation.objects.get(id=self.conversation_id)

            # Check if user is blocked
            if BlockedUser.objects.filter(
                blocker__in=conversation.get_participants(),
                blocked_user=self.user
            ).exists():
                return None

            reply_to = None
            if reply_to_id:
                try:
                    reply_to = ChatMessage.objects.get(id=reply_to_id)
                except ChatMessage.DoesNotExist:
                    pass

            message = ChatMessage.objects.create(
                conversation=conversation,
                sender=self.user,
                message_type=message_type,
                content=content,
                reply_to=reply_to
            )

            # Mark as read by sender
            MessageReadStatus.objects.get_or_create(
                message=message,
                reader=self.user
            )

            # Update conversation's last_message_at
            from django.utils import timezone
            conversation.last_message_at = timezone.now()
            conversation.save(update_fields=['last_message_at', 'updated_at'])

            return message
        except Exception as e:
            print(f"Error saving message: {e}")
            return None

    @database_sync_to_async
    def mark_message_read(self, message_id):
        """Mark a message as read."""
        try:
            message = ChatMessage.objects.get(id=message_id)
            MessageReadStatus.objects.get_or_create(
                message=message,
                reader=self.user
            )
        except Exception as e:
            print(f"Error marking message as read: {e}")

    @database_sync_to_async
    def mark_conversation_read(self):
        """Mark all messages in conversation as read."""
        try:
            conversation = ChatConversation.objects.get(id=self.conversation_id)
            unread_messages = conversation.messages.exclude(
                read_statuses__reader=self.user
            ).exclude(sender=self.user)

            read_statuses = [
                MessageReadStatus(message=msg, reader=self.user)
                for msg in unread_messages
            ]
            MessageReadStatus.objects.bulk_create(
                read_statuses,
                ignore_conflicts=True
            )
        except Exception as e:
            print(f"Error marking conversation as read: {e}")

    @database_sync_to_async
    def set_typing_indicator(self):
        """Create or update typing indicator."""
        try:
            conversation = ChatConversation.objects.get(id=self.conversation_id)
            from django.utils import timezone
            typing_indicator, _ = TypingIndicator.objects.update_or_create(
                conversation=conversation,
                user=self.user,
                defaults={'updated_at': timezone.now()}
            )
            return typing_indicator
        except Exception as e:
            print(f"Error setting typing indicator: {e}")
            return None

    @database_sync_to_async
    def remove_typing_indicator(self):
        """Remove typing indicator."""
        try:
            TypingIndicator.objects.filter(
                conversation_id=self.conversation_id,
                user=self.user
            ).delete()
        except Exception as e:
            print(f"Error removing typing indicator: {e}")

    @database_sync_to_async
    def serialize_message(self, message):
        """Serialize a message for sending over WebSocket."""
        return {
            'id': str(message.id),
            'conversation_id': str(message.conversation.id),
            'sender': {
                'id': str(message.sender.id),
                'first_name': message.sender.first_name,
                'last_name': message.sender.last_name,
                'full_name': message.sender.get_full_name(),
            },
            'message_type': message.message_type,
            'content': message.content,
            'is_edited': message.is_edited,
            'edited_at': message.edited_at.isoformat() if message.edited_at else None,
            'reply_to_id': str(message.reply_to.id) if message.reply_to else None,
            'created_at': message.created_at.isoformat(),
            'updated_at': message.updated_at.isoformat(),
        }

    @database_sync_to_async
    def serialize_typing_indicator(self, typing_indicator):
        """Serialize a typing indicator for sending over WebSocket."""
        return {
            'id': str(typing_indicator.id),
            'conversation_id': str(typing_indicator.conversation.id),
            'user': {
                'id': str(typing_indicator.user.id),
                'first_name': typing_indicator.user.first_name,
                'last_name': typing_indicator.user.last_name,
                'full_name': typing_indicator.user.get_full_name(),
            },
            'started_at': typing_indicator.started_at.isoformat(),
            'updated_at': typing_indicator.updated_at.isoformat(),
        }
