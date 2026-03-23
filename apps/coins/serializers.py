"""
Django REST Framework serializers for coin system API endpoints.
Handles validation and serialization of coin-related data.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    UserCoin, CoinTransaction, RewardAdConfig, DailyReward,
    AdWatchLog, TransactionType, PaymentPackage, PaymentTransaction, PaymentStatus
)

User = get_user_model()


class CoinBalanceSerializer(serializers.ModelSerializer):
    """Serialize user's coin balance and stats."""
    username = serializers.CharField(source='user.username', read_only=True)
    user_id = serializers.CharField(source='user.id', read_only=True)
    can_claim_daily = serializers.SerializerMethodField()

    class Meta:
        model = UserCoin
        fields = [
            'user_id',
            'username',
            'total_coins',
            'daily_coins_earned',
            'daily_coins_earned',
            'current_streak',
            'max_streak',
            'last_ad_watched',
            'last_daily_claim',
            'can_claim_daily',
            'updated_at'
        ]
        read_only_fields = fields

    def get_can_claim_daily(self, obj):
        """Check if user can claim daily reward."""
        from django.utils import timezone
        today = timezone.now().date()
        return obj.last_daily_claim != today


class CoinTransactionSerializer(serializers.ModelSerializer):
    """Serialize coin transaction records."""
    transaction_type_display = serializers.CharField(
        source='get_transaction_type_display',
        read_only=True
    )
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = CoinTransaction
        fields = [
            'id',
            'username',
            'amount',
            'transaction_type',
            'transaction_type_display',
            'description',
            'balance_after',
            'created_at',
            'related_game_id'
        ]
        read_only_fields = fields


class DailyRewardSerializer(serializers.ModelSerializer):
    """Serialize daily reward records."""
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = DailyReward
        fields = [
            'id',
            'username',
            'date',
            'coins_claimed',
            'streak_bonus_applied',
            'streak_days',
            'claimed_at'
        ]
        read_only_fields = fields


class AdWatchLogSerializer(serializers.ModelSerializer):
    """Serialize ad watch records."""
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = AdWatchLog
        fields = [
            'id',
            'username',
            'watched_at',
            'ad_network',
            'reward_claimed',
            'suspicious'
        ]
        read_only_fields = fields


class RewardAdConfigSerializer(serializers.ModelSerializer):
    """Serialize reward ad configuration."""

    class Meta:
        model = RewardAdConfig
        fields = [
            'ad_reward_amount',
            'daily_watch_limit',
            'cooldown_minutes',
            'blitz_win_reward',
            'rapid_win_reward',
            'classical_win_reward',
            'daily_bonus_amount',
            'streak_multiplier',
            'ads_enabled',
            'updated_at'
        ]
        read_only_fields = fields


class ClaimAdRewardSerializer(serializers.Serializer):
    """
    Request/response serializer for claiming ad reward.
    Validates and returns ad reward claim result.
    """
    # Response fields (read-only)
    success = serializers.BooleanField(read_only=True)
    coins_earned = serializers.IntegerField(read_only=True)
    total_coins = serializers.IntegerField(read_only=True)
    remaining_today = serializers.IntegerField(read_only=True)
    message = serializers.CharField(read_only=True)


class CanWatchAdSerializer(serializers.Serializer):
    """
    Response serializer for checking ad watch eligibility.
    Returns current state of cooldown and limits.
    """
    can_watch = serializers.BooleanField()
    reason = serializers.CharField()
    cooldown_seconds = serializers.IntegerField()
    remaining_today = serializers.IntegerField()
    reward_amount = serializers.IntegerField(required=False)
    next_reset = serializers.DateTimeField(required=False)


class ClaimDailyRewardSerializer(serializers.Serializer):
    """
    Request/response serializer for claiming daily reward.
    """
    # Response fields (read-only)
    success = serializers.BooleanField(read_only=True)
    coins_earned = serializers.IntegerField(read_only=True)
    base_reward = serializers.IntegerField(read_only=True)
    streak_bonus = serializers.IntegerField(read_only=True)
    streak_count = serializers.IntegerField(read_only=True)
    total_coins = serializers.IntegerField(read_only=True)
    message = serializers.CharField(read_only=True)


class SpendCoinsSerializer(serializers.Serializer):
    """
    Request serializer for spending coins.
    Validates amount and purpose.
    """
    amount = serializers.IntegerField(
        min_value=1,
        help_text="Number of coins to spend"
    )
    reason = serializers.CharField(
        max_length=255,
        help_text="Reason for spending (e.g., 'hint', 'theme')"
    )
    related_game_id = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text="ID of related game if applicable"
    )

    def validate_amount(self, value):
        """Ensure amount is reasonable."""
        if value > 1000000:  # Prevent absurdly large amounts
            raise serializers.ValidationError("Amount too large")
        return value

    def validate_reason(self, value):
        """Ensure reason is meaningful."""
        allowed_reasons = ['hint', 'theme', 'promotion', 'other']
        if value.lower() not in allowed_reasons:
            raise serializers.ValidationError(
                f"Invalid reason. Must be one of: {', '.join(allowed_reasons)}"
            )
        return value.lower()


class SpendCoinsResponseSerializer(serializers.Serializer):
    """Response for coin spending operation."""
    success = serializers.BooleanField()
    coins_spent = serializers.IntegerField()
    remaining_coins = serializers.IntegerField()
    message = serializers.CharField()
    transaction_id = serializers.CharField(read_only=True)


class GameWinRewardSerializer(serializers.Serializer):
    """
    Request/response serializer for game win rewards.
    """
    # Request
    game_type = serializers.ChoiceField(
        choices=['BLITZ', 'RAPID', 'CLASSICAL'],
        help_text="Type of game won"
    )

    # Response (read-only)
    success = serializers.BooleanField(read_only=True)
    coins_earned = serializers.IntegerField(read_only=True)
    total_coins = serializers.IntegerField(read_only=True)
    message = serializers.CharField(read_only=True)


class UserCoinStatsSerializer(serializers.Serializer):
    """
    Comprehensive user coin statistics.
    Aggregates data from multiple sources for dashboard.
    """
    total_coins = serializers.IntegerField()
    daily_coins_earned = serializers.IntegerField()
    daily_ads_watched = serializers.IntegerField()
    current_streak = serializers.IntegerField()
    max_streak = serializers.IntegerField()
    last_ad_watched = serializers.DateTimeField(allow_null=True)
    last_daily_claim = serializers.DateField(allow_null=True)
    today_claimed = serializers.BooleanField()
    total_earned_from_ads = serializers.IntegerField()
    total_earned_from_games = serializers.IntegerField()
    total_spent = serializers.IntegerField()
    recent_transactions = serializers.ListField(
        child=serializers.DictField(),
        read_only=True
    )


class TransactionHistorySerializer(serializers.ModelSerializer):
    """
    Paginated transaction history with filters.
    """
    transaction_type_display = serializers.CharField(
        source='get_transaction_type_display',
        read_only=True
    )

    class Meta:
        model = CoinTransaction
        fields = [
            'id',
            'amount',
            'transaction_type',
            'transaction_type_display',
            'description',
            'balance_after',
            'created_at'
        ]
        read_only_fields = fields


class BulkTransactionSerializer(serializers.Serializer):
    """
    Serializer for bulk transaction operations.
    Used for admin operations like bonus distributions.
    """
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="List of user IDs to reward"
    )
    amount = serializers.IntegerField(
        min_value=1,
        help_text="Coins per user"
    )
    reason = serializers.CharField(
        max_length=255,
        help_text="Reason for distribution"
    )

    def validate_user_ids(self, value):
        """Validate user IDs exist."""
        non_existent = []
        for user_id in value:
            if not User.objects.filter(id=user_id).exists():
                non_existent.append(user_id)

        if non_existent:
            raise serializers.ValidationError(
                f"Users not found: {non_existent}"
            )
        return value


# ==================== PAYMENT SERIALIZERS ====================


class PaymentPackageSerializer(serializers.ModelSerializer):
    """Serialize coin purchase packages."""
    final_price = serializers.DecimalField(
        source='final_price',
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    coins_per_rupee = serializers.DecimalField(
        source='coins_per_rupee',
        max_digits=10,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = PaymentPackage
        fields = [
            'id',
            'package_name',
            'coins',
            'price_npr',
            'discount_percent',
            'final_price',
            'coins_per_rupee',
            'badge',
            'is_active',
        ]
        read_only_fields = ['id', 'final_price', 'coins_per_rupee']


class InitiatePaymentSerializer(serializers.Serializer):
    """
    Request serializer for initiating a payment.
    """
    package_id = serializers.UUIDField(
        help_text="ID of coin package to purchase"
    )
    return_url = serializers.URLField(
        help_text="URL to redirect after payment"
    )
    website_url = serializers.URLField(
        help_text="Website URL"
    )

    def validate_package_id(self, value):
        """Verify package exists and is active."""
        if not PaymentPackage.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Package not found or inactive")
        return value


class PaymentInitiationResponseSerializer(serializers.Serializer):
    """
    Response serializer for payment initiation.
    Contains payment URL and transaction ID.
    """
    success = serializers.BooleanField()
    pidx = serializers.CharField(help_text="Payment transaction ID from Khalti")
    payment_url = serializers.URLField(help_text="URL to redirect user for payment")
    transaction_id = serializers.UUIDField(help_text="Local transaction ID")


class VerifyPaymentSerializer(serializers.Serializer):
    """
    Request serializer for payment verification.
    """
    pidx = serializers.CharField(
        max_length=255,
        help_text="Khalti payment transaction ID"
    )


class PaymentVerificationResponseSerializer(serializers.Serializer):
    """
    Response serializer for payment verification.
    Shows payment status and coin crediting result.
    """
    success = serializers.BooleanField()
    status = serializers.CharField()
    coins_credited = serializers.IntegerField()
    new_balance = serializers.IntegerField()
    transaction_id = serializers.CharField()
    message = serializers.CharField(required=False)


class PaymentTransactionSerializer(serializers.ModelSerializer):
    """
    Serialize complete payment transaction details.
    """
    package_name = serializers.CharField(
        source='package.package_name',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    payment_method_display = serializers.CharField(
        source='get_payment_method_display',
        read_only=True
    )

    class Meta:
        model = PaymentTransaction
        fields = [
            'id',
            'package_name',
            'amount_npr',
            'coins_purchased',
            'status',
            'status_display',
            'payment_method',
            'payment_method_display',
            'coins_credited',
            'created_at',
            'completed_at',
            'khalti_pidx',
        ]
        read_only_fields = fields


class PaymentHistorySerializer(serializers.ModelSerializer):
    """
    Serializer for payment transaction history.
    Includes package info and status.
    """
    package_name = serializers.CharField(
        source='package.package_name',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )

    class Meta:
        model = PaymentTransaction
        fields = [
            'id',
            'package_name',
            'coins_purchased',
            'amount_npr',
            'status',
            'status_display',
            'coins_credited',
            'created_at',
        ]
        read_only_fields = fields


class PaymentStatsSerializer(serializers.Serializer):
    """
    Serializer for user payment statistics.
    Aggregated metrics about coin purchases.
    """
    total_transactions = serializers.IntegerField()
    total_spent_npr = serializers.FloatField()
    total_coins_purchased = serializers.IntegerField()
    average_transaction = serializers.FloatField()


class KhaltiWebhookPayloadSerializer(serializers.Serializer):
    """
    Serializer for Khalti webhook payload validation.
    """
    pidx = serializers.CharField(help_text="Payment ID")
    transaction_id = serializers.CharField(required=False)
    status = serializers.CharField(required=False)
    amount = serializers.IntegerField(required=False)


class LeaderboardSerializer(serializers.Serializer):
    """
    Leaderboard entry with user stats.
    """
    rank = serializers.IntegerField()
    username = serializers.CharField()
    user_id = serializers.IntegerField()
    total_coins = serializers.IntegerField()
    current_streak = serializers.IntegerField()
    max_streak = serializers.IntegerField()
    total_earned_from_ads = serializers.IntegerField()
    total_earned_from_games = serializers.IntegerField()


class ErrorResponseSerializer(serializers.Serializer):
    """
    Standard error response format.
    Used for consistent error handling across API.
    """
    success = serializers.BooleanField(default=False)
    error = serializers.CharField()
    code = serializers.CharField(required=False)
    details = serializers.DictField(required=False)
