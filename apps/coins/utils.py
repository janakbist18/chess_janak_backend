"""
Utility functions for coin system business logic.
Handles calculations, validations, and coin operations.
"""
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum
from .models import (
    UserCoin, CoinTransaction, TransactionType, RewardAdConfig,
    DailyReward, AdWatchLog, GameType
)
import logging

logger = logging.getLogger(__name__)


class CoinSystemException(Exception):
    """Base exception for coin system operations."""
    pass


class InsufficientCoinsException(CoinSystemException):
    """Raised when user doesn't have enough coins for an operation."""
    pass


class AdWatchLimitException(CoinSystemException):
    """Raised when user has exceeded daily ad watch limit."""
    pass


class AdCooldownException(CoinSystemException):
    """Raised when user tries to watch ad during cooldown period."""
    pass


class DuplicateClaimException(CoinSystemException):
    """Raised when user tries to claim reward twice."""
    pass


class CoinManager:
    """
    Central manager for all coin operations.
    Ensures atomic transactions and proper validation.
    """

    @staticmethod
    def get_user_coin_account(user):
        """
        Get or create user coin account.

        Args:
            user: User instance

        Returns:
            UserCoin instance
        """
        coin_account, created = UserCoin.objects.get_or_create(
            user=user,
            defaults={"total_coins": 100}  # Starting bonus
        )
        return coin_account

    @staticmethod
    def get_reward_config():
        """
        Get reward configuration (singleton).

        Returns:
            RewardAdConfig instance or None
        """
        try:
            return RewardAdConfig.objects.select_related('id').first()
        except Exception as e:
            logger.error(f"Error retrieving reward config: {e}")
            return None

    @staticmethod
    def add_coins(user, amount, transaction_type, description="", ip_address=None):
        """
        Add coins to user account with transaction logging.
        Thread-safe atomic operation.

        Args:
            user: User instance
            amount: Number of coins to add (must be positive)
            transaction_type: Type from TransactionType choices
            description: Transaction description
            ip_address: IP address for logging

        Returns:
            CoinTransaction instance

        Raises:
            CoinSystemException: For invalid operations
        """
        if amount <= 0:
            raise CoinSystemException("Amount must be positive")

        with transaction.atomic():
            coin_account = CoinManager.get_user_coin_account(user)
            txn = coin_account.add_coins(amount, transaction_type, description)

            # Log IP address
            if ip_address:
                txn.ip_address = ip_address
                txn.save(update_fields=["ip_address"])

            logger.info(f"Added {amount} coins to {user.username} ({transaction_type})")
            return txn

    @staticmethod
    def deduct_coins(user, amount, transaction_type, description="", ip_address=None):
        """
        Deduct coins from user account.
        Thread-safe atomic operation.

        Args:
            user: User instance
            amount: Number of coins to deduct (must be positive)
            transaction_type: Type from TransactionType choices
            description: Transaction description
            ip_address: IP address for logging

        Returns:
            CoinTransaction instance

        Raises:
            InsufficientCoinsException: If user has insufficient coins
            CoinSystemException: For invalid operations
        """
        if amount <= 0:
            raise CoinSystemException("Amount must be positive")

        with transaction.atomic():
            coin_account = CoinManager.get_user_coin_account(user)

            if coin_account.total_coins < amount:
                raise InsufficientCoinsException(
                    f"User has {coin_account.total_coins} coins, needs {amount}"
                )

            txn = coin_account.deduct_coins(amount, transaction_type, description)

            if ip_address:
                txn.ip_address = ip_address
                txn.save(update_fields=["ip_address"])

            logger.info(f"Deducted {amount} coins from {user.username} ({transaction_type})")
            return txn

    @staticmethod
    def claim_ad_reward(user, ip_address=None):
        """
        Claim reward for watching an ad.
        Includes validation for daily limit and cooldown.

        Args:
            user: User instance
            ip_address: IP address for logging

        Returns:
            dict with 'success', 'coins_earned', 'message', and 'remaining_today'

        Raises:
            AdWatchLimitException: If daily limit exceeded
            AdCooldownException: If in cooldown period
        """
        config = CoinManager.get_reward_config()
        if not config or not config.ads_enabled:
            raise CoinSystemException("Reward ads are currently disabled")

        with transaction.atomic():
            coin_account = CoinManager.get_user_coin_account(user)
            now = timezone.now()
            today = now.date()

            # Check daily limit
            if coin_account.ads_watched_today >= config.daily_watch_limit:
                remaining = 0
                raise AdWatchLimitException(
                    f"Daily ad limit of {config.daily_watch_limit} exceeded"
                )

            # Check cooldown period
            if coin_account.last_ad_watched:
                cooldown_end = coin_account.last_ad_watched + timedelta(
                    minutes=config.cooldown_minutes
                )
                if now < cooldown_end:
                    seconds_remaining = int((cooldown_end - now).total_seconds())
                    raise AdCooldownException(
                        f"Cooldown active. Try again in {seconds_remaining} seconds."
                    )

            # Award coins
            reward_amount = config.ad_reward_amount
            txn = coin_account.add_coins(
                reward_amount,
                TransactionType.AD_REWARD,
                "Reward for watching advertisement"
            )

            # Update ad watch tracking
            coin_account.last_ad_watched = now
            coin_account.ads_watched_today += 1
            coin_account.save(update_fields=["last_ad_watched", "ads_watched_today"])

            # Log ad watch
            ad_log = AdWatchLog.objects.create(
                user=user,
                reward_claimed=True,
                ip_address=ip_address
            )

            remaining_today = config.daily_watch_limit - coin_account.ads_watched_today

            logger.info(
                f"User {user.username} claimed ad reward. "
                f"Total coins: {coin_account.total_coins}, "
                f"Remaining today: {remaining_today}"
            )

            return {
                "success": True,
                "coins_earned": reward_amount,
                "total_coins": coin_account.total_coins,
                "remaining_today": remaining_today,
                "message": f"You earned {reward_amount} coins!"
            }

    @staticmethod
    def can_watch_ad(user):
        """
        Check if user can watch an ad (limit and cooldown).

        Args:
            user: User instance

        Returns:
            dict with 'can_watch', 'reason', 'cooldown_seconds', 'remaining_today'
        """
        config = CoinManager.get_reward_config()
        if not config or not config.ads_enabled:
            return {
                "can_watch": False,
                "reason": "Reward ads are currently disabled",
                "cooldown_seconds": 0,
                "remaining_today": 0
            }

        coin_account = CoinManager.get_user_coin_account(user)
        now = timezone.now()

        # Check daily limit
        if coin_account.ads_watched_today >= config.daily_watch_limit:
            return {
                "can_watch": False,
                "reason": "Daily ad limit exceeded",
                "remaining_today": 0,
                "next_reset": (now.replace(hour=0, minute=0, second=0) + timedelta(days=1)).isoformat()
            }

        # Check cooldown
        cooldown_seconds = 0
        if coin_account.last_ad_watched:
            cooldown_end = coin_account.last_ad_watched + timedelta(
                minutes=config.cooldown_minutes
            )
            if now < cooldown_end:
                cooldown_seconds = int((cooldown_end - now).total_seconds())

        return {
            "can_watch": cooldown_seconds == 0,
            "reason": "Ready to watch" if cooldown_seconds == 0 else f"Cooldown active",
            "cooldown_seconds": cooldown_seconds,
            "remaining_today": config.daily_watch_limit - coin_account.ads_watched_today,
            "reward_amount": config.ad_reward_amount
        }

    @staticmethod
    def claim_daily_reward(user, ip_address=None):
        """
        Claim daily login reward with streak multiplier.

        Args:
            user: User instance
            ip_address: IP address for logging

        Returns:
            dict with 'success', 'coins_earned', 'streak_count', 'total_coins'

        Raises:
            DuplicateClaimException: If already claimed today
        """
        config = CoinManager.get_reward_config()
        if not config:
            raise CoinSystemException("Reward configuration not found")

        with transaction.atomic():
            coin_account = CoinManager.get_user_coin_account(user)
            today = timezone.now().date()

            # Check if already claimed today
            existing_claim = DailyReward.objects.filter(
                user=user,
                date=today
            ).first()

            if existing_claim:
                raise DuplicateClaimException(
                    f"Daily reward already claimed on {today}"
                )

            # Calculate streak
            yesterday = today - timedelta(days=1)
            yesterday_claim = DailyReward.objects.filter(
                user=user,
                date=yesterday
            ).first()

            if yesterday_claim:
                current_streak = yesterday_claim.streak_days + 1
            else:
                current_streak = 1

            # Calculate reward with streak bonus
            base_reward = config.daily_bonus_amount
            streak_multiplier = min(current_streak, 10)  # Cap at 10x to prevent abuse
            streak_bonus = int(base_reward * (streak_multiplier - 1) * config.streak_multiplier * 0.1)
            total_reward = base_reward + streak_bonus

            # Award coins
            txn = coin_account.add_coins(
                total_reward,
                TransactionType.DAILY_BONUS,
                f"Daily login bonus (Streak: {current_streak})"
            )

            # Update streak tracking
            coin_account.current_streak = current_streak
            if current_streak > coin_account.max_streak:
                coin_account.max_streak = current_streak
            coin_account.last_streak_date = today
            coin_account.last_daily_claim = today
            coin_account.save(update_fields=[
                "current_streak", "max_streak", "last_streak_date",
                "last_daily_claim", "updated_at"
            ])

            # Record daily reward
            daily_reward = DailyReward.objects.create(
                user=user,
                date=today,
                coins_claimed=base_reward,
                streak_days=current_streak,
                streak_bonus_applied=streak_bonus
            )

            logger.info(
                f"Daily reward claimed by {user.username}. "
                f"Base: {base_reward}, Streak Bonus: {streak_bonus}, "
                f"Total: {total_reward}, Streak: {current_streak}"
            )

            return {
                "success": True,
                "coins_earned": total_reward,
                "base_reward": base_reward,
                "streak_bonus": streak_bonus,
                "streak_count": current_streak,
                "total_coins": coin_account.total_coins,
                "message": f"Daily reward claimed! +{total_reward} coins (Streak: {current_streak})"
            }

    @staticmethod
    def reward_game_win(user, game_type, ip_address=None):
        """
        Award coins for winning a game.

        Args:
            user: User instance
            game_type: Type of game (BLITZ, RAPID, CLASSICAL)
            ip_address: IP address for logging

        Returns:
            dict with 'success', 'coins_earned', 'total_coins'

        Raises:
            CoinSystemException: For invalid game type
        """
        config = CoinManager.get_reward_config()
        if not config:
            raise CoinSystemException("Reward configuration not found")

        # Get reward based on game type
        reward_amount = config.get_win_reward(game_type)

        with transaction.atomic():
            txn = CoinManager.add_coins(
                user,
                reward_amount,
                TransactionType.GAME_WIN,
                f"Won {game_type.lower()} game",
                ip_address
            )

            coin_account = CoinManager.get_user_coin_account(user)

            logger.info(
                f"{user.username} earned {reward_amount} coins for winning {game_type} game"
            )

            return {
                "success": True,
                "coins_earned": reward_amount,
                "total_coins": coin_account.total_coins,
                "game_type": game_type,
                "message": f"Victory! +{reward_amount} coins"
            }

    @staticmethod
    def spend_coins(user, amount, reason="", related_game_id=None, ip_address=None):
        """
        Spend coins with validation.

        Args:
            user: User instance
            amount: Coins to spend
            reason: Reason for spending (hint, theme, etc.)
            related_game_id: Optional related game ID
            ip_address: IP address for logging

        Returns:
            CoinTransaction instance

        Raises:
            InsufficientCoinsException: If insufficient balance
        """
        with transaction.atomic():
            txn = CoinManager.deduct_coins(
                user,
                amount,
                TransactionType.SPENT,
                f"Spent on {reason}",
                ip_address
            )

            if related_game_id:
                txn.related_game_id = related_game_id
                txn.save(update_fields=["related_game_id"])

            coin_account = CoinManager.get_user_coin_account(user)
            logger.info(f"{user.username} spent {amount} coins on {reason}")

            return txn

    @staticmethod
    def reset_daily_limits():
        """
        Reset daily ad watch counts and earnings for all users.
        Should be run daily via scheduled task (Celery beat).

        Returns:
            tuple of (updated_count, error_message)
        """
        try:
            updated_count = UserCoin.objects.all().update(
                daily_coins_earned=0,
                ads_watched_today=0
            )
            logger.info(f"Reset daily limits for {updated_count} users")
            return updated_count, None
        except Exception as e:
            error_msg = f"Error resetting daily limits: {str(e)}"
            logger.error(error_msg)
            return 0, error_msg

    @staticmethod
    def check_streak_expiration():
        """
        Check and reset streaks if user didn't claim yesterday.
        Should be run daily via scheduled task.

        Returns:
            tuple of (reset_count, error_message)
        """
        try:
            reset_count = 0
            today = timezone.now().date()
            yesterday = today - timedelta(days=1)

            # Find users with active streaks who didn't claim yesterday
            users_with_streaks = UserCoin.objects.filter(current_streak__gt=0)

            for coin_account in users_with_streaks:
                # Check if they claimed yesterday
                yesterday_claim = DailyReward.objects.filter(
                    user=coin_account.user,
                    date=yesterday
                ).exists()

                if not yesterday_claim:
                    # Streak broken
                    coin_account.current_streak = 0
                    coin_account.save(update_fields=["current_streak"])
                    reset_count += 1

            logger.info(f"Reset streaks for {reset_count} users due to missed daily claim")
            return reset_count, None
        except Exception as e:
            error_msg = f"Error checking streak expiration: {str(e)}"
            logger.error(error_msg)
            return 0, error_msg

    @staticmethod
    def get_transaction_history(user, limit=50, offset=0):
        """
        Get paginated transaction history for user.

        Args:
            user: User instance
            limit: Number of transactions per page
            offset: Starting position

        Returns:
            QuerySet of CoinTransaction
        """
        return CoinTransaction.objects.filter(user=user)[offset:offset+limit]

    @staticmethod
    def get_user_stats(user):
        """
        Get comprehensive coin stats for user.

        Args:
            user: User instance

        Returns:
            dict with various statistics
        """
        coin_account = CoinManager.get_user_coin_account(user)

        # Get recent transactions
        recent_txns = CoinTransaction.objects.filter(user=user)[:10]

        # Get daily reward info
        today = timezone.now().date()
        today_claim = DailyReward.objects.filter(
            user=user,
            date=today
        ).first()

        # Calculate statistics
        total_earned_ads = CoinTransaction.objects.filter(
            user=user,
            transaction_type=TransactionType.AD_REWARD
        ).aggregate(models.Sum('amount'))['amount__sum'] or 0

        total_earned_games = CoinTransaction.objects.filter(
            user=user,
            transaction_type=TransactionType.GAME_WIN
        ).aggregate(models.Sum('amount'))['amount__sum'] or 0

        total_spent = CoinTransaction.objects.filter(
            user=user,
            transaction_type=TransactionType.SPENT
        ).aggregate(models.Sum('amount'))['amount__sum'] or 0

        return {
            "total_coins": coin_account.total_coins,
            "daily_coins_earned": coin_account.daily_coins_earned,
            "daily_ads_watched": coin_account.ads_watched_today,
            "current_streak": coin_account.current_streak,
            "max_streak": coin_account.max_streak,
            "last_ad_watched": coin_account.last_ad_watched,
            "last_daily_claim": coin_account.last_daily_claim,
            "today_claimed": today_claim is not None,
            "total_earned_from_ads": total_earned_ads,
            "total_earned_from_games": total_earned_games,
            "total_spent": total_spent,
            "recent_transactions": [
                {
                    "type": t.get_transaction_type_display(),
                    "amount": t.amount,
                    "date": t.created_at.isoformat(),
                    "description": t.description
                }
                for t in recent_txns
            ]
        }
