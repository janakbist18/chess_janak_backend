from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.calls.models import Call

User = get_user_model()


class UserSimpleSerializer(serializers.ModelSerializer):
    """Simple user serializer for call context"""

    class Meta:
        model = User
        fields = ['id', 'email', 'username']


class CallSerializer(serializers.ModelSerializer):
    """Serializer for calls"""

    caller = UserSimpleSerializer(read_only=True)
    receiver = UserSimpleSerializer(read_only=True)
    duration = serializers.ReadOnlyField()

    class Meta:
        model = Call
        fields = [
            'id',
            'caller',
            'receiver',
            'status',
            'call_type',
            'started_at',
            'ended_at',
            'duration',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'started_at', 'ended_at']