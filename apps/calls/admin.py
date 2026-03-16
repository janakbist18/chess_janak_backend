from django.contrib import admin
from apps.calls.models import Call


@admin.register(Call)
class CallAdmin(admin.ModelAdmin):
    list_display = ['id', 'caller', 'receiver', 'status', 'call_type', 'duration', 'created_at']
    list_filter = ['status', 'call_type', 'created_at']
    readonly_fields = ['created_at', 'started_at', 'ended_at', 'duration']
    search_fields = ['caller__email', 'receiver__email', 'caller__username', 'receiver__username']

    def duration(self, obj):
        if obj.duration:
            return f"{obj.duration}s"
        return "-"
    duration.short_description = 'Duration'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('caller', 'receiver')
