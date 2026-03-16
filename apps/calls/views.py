from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.contrib.auth import get_user_model

from apps.calls.models import Call
from apps.calls.serializers import CallSerializer

User = get_user_model()


class CallViewSet(viewsets.ModelViewSet):
    """ViewSet for managing calls"""

    permission_classes = [IsAuthenticated]
    serializer_class = CallSerializer
    queryset = Call.objects.all()

    def get_queryset(self):
        """Return calls for the current user"""
        return Call.objects.filter(
            Q(caller=self.request.user) | Q(receiver=self.request.user)
        ).select_related('caller', 'receiver')

    @action(detail=False, methods=['post'])
    def initiate(self, request):
        """Initiate a call with another user"""
        receiver_id = request.data.get('receiver_id')
        call_type = request.data.get('call_type', 'voice')

        if not receiver_id:
            return Response(
                {'error': 'receiver_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            receiver = User.objects.get(id=receiver_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Create new call
        call = Call.objects.create(
            caller=request.user,
            receiver=receiver,
            call_type=call_type
        )

        serializer = CallSerializer(call)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """Accept an incoming call"""
        call = self.get_object()

        if call.receiver != request.user:
            return Response(
                {'error': 'Only receiver can accept this call'},
                status=status.HTTP_403_FORBIDDEN
            )

        if call.status != 'pending':
            return Response(
                {'error': f'Cannot accept a {call.status} call'},
                status=status.HTTP_400_BAD_REQUEST
            )

        call.accept()
        serializer = CallSerializer(call)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        """Decline an incoming call"""
        call = self.get_object()

        if call.receiver != request.user:
            return Response(
                {'error': 'Only receiver can decline this call'},
                status=status.HTTP_403_FORBIDDEN
            )

        if call.status != 'pending':
            return Response(
                {'error': f'Cannot decline a {call.status} call'},
                status=status.HTTP_400_BAD_REQUEST
            )

        call.decline()
        serializer = CallSerializer(call)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def end(self, request, pk=None):
        """End an active call"""
        call = self.get_object()

        if call.status != 'active':
            return Response(
                {'error': f'Cannot end a {call.status} call'},
                status=status.HTTP_400_BAD_REQUEST
            )

        call.end()
        serializer = CallSerializer(call)
        return Response(serializer.data)
