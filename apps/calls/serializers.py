from rest_framework import serializers
from apps.accounts.serializers import UserSerializer
from .models import Call, CallLog


class CallSerializer(serializers.ModelSerializer):
    caller = UserSerializer(read_only=True)
    receiver = UserSerializer(read_only=True)
    duration = serializers.SerializerMethodField()

    class Meta:
        model = Call
        fields = ('id', 'caller', 'receiver', 'status', 'duration', 'started_at', 'ended_at', 'created_at')
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_duration(self, obj):
        return obj.get_duration()


class CallLogSerializer(serializers.ModelSerializer):
    caller = UserSerializer(read_only=True)
    receiver = UserSerializer(read_only=True)

    class Meta:
        model = CallLog
        fields = ('id', 'caller', 'receiver', 'duration', 'call_type', 'created_at')
        read_only_fields = ('id', 'created_at')


class InitiateCallSerializer(serializers.Serializer):
    receiver_id = serializers.IntegerField()
    call_type = serializers.CharField(max_length=20, default='video')

    def validate_receiver_id(self, value):
        from apps.accounts.models import User
        try:
            User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("Receiver user not found.")
        return value
