from django.contrib import admin
from .models import Call, CallLog


@admin.register(Call)
class CallAdmin(admin.ModelAdmin):
    list_display = ('id', 'caller', 'receiver', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('caller__username', 'receiver__username')


@admin.register(CallLog)
class CallLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'caller', 'receiver', 'duration', 'created_at')
    search_fields = ('caller__username', 'receiver__username')
