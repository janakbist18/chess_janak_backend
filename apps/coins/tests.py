"""
Unit tests for coin system.
Comprehensive test coverage for models, views, and utilities.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import timedelta

from .models import (
    UserCoin, CoinTransaction, RewardAdConfig, DailyReward,
    AdWatchLog, TransactionType, GameType, CoinConfig
)
from .utils import (
    CoinManager, AdWatchLimitException, AdCooldownException,
    DuplicateClaimException, InsufficientCoinsException
)

User = get_user_model()


class UserCoinModelTest(TestCase):
    """Test UserCoin model."""

    def setUp(self):
        """Create test user and coin account."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_create_coin_account(self):
        """Test coin account creation."""
        coin = CoinManager.get_user_coin_account(self.user)
        self.assertIsNotNone(coin)
        self.assertEqual(coin.user, self.user)
        self.assertEqual(coin.total_coins, 100)  # Starting bonus

    def test_add_coins(self):
        """Test adding coins to account."""
        coin = CoinManager.get_user_coin_account(self.user)
        initial = coin.total_coins

        coin.add_coins(50, TransactionType.AD_REWARD, "Test reward")

        coin.refresh_from_db()
        self.assertEqual(coin.total_coins, initial + 50)

    def test_deduct_coins(self):
        """Test deducting coins from account."""
        coin = CoinManager.get_user_coin_account(self.user)
        coin.total_coins = 100
        coin.save()

        txn = coin.deduct_coins(30, TransactionType.SPENT, "Test purchase")

        coin.refresh_from_db()
        self.assertEqual(coin.total_coins, 70)
        self.assertIsNotNone(txn)

    def test_reset_daily_stats(self):
        """Test resetting daily stats."""
        coin = CoinManager.get_user_coin_account(self.user)
        coin.daily_coins_earned = 50
        coin.ads_watched_today = 3
        coin.save()

        coin.reset_daily_stats()

        coin.refresh_from_db()
        self.assertEqual(coin.daily_coins_earned, 0)
        self.assertEqual(coin.ads_watched_today, 0)


class CoinManagerTest(TestCase):
    """Test CoinManager utility functions."""

    def setUp(self):
        """Set up test user and config."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create config
        config_obj = CoinConfig.objects.create()
        RewardAdConfig.objects.create(
            id=config_obj,
            ad_reward_amount=10,
            daily_watch_limit=5,
            cooldown_minutes=5
        )

    def test_get_user_coin_account(self):
        """Test getting user coin account."""
        coin = CoinManager.get_user_coin_account(self.user)
        self.assertEqual(coin.user, self.user)

    def test_add_coins(self):
        """Test add_coins utility."""
        CoinManager.add_coins(self.user, 50, TransactionType.AD_REWARD, "Test")

        coin = CoinManager.get_user_coin_account(self.user)
        self.assertTrue(coin.total_coins >= 50)

    def test_deduct_coins(self):
        """Test deduct_coins utility."""
        coin = CoinManager.get_user_coin_account(self.user)
        coin.total_coins = 100
        coin.save()

        CoinManager.deduct_coins(self.user, 30, TransactionType.SPENT, "Test")

        coin.refresh_from_db()
        self.assertEqual(coin.total_coins, 70)

    def test_insufficient_coins_exception(self):
        """Test insufficient coins exception."""
        coin = CoinManager.get_user_coin_account(self.user)
        coin.total_coins = 10
        coin.save()

        with self.assertRaises(InsufficientCoinsException):
            CoinManager.deduct_coins(self.user, 50, TransactionType.SPENT)

    def test_can_watch_ad(self):
        """Test checking ad watch eligibility."""
        result = CoinManager.can_watch_ad(self.user)

        self.assertIsNotNone(result)
        self.assertIn('can_watch', result)
        self.assertIn('cooldown_seconds', result)

    def test_ad_watch_limit(self):
        """Test daily ad watch limit."""
        coin = CoinManager.get_user_coin_account(self.user)
        coin.ads_watched_today = 5
        coin.save()

        with self.assertRaises(AdWatchLimitException):
            CoinManager.claim_ad_reward(self.user)

    def test_ad_cooldown(self):
        """Test ad cooldown period."""
        coin = CoinManager.get_user_coin_account(self.user)
        coin.last_ad_watched = timezone.now() - timedelta(minutes=2)
        coin.save()

        with self.assertRaises(AdCooldownException):
            CoinManager.claim_ad_reward(self.user)

    def test_claim_ad_reward_success(self):
        """Test successful ad reward claim."""
        result = CoinManager.claim_ad_reward(self.user)

        self.assertTrue(result['success'])
        self.assertGreater(result['coins_earned'], 0)

    def test_duplicate_daily_claim(self):
        """Test preventing duplicate daily claims."""
        # First claim
        CoinManager.claim_daily_reward(self.user)

        # Second claim same day
        with self.assertRaises(DuplicateClaimException):
            CoinManager.claim_daily_reward(self.user)

    def test_streak_calculation(self):
        """Test daily reward streak calculation."""
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)

        # Create yesterday's claim
        DailyReward.objects.create(
            user=self.user,
            date=yesterday,
            coins_claimed=20,
            streak_days=1,
            streak_bonus_applied=0
        )

        # Claim today
        result = CoinManager.claim_daily_reward(self.user)

        self.assertEqual(result['streak_count'], 2)

    def test_game_win_reward(self):
        """Test game win reward."""
        result = CoinManager.reward_game_win(self.user, GameType.BLITZ)

        self.assertTrue(result['success'])
        self.assertGreater(result['coins_earned'], 0)

    def test_spend_coins(self):
        """Test spending coins."""
        coin = CoinManager.get_user_coin_account(self.user)
        coin.total_coins = 100
        coin.save()

        CoinManager.spend_coins(self.user, 30, "hint")

        coin.refresh_from_db()
        self.assertEqual(coin.total_coins, 70)


class CoinTransactionTest(TestCase):
    """Test CoinTransaction model."""

    def setUp(self):
        """Create test user."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_create_transaction(self):
        """Test creating transaction."""
        txn = CoinTransaction.objects.create(
            user=self.user,
            amount=50,
            transaction_type=TransactionType.AD_REWARD,
            description="Test ad",
            balance_after=150
        )

        self.assertEqual(txn.user, self.user)
        self.assertEqual(txn.amount, 50)

    def test_transaction_ordering(self):
        """Test transactions are ordered by date."""
        txn1 = CoinTransaction.objects.create(
            user=self.user,
            amount=10,
            transaction_type=TransactionType.DAILY_BONUS,
            balance_after=110
        )
        txn2 = CoinTransaction.objects.create(
            user=self.user,
            amount=20,
            transaction_type=TransactionType.GAME_WIN,
            balance_after=130
        )

        txns = list(CoinTransaction.objects.filter(user=self.user))
        self.assertEqual(txns[0], txn2)  # Most recent first


class CoinAPITest(APITestCase):
    """Test coin system API endpoints."""

    def setUp(self):
        """Set up test user and authentication."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create JWT token
        refresh = RefreshToken.for_user(self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')

        # Create config
        config_obj = CoinConfig.objects.create()
        RewardAdConfig.objects.create(
            id=config_obj,
            ad_reward_amount=10,
            daily_watch_limit=5,
            cooldown_minutes=5
        )

    def test_get_balance(self):
        """Test GET /api/coins/balance/"""
        response = self.client.get('/api/coins/balance/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('total_coins', response.data)

    def test_claim_ad_reward(self):
        """Test POST /api/coins/claim-ad-reward/"""
        response = self.client.post('/api/coins/claim-ad-reward/')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])

    def test_can_watch_ad(self):
        """Test GET /api/coins/can-watch-ad/"""
        response = self.client.get('/api/coins/can-watch-ad/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('can_watch', response.data)

    def test_get_transactions(self):
        """Test GET /api/coins/transactions/"""
        response = self.client.get('/api/coins/transactions/')

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data['results'], list)

    def test_claim_daily_reward(self):
        """Test POST /api/coins/daily-reward/"""
        response = self.client.post('/api/coins/daily-reward/')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])

    def test_spend_coins(self):
        """Test POST /api/coins/spend/"""
        # First add coins
        coin = CoinManager.get_user_coin_account(self.user)
        coin.total_coins = 100
        coin.save()

        response = self.client.post('/api/coins/spend/', {
            'amount': 30,
            'reason': 'hint'
        })

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])

    def test_get_config(self):
        """Test GET /api/coins/config/"""
        response = self.client.get('/api/coins/config/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('ad_reward_amount', response.data)

    def test_get_stats(self):
        """Test GET /api/coins/stats/"""
        response = self.client.get('/api/coins/stats/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('total_coins', response.data)

    def test_authentication_required(self):
        """Test endpoints require authentication."""
        self.client.credentials()  # Remove credentials

        response = self.client.get('/api/coins/balance/')
        self.assertEqual(response.status_code, 401)
