from rest_framework import serializers
from apps.chessplay.models_ads import RewardAd, UserAdReward, AdViewerSession


class RewardAdSerializer(serializers.ModelSerializer):
    """Serializer for reward ads"""
    is_available = serializers.ReadOnlyField()

    class Meta:
        model = RewardAd
        fields = [
            'id',
            'title',
            'description',
            'ad_type',
            'status',
            'reward_coins',
            'reward_points',
            'duration_seconds',
            'daily_limit_per_user',
            'ad_url',
            'thumbnail_url',
            'total_impressions',
            'total_completions',
            'is_available',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'total_impressions', 'total_completions', 'created_at', 'updated_at']


class UserAdRewardSerializer(serializers.ModelSerializer):
    """Serializer for user ad rewards"""
    ad_title = serializers.CharField(source='ad.title', read_only=True)

    class Meta:
        model = UserAdReward
        fields = [
            'id',
            'ad',
            'ad_title',
            'viewed_at',
            'completed',
            'completed_at',
            'coins_earned',
            'points_earned',
            'clicked',
            'clicked_at',
        ]
        read_only_fields = [
            'id',
            'viewed_at',
            'completed_at',
            'coins_earned',
            'points_earned',
            'clicked_at',
        ]


class AdViewerSessionSerializer(serializers.ModelSerializer):
    """Serializer for ad viewer sessions"""
    ad_title = serializers.CharField(source='ad.title', read_only=True)

    class Meta:
        model = AdViewerSession
        fields = [
            'id',
            'ad',
            'ad_title',
            'started_at',
            'ended_at',
            'watch_duration_seconds',
            'skipped',
            'skipped_at',
        ]
        read_only_fields = ['id', 'started_at', 'ended_at', 'skipped_at']


class AdRewardResponseSerializer(serializers.Serializer):
    """Serializer for ad reward response"""
    coins = serializers.IntegerField()
    points = serializers.IntegerField()
    message = serializers.CharField(required=False)
