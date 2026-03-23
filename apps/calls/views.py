from django.utils import timezone
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
import logging

from apps.accounts.models import User
from .models import Call, CallLog
from .serializers import CallSerializer, CallLogSerializer, InitiateCallSerializer

logger = logging.getLogger(__name__)


class InitiateCallView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = InitiateCallSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        receiver_id = serializer.validated_data['receiver_id']
        receiver = User.objects.get(id=receiver_id)

        # Check if caller is calling themselves
        if request.user.id == receiver_id:
            return Response(
                {"error": "You cannot call yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # End any existing active calls for the caller
        Call.objects.filter(
            caller=request.user,
            status__in=['pending', 'active']
        ).update(status='ended', ended_at=timezone.now())

        # Create new call
        call = Call.objects.create(
            caller=request.user,
            receiver=receiver,
            status='pending'
        )

        return Response(
            {
                "message": "Call initiated successfully.",
                "call": CallSerializer(call, context={"request": request}).data,
            },
            status=status.HTTP_201_CREATED,
        )


class AnswerCallView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, call_id):
        try:
            call = Call.objects.get(id=call_id)
        except Call.DoesNotExist:
            return Response(
                {"error": "Call not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if call.receiver != request.user:
            return Response(
                {"error": "You are not the receiver of this call."},
                status=status.HTTP_403_FORBIDDEN,
            )

        call.status = 'active'
        call.started_at = timezone.now()
        call.save()

        return Response(
            {
                "message": "Call answered successfully.",
                "call": CallSerializer(call, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )


class RejectCallView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, call_id):
        try:
            call = Call.objects.get(id=call_id)
        except Call.DoesNotExist:
            return Response(
                {"error": "Call not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if call.receiver != request.user:
            return Response(
                {"error": "You are not the receiver of this call."},
                status=status.HTTP_403_FORBIDDEN,
            )

        call.status = 'rejected'
        call.ended_at = timezone.now()
        call.save()

        return Response(
            {"message": "Call rejected."},
            status=status.HTTP_200_OK,
        )


class EndCallView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, call_id):
        try:
            call = Call.objects.get(id=call_id)
        except Call.DoesNotExist:
            return Response(
                {"error": "Call not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if call.caller != request.user and call.receiver != request.user:
            return Response(
                {"error": "You are not part of this call."},
                status=status.HTTP_403_FORBIDDEN,
            )

        call.status = 'ended'
        call.ended_at = timezone.now()
        call.save()

        # Log the call
        duration = int(call.get_duration())
        CallLog.objects.create(
            caller=call.caller,
            receiver=call.receiver,
            duration=duration,
            call_type='video'
        )

        return Response(
            {
                "message": "Call ended.",
                "call": CallSerializer(call, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )


class ActiveCallView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get active or pending calls for the user
        calls = Call.objects.filter(
            receiver=request.user,
            status__in=['pending', 'active']
        ).order_by('-created_at')

        serializer = CallSerializer(calls, many=True, context={"request": request})
        return Response(
            {
                "calls": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class CallHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        logs = CallLog.objects.filter(
            Q(caller=request.user) | Q(receiver=request.user)
        ).order_by('-created_at')[:50]

        serializer = CallLogSerializer(logs, many=True, context={"request": request})
        return Response(
            {
                "call_history": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
