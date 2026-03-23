"""
Django REST Framework views for coin system API endpoints.
Implements all coin management endpoints with device_id based authentication.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.throttling import UserRateThrottle
from django.db import transaction, models
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

from .models import (
    UserCoin, CoinTransaction, RewardAdConfig, DailyReward,
    AdWatchLog, TransactionType, GameType
)
from .serializers import (
    CoinBalanceSerializer, CoinTransactionSerializer, RewardAdConfigSerializer,
    ClaimAdRewardSerializer, CanWatchAdSerializer, ClaimDailyRewardSerializer,
    SpendCoinsSerializer, GameWinRewardSerializer, UserCoinStatsSerializer,
    TransactionHistorySerializer, ErrorResponseSerializer, LeaderboardSerializer
)
from .permissions import (
    IsOwnerOrAdmin, CanClaimRewards, CanSpendCoins, IsAdminUser,
    CanManageRewardConfig
)
from .utils import (
    CoinManager,
    AdWatchLimitException,
    AdCooldownException,
    DuplicateClaimException,
    InsufficientCoinsException,
    CoinSystemException
)
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class CoinTransactionPagination(PageNumberPagination):
    """Pagination for transaction history."""
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100


class AdRewardThrottle(UserRateThrottle):
    """Throttle for ad reward claims (5 per minute per user)."""
    scope = 'ad_reward'
    rate = '5/min'


class DailyRewardThrottle(UserRateThrottle):
    """Throttle for daily reward claims (1 per minute per user)."""
    scope = 'daily_reward'
    rate = '1/min'


class SpendCoinsThrottle(UserRateThrottle):
    """Throttle for coin spending (10 per minute per user)."""
    scope = 'spend_coins'
    rate = '10/min'


class CoinViewSet(viewsets.ViewSet):
    """
    ViewSet for all coin-related operations.
    Handles balance, transactions, rewards, and spending.
    All endpoints work with device_id based anonymous authentication.
    """
    # Device ID middleware handles authentication automatically
    # No explicit authentication required

    def get_client_ip(self, request):
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    @action(
        detail=False,
        methods=['GET']
    )
    def balance(self, request):
        """
        GET /api/coins/balance/

        Get user's current coin balance and statistics.
        Includes daily tracking and streak information.
        """
        try:
            coin_account = CoinManager.get_user_coin_account(request.user)
            serializer = CoinBalanceSerializer(coin_account)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error getting balance for {request.user}: {str(e)}")
            return Response(
                {
                    "success": False,
                    "error": "Failed to retrieve balance",
                    "code": "BALANCE_ERROR"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(
        detail=False,
        methods=['POST'],
        throttle_classes=[AdRewardThrottle]
    )
    def claim_ad_reward(self, request):
        """
        POST /api/coins/claim-ad-reward/

        Claim reward for watching an advertisement.

        Validations:
        - Daily watch limit enforced (default: 5 ads/day)
        - Cooldown between ads enforced (default: 5 minutes)
        - Atomic transaction ensures consistency

        Returns:
        - 200: Reward successfully claimed with amount and remaining watch count
        - 400: Limit exceeded or cooldown active
        - 500: Server error
        """
        try:
            ip_address = self.get_client_ip(request)
            result = CoinManager.claim_ad_reward(request.user, ip_address)

            serializer = ClaimAdRewardSerializer(result)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except AdWatchLimitException as e:
            logger.warning(f"Ad watch limit exceeded for {request.user}: {str(e)}")
            return Response(
                {
                    "success": False,
                    "error": str(e),
                    "code": "DAILY_LIMIT_EXCEEDED"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        except AdCooldownException as e:
            logger.warning(f"Ad cooldown active for {request.user}: {str(e)}")
            return Response(
                {
                    "success": False,
                    "error": str(e),
                    "code": "COOLDOWN_ACTIVE"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        except CoinSystemException as e:
            logger.error(f"Coin system error for {request.user}: {str(e)}")
            return Response(
                {
                    "success": False,
                    "error": str(e),
                    "code": "SYSTEM_ERROR"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            logger.error(f"Unexpected error claiming ad reward for {request.user}: {str(e)}")
            return Response(
                {
                    "success": False,
                    "error": "Failed to claim reward",
                    "code": "CLAIM_ERROR"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(
        detail=False,
        methods=['GET']
    )
    def can_watch_ad(self, request):
        """
        GET /api/coins/can-watch-ad/

        Check if user can watch an ad without claiming.
        Provides details about cooldown and remaining daily limit.

        Response includes:
        - can_watch: Boolean indicating if ad is available
        - cooldown_seconds: Seconds remaining in cooldown
        - remaining_today: Ads remaining after today's limit
        - reward_amount: Coins that will be earned
        """
        try:
            result = CoinManager.can_watch_ad(request.user)
            serializer = CanWatchAdSerializer(result)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error checking ad eligibility for {request.user}: {str(e)}")
            return Response(
                {
                    "success": False,
                    "error": "Failed to check ad eligibility",
                    "code": "CHECK_ERROR"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(
        detail=False,
        methods=['GET']
    )
    def transactions(self, request):
        """
        GET /api/coins/transactions/

        Get paginated transaction history for current user.

        Query Parameters:
        - page: Page number (default: 1)
        - page_size: Items per page (default: 50, max: 100)
        - type: Filter by transaction type (optional)

        Response includes transaction list with amounts, types, and timestamps.
        """
        try:
            # Get transactions for the user
            queryset = CoinTransaction.objects.filter(user=request.user)

            # Optional filter by transaction type
            txn_type = request.query_params.get('type')
            if txn_type:
                if txn_type in dict(TransactionType.choices):
                    queryset = queryset.filter(transaction_type=txn_type)

            # Paginate
            page = self.paginate_queryset(queryset, request)
            if page is not None:
                serializer = TransactionHistorySerializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = TransactionHistorySerializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error retrieving transactions for {request.user}: {str(e)}")
            return Response(
                {
                    "success": False,
                    "error": "Failed to retrieve transactions",
                    "code": "TRANSACTION_ERROR"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(
        detail=False,
        methods=['POST'],
        throttle_classes=[DailyRewardThrottle]
    )
    def daily_reward(self, request):
        """
        POST /api/coins/daily-reward/

        Claim daily login bonus with streak multiplier.

        Business Logic:
        - Can only be claimed once per day (UTC)
        - Streak increases for consecutive daily claims
        - Streak multiplier increases reward amount (up to 10x)
        - Streak resets if user misses a day

        Returns:
        - 200: Reward claimed with base amount, streak bonus, and new streak count
        - 400: Already claimed today
        - 500: Server error
        """
        try:
            ip_address = self.get_client_ip(request)
            result = CoinManager.claim_daily_reward(request.user, ip_address)

            serializer = ClaimDailyRewardSerializer(result)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except DuplicateClaimException as e:
            logger.warning(f"Duplicate daily claim for {request.user}: {str(e)}")
            return Response(
                {
                    "success": False,
                    "error": str(e),
                    "code": "ALREADY_CLAIMED"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        except CoinSystemException as e:
            logger.error(f"Coin system error for {request.user}: {str(e)}")
            return Response(
                {
                    "success": False,
                    "error": str(e),
                    "code": "SYSTEM_ERROR"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            logger.error(f"Unexpected error claiming daily reward for {request.user}: {str(e)}")
            return Response(
                {
                    "success": False,
                    "error": "Failed to claim daily reward",
                    "code": "CLAIM_ERROR"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(
        detail=False,
        methods=['POST'],
        throttle_classes=[SpendCoinsThrottle]
    )
    def spend(self, request):
        """
        POST /api/coins/spend/

        Spend coins for in-game purchases (hints, themes, etc).

        Request Body:
        {
            "amount": 50,
            "reason": "hint",
            "related_game_id": "game_123" (optional)
        }

        Validations:
        - User must have sufficient coins
        - Amount must be positive
        - Reason must be valid category

        Returns:
        - 200: Coins successfully deducted
        - 400: Validation error or insufficient coins
        - 500: Server error
        """
        serializer = SpendCoinsSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "error": "Invalid request",
                    "code": "VALIDATION_ERROR",
                    "details": serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            amount = serializer.validated_data['amount']
            reason = serializer.validated_data['reason']
            game_id = serializer.validated_data.get('related_game_id')
            ip_address = self.get_client_ip(request)

            txn = CoinManager.spend_coins(
                request.user,
                amount,
                reason=reason,
                related_game_id=game_id,
                ip_address=ip_address
            )

            coin_account = CoinManager.get_user_coin_account(request.user)

            return Response(
                {
                    "success": True,
                    "coins_spent": amount,
                    "remaining_coins": coin_account.total_coins,
                    "transaction_id": str(txn.id),
                    "message": f"Spent {amount} coins on {reason}"
                },
                status=status.HTTP_200_OK
            )

        except InsufficientCoinsException as e:
            logger.warning(f"Insufficient coins for {request.user}: {str(e)}")
            return Response(
                {
                    "success": False,
                    "error": str(e),
                    "code": "INSUFFICIENT_COINS"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        except CoinSystemException as e:
            logger.error(f"Coin system error for {request.user}: {str(e)}")
            return Response(
                {
                    "success": False,
                    "error": str(e),
                    "code": "SYSTEM_ERROR"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            logger.error(f"Unexpected error spending coins for {request.user}: {str(e)}")
            return Response(
                {
                    "success": False,
                    "error": "Failed to spend coins",
                    "code": "SPEND_ERROR"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(
        detail=False,
        methods=['POST']
    )
    def game_win(self, request):
        """
        POST /api/coins/game-win/

        Reward coins for winning a game.
        Normally called by gameplay/signals after game completion.

        Request Body:
        {
            "game_type": "BLITZ" | "RAPID" | "CLASSICAL"
        }

        Reward amounts are configurable via RewardAdConfig:
        - Blitz: 15 coins
        - Rapid: 25 coins
        - Classical: 50 coins
        """
        serializer = GameWinRewardSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "error": "Invalid request",
                    "code": "VALIDATION_ERROR",
                    "details": serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            game_type = serializer.validated_data['game_type']
            ip_address = self.get_client_ip(request)

            result = CoinManager.reward_game_win(request.user, game_type, ip_address)

            return Response(result, status=status.HTTP_200_OK)

        except CoinSystemException as e:
            logger.error(f"Coin system error for {request.user}: {str(e)}")
            return Response(
                {
                    "success": False,
                    "error": str(e),
                    "code": "SYSTEM_ERROR"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            logger.error(f"Unexpected error rewarding game win for {request.user}: {str(e)}")
            return Response(
                {
                    "success": False,
                    "error": "Failed to reward game win",
                    "code": "REWARD_ERROR"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(
        detail=False,
        methods=['GET']
    )
    def config(self, request):
        """
        GET /api/coins/config/

        Get current reward configuration.
        Public endpoint - available to all users.
        Displays reward amounts, limits, and system settings.
        """
        try:
            config = CoinManager.get_reward_config()
            if not config:
                return Response(
                    {
                        "success": False,
                        "error": "Configuration not found",
                        "code": "CONFIG_ERROR"
                    },
                    status=status.HTTP_404_NOT_FOUND
                )

            serializer = RewardAdConfigSerializer(config)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error retrieving config: {str(e)}")
            return Response(
                {
                    "success": False,
                    "error": "Failed to retrieve configuration",
                    "code": "CONFIG_ERROR"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(
        detail=False,
        methods=['GET']
    )
    def stats(self, request):
        """
        GET /api/coins/stats/

        Get comprehensive user coin statistics.
        Includes total coins, streaks, and aggregated transaction data.
        """
        try:
            stats = CoinManager.get_user_stats(request.user)
            serializer = UserCoinStatsSerializer(stats)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error retrieving stats for {request.user}: {str(e)}")
            return Response(
                {
                    "success": False,
                    "error": "Failed to retrieve statistics",
                    "code": "STATS_ERROR"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(
        detail=False,
        methods=['GET'],
        permission_classes=[IsAdminUser]
    )
    def leaderboard(self, request):
        """
        GET /api/coins/leaderboard/

        Get top coin holders leaderboard.
        Admin only - can add pagination and filtering in future.

        Query Parameters:
        - limit: Number of top users (default: 100)
        """
        try:
            limit = int(request.query_params.get('limit', 100))
            limit = min(limit, 1000)  # Max 1000 for performance

            top_users = UserCoin.objects.all().order_by('-total_coins')[:limit]

            leaderboard_data = [
                {
                    "rank": idx + 1,
                    "username": coin.user.username,
                    "user_id": coin.user.id,
                    "total_coins": coin.total_coins,
                    "current_streak": coin.current_streak,
                    "max_streak": coin.max_streak,
                    "total_earned_from_ads": CoinTransaction.objects.filter(
                        user=coin.user,
                        transaction_type=TransactionType.AD_REWARD
                    ).aggregate(models.Sum('amount'))['amount__sum'] or 0,
                    "total_earned_from_games": CoinTransaction.objects.filter(
                        user=coin.user,
                        transaction_type=TransactionType.GAME_WIN
                    ).aggregate(models.Sum('amount'))['amount__sum'] or 0,
                }
                for idx, coin in enumerate(top_users)
            ]

            return Response(leaderboard_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error retrieving leaderboard: {str(e)}")
            return Response(
                {
                    "success": False,
                    "error": "Failed to retrieve leaderboard",
                    "code": "LEADERBOARD_ERROR"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
