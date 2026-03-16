"""
Game invitation and video call API views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action  
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
import uuid

from apps.rooms.models_invitations import (
    GameInvitation,
    VideoCallSession,
    ICECandidate
)
from apps.chessplay.models import ChessMatch
from apps.rooms.models import GameRoom


class GameInvitationViewSet(viewsets.ViewSet):
    """Game invitation endpoints"""
    
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=["post"])
    def create_invitation(self, request):
        """Create and send game invitation"""
        invitee_id = request.data.get('invitee_id')
        time_control = request.data.get('time_control', 'blitz')
        message = request.data.get('message', '')
        
        if not invitee_id:
            return Response(
                {"error": "invitee_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from apps.accounts.models import User
            invitee = User.objects.get(id=invitee_id)
            
            if invitee == request.user:
                return Response(
                    {"error": "Cannot invite yourself"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            invitation = GameInvitation.objects.create(
                inviter=request.user,
                invitee=invitee,
                time_control=time_control,
                message=message,
                expires_at=timezone.now() + timedelta(hours=24),
            )
            
            return Response({
                "message": "Invitation created",
                "invitation_id": invitation.id,
                "join_code": invitation.join_code,
            }, status=status.HTTP_201_CREATED)
        
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=["get"])
    def my_invitations(self, request):
        """Get pending invitations for current user"""
        invitations = GameInvitation.objects.filter(
            invitee=request.user,
            status=GameInvitation.STATUS_PENDING
        ).select_related('inviter')
        
        data = []
        for inv in invitations:
            data.append({
                "id": inv.id,
                "inviter": inv.inviter.username,
                "inviter_id": inv.inviter.id,
                "time_control": inv.time_control,
                "message": inv.message,
                "join_code": inv.join_code,
                "created_at": inv.created_at,
            })
        
        return Response({"invitations": data})
    
    @action(detail=False, methods=["post"])
    def accept_invitation(self, request):
        """Accept game invitation"""
        invitation_id = request.data.get('invitation_id')
        
        if not invitation_id:
            return Response(
                {"error": "invitation_id required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            invitation = GameInvitation.objects.get(
                id=invitation_id,
                invitee=request.user,
                status=GameInvitation.STATUS_PENDING
            )
            
            # Create game room and match
            room = GameRoom.objects.create(
                room_code=invitation.join_code,
                created_by=invitation.inviter,
            )
            
            match = ChessMatch.objects.create(
                room=room,
                white_player=invitation.inviter,
                black_player=invitation.invitee,
                status=ChessMatch.STATUS_IN_PROGRESS,
            )
            
            # Update invitation
            invitation.status = GameInvitation.STATUS_ACCEPTED
            invitation.game_room = room
            invitation.save()
            
            return Response({
                "message": "Invitation accepted",
                "game_id": match.id,
                "room_code": room.room_code,
            })
        
        except GameInvitation.DoesNotExist:
            return Response(
                {"error": "Invitation not found"},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=["post"])
    def decline_invitation(self, request):
        """Decline game invitation"""
        invitation_id = request.data.get('invitation_id')
        
        if not invitation_id:
            return Response(
                {"error": "invitation_id required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            invitation = GameInvitation.objects.get(
                id=invitation_id,
                invitee=request.user
            )
            invitation.status = GameInvitation.STATUS_DECLINED
            invitation.save()
            
            return Response({"message": "Invitation declined"})
        
        except GameInvitation.DoesNotExist:
            return Response(
                {"error": "Invitation not found"},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=["get"])
    def join_game(self, request):
        """Join game using invitation code"""
        join_code = request.query_params.get('code')
        
        if not join_code:
            return Response(
                {"error": "join code required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            invitation = GameInvitation.objects.get(
                join_code=join_code,
                status__in=[
                    GameInvitation.STATUS_PENDING,
                    GameInvitation.STATUS_ACCEPTED
                ]
            )
            
            if invitation.expires_at < timezone.now():
                invitation.status = GameInvitation.STATUS_EXPIRED
                invitation.save()
                return Response(
                    {"error": "Invitation expired"},
                    status=status.HTTP_410_GONE
                )
            
            # Get or create game room
            if invitation.game_room:
                room = invitation.game_room
                match = room.match
            else:
                room = invitation.game_room or GameRoom.objects.create(
                    room_code=join_code,
                    created_by=invitation.inviter,
                )
            
            return Response({
                "game_id": match.id if invitation.game_room else None,
                "room_code": join_code,
                "status": invitation.status,
            })
        
        except GameInvitation.DoesNotExist:
            return Response(
                {"error": "Invalid join code"},
                status=status.HTTP_404_NOT_FOUND
            )


class VideoCallViewSet(viewsets.ViewSet):
    """Video/Audio call endpoints"""
    
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=["post"])
    def initiate_call(self, request):
        """Initiate video/audio call"""
        receiver_id = request.data.get('receiver_id')
        game_match_id = request.data.get('game_match_id')
        
        if not receiver_id:
            return Response(
                {"error": "receiver_id required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from apps.accounts.models import User
            receiver = User.objects.get(id=receiver_id)
            
            match = None
            if game_match_id:
                match = ChessMatch.objects.get(id=game_match_id)
            
            # Check if call already exists
            existing = VideoCallSession.objects.filter(
                initiator=request.user,
                receiver=receiver,
                status__in=['initializing', 'active']
            ).first()
            
            if existing:
                return Response(
                    {"error": "Call already exists"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            session_id = str(uuid.uuid4())
            
            call = VideoCallSession.objects.create(
                initiator=request.user,
                receiver=receiver,
                session_id=session_id,
                game_match=match,
                status=VideoCallSession.STATUS_INITIALIZING,
            )
            
            return Response({
                "message": "Call initiated",
                "session_id": session_id,
                "call_id": call.id,
            }, status=status.HTTP_201_CREATED)
        
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=["post"])
    def answer_call(self, request):
        """Answer incoming call"""
        session_id = request.data.get('session_id')
        answer_sdp = request.data.get('answer_sdp')
        
        if not session_id:
            return Response(
                {"error": "session_id required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            call = VideoCallSession.objects.get(
                session_id=session_id,
                receiver=request.user,
                status=VideoCallSession.STATUS_INITIALIZING
            )
            
            if answer_sdp:
                call.answer_sdp = answer_sdp
            
            call.status = VideoCallSession.STATUS_ACTIVE
            call.started_at = timezone.now()
            call.save()
            
            return Response({
                "message": "Call answered",
                "offer_sdp": call.offer_sdp,
            })
        
        except VideoCallSession.DoesNotExist:
            return Response(
                {"error": "Call not found"},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=["post"])
    def add_ice_candidate(self, request):
        """Add ICE candidate for WebRTC"""
        session_id = request.data.get('session_id')
        candidate = request.data.get('candidate')
        sdp_mline_index = request.data.get('sdp_mline_index')
        
        if not session_id or not candidate:
            return Response(
                {"error": "session_id and candidate required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            call = VideoCallSession.objects.get(session_id=session_id)
            
            # Determine who receives this candidate
            if call.initiator == request.user:
                received_by = call.receiver
                sent_by = call.initiator
            else:
                received_by = call.initiator
                sent_by = call.receiver
            
            ICECandidate.objects.create(
                call_session=call,
                candidate=candidate,
                sdp_mline_index=sdp_mline_index,
                sent_by=sent_by,
                received_by=received_by,
            )
            
            return Response({"message": "ICE candidate added"})
        
        except VideoCallSession.DoesNotExist:
            return Response(
                {"error": "Call not found"},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=["post"])
    def end_call(self, request):
        """End video/audio call"""
        session_id = request.data.get('session_id')
        
        if not session_id:
            return Response(
                {"error": "session_id required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            call = VideoCallSession.objects.get(session_id=session_id)
            
            call.status = VideoCallSession.STATUS_ENDED
            call.ended_at = timezone.now()
            
            if call.started_at:
                duration = (call.ended_at - call.started_at).total_seconds()
                call.duration_seconds = int(duration)
            
            call.save()
            
            return Response({
                "message": "Call ended",
                "duration": call.duration_seconds,
            })
        
        except VideoCallSession.DoesNotExist:
            return Response(
                {"error": "Call not found"},
                status=status.HTTP_404_NOT_FOUND
            )
