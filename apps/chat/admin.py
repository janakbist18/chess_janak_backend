from django.contrib import admin
from apps.chat.models import Conversation, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'created_at', 'updated_at', 'participant_count']
    filter_horizontal = ['participants']
    readonly_fields = ['created_at', 'updated_at']
    search_fields = ['participants__email', 'participants__username']

    def participant_count(self, obj):
        return obj.participants.count()
    participant_count.short_description = 'Participants'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'sender', 'conversation', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    readonly_fields = ['created_at', 'read_at']
    search_fields = ['sender__email', 'content', 'conversation__id']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('sender', 'conversation')
