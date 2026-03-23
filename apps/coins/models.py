from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator
from enum import Enum
import uuid


class TransactionType(models.TextChoices):
    """Enum for coin transaction types."""
    AD_REWARD = "AD_REWARD", "Ad Reward"
    GAME_WIN = "GAME_WIN", "Game Win"
    DAILY_BONUS = "DAILY_BONUS", "Daily Bonus"
    PURCHASE = "PURCHASE", "Coin Purchase"
    SPENT = "SPENT", "Coins Spent"
    STREAK_BONUS = "STREAK_BONUS", "Streak Bonus"
    REFUND = "REFUND", "Refund"


class GameType(models.TextChoices):
    """Game types for win-based rewards."""
    BLITZ = "BLITZ", "Blitz"
    RAPID = "RAPID", "Rapid"
    CLASSICAL = "CLASSICAL", "Classical"


class UserCoin(models.Model):
    """
    Track user's coin balance and daily earning metrics.
    Contains denormalized data for performance optimization.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="coin_account")
    total_coins = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    daily_coins_earned = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    ads_watched_today = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    last_ad_watched = models.DateTimeField(null=True, blank=True)
    last_daily_claim = models.DateField(null=True, blank=True)

    # Streak tracking
    current_streak = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    max_streak = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    last_streak_date = models.DateField(null=True, blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-total_coins"]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["total_coins"]),
            models.Index(fields=["-updated_at"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.total_coins} coins"

    def reset_daily_stats(self):
        """Reset daily earning stats at midnight UTC."""
        self.daily_coins_earned = 0
        self.ads_watched_today = 0
        self.save(update_fields=["daily_coins_earned", "ads_watched_today"])

    def add_coins(self, amount, transaction_type, description=""):
        """
        Safely add coins to user account with transaction logging.

        Args:
            amount: Number of coins to add
            transaction_type: Type of transaction from TransactionType choices
            description: Optional description for the transaction

        Returns:
            CoinTransaction object
        """
        self.total_coins += amount
        self.daily_coins_earned += amount
        self.save(update_fields=["total_coins", "daily_coins_earned", "updated_at"])

        # Create transaction record
        transaction = CoinTransaction.objects.create(
            user=self.user,
            amount=amount,
            transaction_type=transaction_type,
            description=description,
            balance_after=self.total_coins
        )
        return transaction

    def deduct_coins(self, amount, transaction_type, description=""):
        """
        Safely deduct coins from user account with validation.

        Args:
            amount: Number of coins to deduct
            transaction_type: Type of transaction from TransactionType choices
            description: Optional description

        Returns:
            CoinTransaction object or None if insufficient coins
        """
        if self.total_coins < amount:
            return None

        self.total_coins -= amount
        self.save(update_fields=["total_coins", "updated_at"])

        transaction = CoinTransaction.objects.create(
            user=self.user,
            amount=-amount,
            transaction_type=transaction_type,
            description=description,
            balance_after=self.total_coins
        )
        return transaction


class CoinTransaction(models.Model):
    """
    Immutable transaction log for coin operations.
    Provides complete audit trail for coin economy.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="coin_transactions")
    amount = models.IntegerField()  # Can be negative for spending
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
        db_index=True
    )
    description = models.TextField(blank=True)
    balance_after = models.IntegerField(validators=[MinValueValidator(0)])

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    # For audit trail
    related_game_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="ID of related game if applicable"
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["transaction_type", "-created_at"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        sign = "+" if self.amount > 0 else ""
        return f"{self.user.username}: {sign}{self.amount} ({self.get_transaction_type_display()})"


class RewardAdConfig(models.Model):
    """
    Configuration for reward ad system.
    Singleton pattern - only one instance should exist.
    """
    # Ensure only one config instance
    id = models.OneToOneField('CoinConfig', on_delete=models.CASCADE, primary_key=True)

    ad_reward_amount = models.IntegerField(
        default=10,
        validators=[MinValueValidator(1)],
        help_text="Coins earned per ad watch"
    )
    daily_watch_limit = models.IntegerField(
        default=5,
        validators=[MinValueValidator(1)],
        help_text="Maximum ads a user can watch per day"
    )
    cooldown_minutes = models.IntegerField(
        default=5,
        validators=[MinValueValidator(1)],
        help_text="Minutes between consecutive ad watches"
    )

    # Game win rewards by type
    blitz_win_reward = models.IntegerField(
        default=15,
        validators=[MinValueValidator(1)],
        help_text="Coins for winning a blitz game"
    )
    rapid_win_reward = models.IntegerField(
        default=25,
        validators=[MinValueValidator(1)],
        help_text="Coins for winning a rapid game"
    )
    classical_win_reward = models.IntegerField(
        default=50,
        validators=[MinValueValidator(1)],
        help_text="Coins for winning a classical game"
    )

    # Daily reward system
    daily_bonus_amount = models.IntegerField(
        default=20,
        validators=[MinValueValidator(1)],
        help_text="Base coins for daily login"
    )
    streak_multiplier = models.FloatField(
        default=1.5,
        validators=[MinValueValidator(1.0)],
        help_text="Multiplier for streak bonus (multiplied by streak count)"
    )

    # Admin controls
    ads_enabled = models.BooleanField(
        default=True,
        help_text="Enable/disable reward ads globally"
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Reward Ad Configuration"
        verbose_name_plural = "Reward Ad Configuration"

    def __str__(self):
        return "Reward Ad Configuration"

    def get_win_reward(self, game_type):
        """Get reward amount for winning a specific game type."""
        rewards = {
            GameType.BLITZ: self.blitz_win_reward,
            GameType.RAPID: self.rapid_win_reward,
            GameType.CLASSICAL: self.classical_win_reward,
        }
        return rewards.get(game_type, self.blitz_win_reward)


class CoinConfig(models.Model):
    """
    Global coin system configuration (singleton pattern).
    """
    id = models.OneToOneField('self', on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        verbose_name = "Coin Configuration"
        verbose_name_plural = "Coin Configuration"

    def __str__(self):
        return "Global Coin Configuration"


class DailyReward(models.Model):
    """
    Track daily login rewards and streak information.
    One record per user per day.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="daily_rewards")
    date = models.DateField(db_index=True)  # Date of claim in UTC
    coins_claimed = models.IntegerField(validators=[MinValueValidator(0)])
    streak_days = models.IntegerField(help_text="Streak count on this day")
    streak_bonus_applied = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Additional coins from streak multiplication"
    )

    # Metadata
    claimed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "date")
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["user", "-date"]),
            models.Index(fields=["-date"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.date} (Streak: {self.streak_days})"


class AdWatchLog(models.Model):
    """
    Detailed log of ad watches for fraud detection and analytics.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ad_watches")
    watched_at = models.DateTimeField(auto_now_add=True, db_index=True)

    ad_network = models.CharField(
        max_length=50,
        blank=True,
        help_text="Ad network provider (e.g., Google AdMob)"
    )
    ad_id = models.CharField(max_length=255, blank=True)
    reward_claimed = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    # Fraud detection
    suspicious = models.BooleanField(
        default=False,
        help_text="Flag for manual review"
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-watched_at"]
        indexes = [
            models.Index(fields=["user", "-watched_at"]),
            models.Index(fields=["-watched_at"]),
            models.Index(fields=["reward_claimed"]),
            models.Index(fields=["suspicious"]),
        ]

    def __str__(self):
        return f"{self.user.username} watched ad at {self.watched_at}"


class PaymentStatus(models.TextChoices):
    """Status choices for payment transactions."""
    PENDING = "PENDING", "Pending"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"
    REFUNDED = "REFUNDED", "Refunded"
    EXPIRED = "EXPIRED", "Expired"


class PaymentMethod(models.TextChoices):
    """Payment method choices."""
    KHALTI = "KHALTI", "Khalti"
    ESEWA = "ESEWA", "eSewa"
    BANK_TRANSFER = "BANK_TRANSFER", "Bank Transfer"


class PaymentPackage(models.Model):
    """
    Coin purchase packages.
    Admin-managed pricing and coin bundles.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    package_name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Name of the coin package"
    )
    coins = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Number of coins in this package"
    )
    price_npr = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Price in NPR currency"
    )
    discount_percent = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Discount percentage (0-100)"
    )
    badge = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Badge label (e.g., 'Popular', 'Best Value')"
    )

    # Metadata
    is_active = models.BooleanField(
        default=True,
        help_text="Deactivate package to hide from users"
    )
    display_order = models.IntegerField(
        default=0,
        help_text="Order in which packages appear to users"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "-created_at"]
        indexes = [
            models.Index(fields=["is_active", "display_order"]),
        ]

    def __str__(self):
        return f"{self.package_name} - {self.coins} coins @ NPR {self.price_npr}"

    @property
    def final_price(self):
        """Calculate final price after discount."""
        discount_amount = (self.price_npr * self.discount_percent) / 100
        return self.price_npr - discount_amount

    @property
    def coins_per_rupee(self):
        """Calculate coin value efficiency."""
        if self.final_price == 0:
            return 0
        return self.coins / float(self.final_price)


class PaymentTransaction(models.Model):
    """
    Khalti payment transaction records.
    Immutable log for payment operations and coin crediting.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payment_transactions"
    )
    package = models.ForeignKey(
        PaymentPackage,
        on_delete=models.PROTECT,
        related_name="transactions"
    )

    # Payment details
    amount_npr = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Amount paid in NPR"
    )
    coins_purchased = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Number of coins purchased"
    )

    # Khalti transaction tracking
    khalti_pidx = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Khalti payment transaction ID"
    )
    khalti_transaction_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Khalti transaction reference ID"
    )

    # Payment status
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        db_index=True
    )
    payment_method = models.CharField(
        max_length=50,
        choices=PaymentMethod.choices,
        default=PaymentMethod.KHALTI
    )

    # Coin crediting
    coins_credited = models.BooleanField(
        default=False,
        help_text="Whether coins have been credited to user"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)

    # Webhook data for audit trail
    webhook_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Webhook payload from Khalti"
    )

    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["coins_credited"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.coins_purchased} coins (NPR {self.amount_npr}) - {self.status}"

    def mark_completed(self):
        """Mark payment as completed."""
        if self.status != PaymentStatus.COMPLETED:
            self.status = PaymentStatus.COMPLETED
            self.completed_at = timezone.now()
            self.save(update_fields=["status", "completed_at"])

    def mark_failed(self):
        """Mark payment as failed."""
        if self.status in [PaymentStatus.PENDING, PaymentStatus.EXPIRED]:
            self.status = PaymentStatus.FAILED
            self.save(update_fields=["status"])

    def credit_coins(self):
        """
        Credit coins to user and mark as credited.
        Safe to call multiple times - only credits once.

        Returns:
            tuple: (success: bool, transaction: CoinTransaction or None, error: str or None)
        """
        if self.coins_credited:
            return False, None, "Coins already credited for this transaction"

        try:
            # Get or create user coin account
            coin_account, _ = UserCoin.objects.get_or_create(user=self.user)

            # Add coins with atomic transaction
            coin_txn = coin_account.add_coins(
                amount=self.coins_purchased,
                transaction_type=TransactionType.PURCHASE,
                description=f"Purchased via {self.payment_method}: {self.package.package_name}"
            )

            # Mark as credited
            self.coins_credited = True
            self.save(update_fields=["coins_credited"])

            return True, coin_txn, None

        except Exception as e:
            return False, None, str(e)

class StripeCustomer(models.Model):
    device_id = models.CharField(max_length=255, unique=True)
    stripe_customer_id = models.CharField(max_length=255, unique=True)
    email = models.EmailField(null=True, blank=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    default_payment_method = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class StripePaymentIntent(models.Model):
    device_id = models.CharField(max_length=255)
    stripe_payment_intent_id = models.CharField(max_length=255, unique=True)
    stripe_customer_id = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # in USD
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=50)  # requires_payment_method, succeeded, etc.
    package_id = models.IntegerField()
    coins_to_credit = models.IntegerField()
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class PaymentPackageStripe(models.Model):
    name = models.CharField(max_length=100)
    coins = models.IntegerField()
    price_usd = models.DecimalField(max_digits=10, decimal_places=2)
    price_eur = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    price_gbp = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    discount_percentage = models.IntegerField(default=0)
    is_popular = models.BooleanField(default=False)
    stripe_price_id = models.CharField(max_length=255, null=True)  # for subscriptions
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

class StripeWebhookEvent(models.Model):
    event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

