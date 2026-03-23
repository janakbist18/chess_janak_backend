"""
Django signals for coin system.
Auto-triggers coin rewards on game wins and other events.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


@receiver(post_save, sender=User)
def create_user_coin_account(sender, instance, created, **kwargs):
    """
    Signal handler: Create coin account when new user is created.
    Automatically initializes coin system for new users.
    """
    if created:
        try:
            from .models import UserCoin
            coin_account = UserCoin.objects.create(
                user=instance,
                total_coins=100  # Welcome bonus
            )
            logger.info(f"Created coin account for new user {instance.username}")
        except Exception as e:
            logger.error(f"Error creating coin account for {instance.username}: {str(e)}")


def reward_game_win(user, game_type, winner=True):
    """
    Reward user for game win.

    Called by chessplay app when game completes.
    This is a helper function that can be imported and called directly.

    Args:
        user: User instance
        game_type: Game type (BLITZ, RAPID, CLASSICAL)
        winner: Boolean indicating if user won
    """
    if not winner:
        return None

    try:
        from .utils import CoinManager
        result = CoinManager.reward_game_win(user, game_type)
        logger.info(f"Rewarded {result['coins_earned']} coins to {user.username} for {game_type} win")
        return result
    except Exception as e:
        logger.error(f"Error rewarding game win for {user.username}: {str(e)}")
        return None


def handle_daily_reset():
    """
    Handle daily reset of coin limits and streak checks.

    Called by Celery beat task daily at midnight UTC.
    Resets:
    - Daily ad watch counts
    - Daily coin earning tallies
    - Checks and resets expired streaks
    """
    try:
        from .utils import CoinManager

        # Reset daily limits
        updated, error = CoinManager.reset_daily_limits()
        if error:
            logger.error(f"Daily reset error: {error}")
        else:
            logger.info(f"Daily limits reset for {updated} users")

        # Check streak expiration
        reset_count, error = CoinManager.check_streak_expiration()
        if error:
            logger.error(f"Streak expiration error: {error}")
        else:
            logger.info(f"Streaks reset for {reset_count} users")

    except Exception as e:
        logger.error(f"Unexpected error in daily reset: {str(e)}")
