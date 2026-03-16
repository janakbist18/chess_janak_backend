from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone

from apps.chessplay.models_ads import RewardAd, UserAdReward, AdViewerSession
from apps.chessplay.serializers_ads import (
    RewardAdSerializer,
    UserAdRewardSerializer,
    AdViewerSessionSerializer,
    AdRewardResponseSerializer,
)


class RewardAdViewSet(viewsets.ModelViewSet):
    """ViewSet for reward ads"""

    permission_classes = [permissions.AllowAny]
    serializer_class = RewardAdSerializer
    queryset = RewardAd.objects.all()

    def get_queryset(self):
        """Return active ads available for viewing"""
        queryset = RewardAd.objects.filter(status='active')

        # Filter by availability
        now = timezone.now()
        queryset = queryset.filter(
            Q(starts_at__isnull=True) | Q(starts_at__lte=now)
        ).filter(
            Q(ends_at__isnull=True) | Q(ends_at__gte=now)
        )

        return queryset.order_by('-created_at')

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def available(self, request):
        """Get all available ads for watching"""
        ads = self.get_queryset()

        # Filter by impressions limit
        available_ads = [ad for ad in ads if ad.is_available]

        serializer = self.get_serializer(available_ads, many=True)
        return Response({
            'count': len(available_ads),
            'ads': serializer.data,
        })

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def start_watching(self, request, pk=None):
        """Start watching an ad"""
        ad = self.get_object()

        if not ad.is_available:
            return Response(
                {'error': 'Ad is not available'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check daily limit
        today = timezone.now().date()
        daily_views = UserAdReward.objects.filter(
            user=request.user,
            ad=ad,
            viewed_at__date=today
        ).count()

        if daily_views >= ad.daily_limit_per_user:
            return Response(
                {
                    'error': f'Daily limit reached. You can watch {ad.daily_limit_per_user} ads per day.',
                    'limit': ad.daily_limit_per_user,
                    'viewed_today': daily_views,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create viewer session
        session = AdViewerSession.objects.create(
            user=request.user,
            ad=ad
        )

        # Create reward record
        reward = UserAdReward.objects.create(
            user=request.user,
            ad=ad
        )

        # Update impressions
        ad.total_impressions += 1
        ad.save()

        return Response({
            'session_id': session.id,
            'reward_id': reward.id,
            'ad': RewardAdSerializer(ad).data,
            'message': 'Ad viewing started. Watch the ad to earn rewards!',
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def complete_watching(self, request):
        """Complete watching an ad and claim rewards"""
        reward_id = request.data.get('reward_id')
        session_id = request.data.get('session_id')
        watch_duration = request.data.get('watch_duration_seconds', 0)

        if not reward_id:
            return Response(
                {'error': 'reward_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            reward = UserAdReward.objects.get(
                id=reward_id,
                user=request.user
            )
        except UserAdReward.DoesNotExist:
            return Response(
                {'error': 'Reward not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Mark ad as completed
        reward_data = reward.mark_completed()

        # Update session
        if session_id:
            try:
                session = AdViewerSession.objects.get(id=session_id)
                session.mark_ended(watch_duration)
            except AdViewerSession.DoesNotExist:
                pass

        return Response({
            'message': 'Ad completed! Rewards earned.',
            'coins_earned': reward.coins_earned,
            'points_earned': reward.points_earned,
            'reward': UserAdRewardSerializer(reward).data,
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def skip_ad(self, request):
        """Skip watching an ad"""
        session_id = request.data.get('session_id')

        if not session_id:
            return Response(
                {'error': 'session_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            session = AdViewerSession.objects.get(
                id=session_id,
                user=request.user
            )
        except AdViewerSession.DoesNotExist:
            return Response(
                {'error': 'Session not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        session.mark_skipped()

        return Response({
            'message': 'Ad skipped',
            'session': AdViewerSessionSerializer(session).data,
        }, status=status.HTTP_200_OK)


class UserAdRewardViewSet(viewsets.ModelViewSet):
    """ViewSet for user ad rewards"""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserAdRewardSerializer
    queryset = UserAdReward.objects.all()

    def get_queryset(self):
        """Return rewards for the current user"""
        return UserAdReward.objects.filter(
            user=self.request.user
        ).select_related('ad')

    @action(detail=False, methods=['get'])
    def completed(self, request):
        """Get completed ad rewards"""
        rewards = self.get_queryset().filter(completed=True)
        serializer = self.get_serializer(rewards, many=True)
        return Response({
            'count': rewards.count(),
            'rewards': serializer.data,
        })

    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get today's ad rewards"""
        today = timezone.now().date()
        rewards = self.get_queryset().filter(viewed_at__date=today)
        serializer = self.get_serializer(rewards, many=True)

        total_coins = sum(r.coins_earned for r in rewards)
        total_points = sum(r.points_earned for r in rewards)

        return Response({
            'count': rewards.count(),
            'total_coins': total_coins,
            'total_points': total_points,
            'rewards': serializer.data,
        })

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get user's ad reward statistics"""
        all_rewards = self.get_queryset()
        completed = all_rewards.filter(completed=True)

        total_coins = sum(r.coins_earned for r in completed)
        total_points = sum(r.points_earned for r in completed)

        return Response({
            'total_ads_watched': all_rewards.count(),
            'completed_ads': completed.count(),
            'total_coins_earned': total_coins,
            'total_points_earned': total_points,
            'completion_rate': f"{(completed.count() / all_rewards.count() * 100) if all_rewards.count() > 0 else 0:.1f}%",
        })
