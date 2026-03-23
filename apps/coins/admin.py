"""
Django admin interface for coin system.
Provides admin dashboard for managing coins, rewards, and configuration.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum
from .models import (
    UserCoin, CoinTransaction, RewardAdConfig, DailyReward,
    AdWatchLog, CoinConfig, TransactionType, PaymentPackage, PaymentTransaction, PaymentStatus
)
from .utils import CoinManager
import logging

logger = logging.getLogger(__name__)


@admin.register(UserCoin)
class UserCoinAdmin(admin.ModelAdmin):
    """Admin interface for user coin accounts."""

    list_display = (
        'user', 'total_coins_display', 'daily_coins_earned',
        'current_streak', 'last_ad_watched_display', 'updated_at'
    )
    list_filter = (
        'created_at', 'updated_at', 'current_streak',
        ('total_coins', admin.RelatedOnlyFieldListFilter)
    )
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('id', 'created_at', 'updated_at', 'stats_summary')

    fieldsets = (
        ('User', {
            'fields': ('id', 'user')
        }),
        ('Balance', {
            'fields': ('total_coins', 'daily_coins_earned', 'ads_watched_today')
        }),
        ('Ad Watching', {
            'fields': ('last_ad_watched',)
        }),
        ('Streak Information', {
            'fields': ('current_streak', 'max_streak', 'last_streak_date')
        }),
        ('Daily Tracking', {
            'fields': ('last_daily_claim',)
        }),
        ('Summary', {
            'fields': ('stats_summary',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def total_coins_display(self, obj):
        """Display total coins with color coding."""
        if obj.total_coins >= 1000:
            color = 'green'
        elif obj.total_coins >= 100:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.total_coins
        )
    total_coins_display.short_description = 'Total Coins'

    def last_ad_watched_display(self, obj):
        """Display last ad watch time."""
        if obj.last_ad_watched:
            return obj.last_ad_watched.strftime('%Y-%m-%d %H:%M')
        return '—'
    last_ad_watched_display.short_description = 'Last Ad Watched'

    def stats_summary(self, obj):
        """Display comprehensive stats summary."""
        txns = CoinTransaction.objects.filter(user=obj.user)
        stats = f"""
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td><strong>Total Transactions:</strong></td>
                <td>{txns.count()}</td>
            </tr>
            <tr>
                <td><strong>Ad Rewards Total:</strong></td>
                <td>{txns.filter(transaction_type='AD_REWARD').aggregate(Sum('amount'))['amount__sum'] or 0}</td>
            </tr>
            <tr>
                <td><strong>Game Win Rewards:</strong></td>
                <td>{txns.filter(transaction_type='GAME_WIN').aggregate(Sum('amount'))['amount__sum'] or 0}</td>
            </tr>
            <tr>
                <td><strong>Daily Bonuses:</strong></td>
                <td>{txns.filter(transaction_type='DAILY_BONUS').aggregate(Sum('amount'))['amount__sum'] or 0}</td>
            </tr>
            <tr>
                <td><strong>Total Spent:</strong></td>
                <td>{abs(txns.filter(transaction_type='SPENT').aggregate(Sum('amount'))['amount__sum'] or 0)}</td>
            </tr>
        </table>
        """
        return format_html(stats)
    stats_summary.short_description = 'Statistics Summary'

    def has_add_permission(self, request):
        """Prevent manual creation of coin accounts."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of coin accounts."""
        return False


@admin.register(CoinTransaction)
class CoinTransactionAdmin(admin.ModelAdmin):
    """Admin interface for transaction logs."""

    list_display = (
        'user', 'amount_display', 'transaction_type',
        'balance_after', 'created_at'
    )
    list_filter = (
        'transaction_type', 'created_at',
        ('amount', admin.AllValuesFieldListFilter)
    )
    search_fields = (
        'user__username', 'user__email', 'description',
        'related_game_id'
    )
    readonly_fields = (
        'id', 'user', 'amount', 'transaction_type', 'balance_after',
        'created_at', 'ip_address', 'description'
    )
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Transaction', {
            'fields': ('id', 'user', 'amount', 'transaction_type')
        }),
        ('Details', {
            'fields': ('description', 'balance_after', 'related_game_id')
        }),
        ('Audit', {
            'fields': ('created_at', 'ip_address')
        })
    )

    def amount_display(self, obj):
        """Display amount with sign color coding."""
        sign = '+' if obj.amount > 0 else ''
        color = 'green' if obj.amount > 0 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}{}</span>',
            color,
            sign,
            obj.amount
        )
    amount_display.short_description = 'Amount'

    def has_add_permission(self, request):
        """Prevent manual transaction creation."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of transaction records."""
        return False

    def has_change_permission(self, request, obj=None):
        """Prevent editing of transaction records."""
        return False


@admin.register(DailyReward)
class DailyRewardAdmin(admin.ModelAdmin):
    """Admin interface for daily reward tracking."""

    list_display = (
        'user', 'date', 'coins_claimed',
        'streak_bonus_applied', 'streak_days', 'claimed_at'
    )
    list_filter = ('date', 'streak_days', 'claimed_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('id', 'claimed_at', 'claimed_at')
    date_hierarchy = 'date'

    fieldsets = (
        ('User', {
            'fields': ('user', 'date')
        }),
        ('Rewards', {
            'fields': ('coins_claimed', 'streak_bonus_applied')
        }),
        ('Streak', {
            'fields': ('streak_days',)
        }),
        ('Metadata', {
            'fields': ('id', 'claimed_at')
        })
    )

    def has_add_permission(self, request):
        """Prevent manual daily reward creation."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of daily reward records."""
        return False


@admin.register(AdWatchLog)
class AdWatchLogAdmin(admin.ModelAdmin):
    """Admin interface for ad watch audit logs."""

    list_display = (
        'user', 'watched_at', 'ad_network', 'reward_claimed',
        'suspicious_display'
    )
    list_filter = (
        'watched_at', 'reward_claimed', 'suspicious', 'ad_network'
    )
    search_fields = (
        'user__username', 'user__email', 'ad_id', 'ip_address'
    )
    readonly_fields = (
        'id', 'watched_at', 'user', 'ad_id', 'ip_address', 'user_agent'
    )
    date_hierarchy = 'watched_at'

    fieldsets = (
        ('User & Timing', {
            'fields': ('user', 'watched_at', 'id')
        }),
        ('Ad Details', {
            'fields': ('ad_network', 'ad_id', 'reward_claimed')
        }),
        ('Network Info', {
            'fields': ('ip_address', 'user_agent')
        }),
        ('Fraud Detection', {
            'fields': ('suspicious', 'notes')
        })
    )

    actions = ['mark_suspicious', 'mark_not_suspicious']

    def suspicious_display(self, obj):
        """Display suspicious flag with color."""
        if obj.suspicious:
            return format_html(
                '<span style="color: red; font-weight: bold;">⚠ Yes</span>'
            )
        return format_html(
            '<span style="color: green;">No</span>'
        )
    suspicious_display.short_description = 'Suspicious'

    def mark_suspicious(self, request, queryset):
        """Mark selected ad watches as suspicious."""
        updated = queryset.update(suspicious=True)
        self.message_user(request, f'{updated} ad watches marked as suspicious')
    mark_suspicious.short_description = 'Mark selected as suspicious'

    def mark_not_suspicious(self, request, queryset):
        """Clear suspicious flag."""
        updated = queryset.update(suspicious=False)
        self.message_user(request, f'{updated} ad watches cleared')
    mark_not_suspicious.short_description = 'Clear suspicious flag'

    def has_add_permission(self, request):
        """Prevent manual ad log creation."""
        return False


@admin.register(RewardAdConfig)
class RewardAdConfigAdmin(admin.ModelAdmin):
    """Admin interface for reward configuration (singleton)."""

    list_display = ('config_status',)

    fieldsets = (
        ('Ad Rewards', {
            'fields': (
                'ad_reward_amount', 'daily_watch_limit', 'cooldown_minutes'
            )
        }),
        ('Game Win Rewards', {
            'fields': (
                'blitz_win_reward', 'rapid_win_reward', 'classical_win_reward'
            )
        }),
        ('Daily Login Rewards', {
            'fields': (
                'daily_bonus_amount', 'streak_multiplier'
            )
        }),
        ('System Control', {
            'fields': ('ads_enabled',)
        })
    )

    def config_status(self, obj):
        """Display configuration status."""
        status_icon = '✓' if obj.ads_enabled else '✗'
        color = 'green' if obj.ads_enabled else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} Reward Config</span>',
            color,
            status_icon
        )
    config_status.short_description = 'Reward Configuration'

    def has_add_permission(self, request):
        """Enforce singleton pattern - prevent adding multiple configs."""
        return RewardAdConfig.objects.count() == 0

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of configuration."""
        return False


class CoinAdminSite(admin.AdminSite):
    """Custom admin site for coin system with extended actions."""
    site_header = "Chess Janak Coin System Administration"
    site_title = "Coin Admin"
    index_title = "Coin System Management"

    def index(self, request, extra_context=None):
        """Custom admin index with coin system statistics."""
        extra_context = extra_context or {}

        # Add statistics
        try:
            total_users_with_coins = UserCoin.objects.count()
            total_coins_in_system = UserCoin.objects.aggregate(Sum('total_coins'))['total_coins__sum'] or 0
            total_transactions = CoinTransaction.objects.count()

            extra_context.update({
                'total_users_with_coins': total_users_with_coins,
                'total_coins_in_system': total_coins_in_system,
                'total_transactions': total_transactions,
            })
        except Exception as e:
            logger.error(f"Error gathering admin statistics: {str(e)}")

        return super().index(request, extra_context)


# Register with custom admin site (optional - comment out to use default)
# admin.site = CoinAdminSite()


# ==================== PAYMENT MODELS ADMIN ====================


@admin.register(PaymentPackage)
class PaymentPackageAdmin(admin.ModelAdmin):
    """Admin interface for coin purchase packages."""

    list_display = (
        'package_name', 'coins', 'price_display', 'final_price_display',
        'discount_display', 'coins_per_rupee_display', 'is_active_display'
    )
    list_filter = ('is_active', 'created_at')
    search_fields = ('package_name',)
    readonly_fields = ('id', 'created_at', 'updated_at', 'coins_per_rupee')

    fieldsets = (
        ('Package Details', {
            'fields': ('id', 'package_name', 'coins', 'badge')
        }),
        ('Pricing', {
            'fields': ('price_npr', 'discount_percent', 'final_price_display')
        }),
        ('Analytics', {
            'fields': ('coins_per_rupee',)
        }),
        ('Settings', {
            'fields': ('is_active', 'display_order')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def price_display(self, obj):
        """Display original price in NPR."""
        return f"NPR {obj.price_npr}"
    price_display.short_description = 'Original Price'

    def final_price_display(self, obj):
        """Display final price after discount."""
        return f"NPR {obj.final_price}"
    final_price_display.short_description = 'Final Price'

    def discount_display(self, obj):
        """Display discount percentage."""
        if obj.discount_percent > 0:
            return format_html(
                '<span style="color: green; font-weight: bold;">{:d}% OFF</span>',
                obj.discount_percent
            )
        return '—'
    discount_display.short_description = 'Discount'

    def coins_per_rupee_display(self, obj):
        """Display coin to rupee ratio."""
        return f"{obj.coins_per_rupee:.2f} coins/NPR"
    coins_per_rupee_display.short_description = 'Value'

    def is_active_display(self, obj):
        """Display active status with color."""
        if obj.is_active:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Active</span>'
            )
        return format_html(
            '<span style="color: red;">✗ Inactive</span>'
        )
    is_active_display.short_description = 'Status'


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    """Admin interface for payment transactions."""

    list_display = (
        'user', 'package_display', 'amount_display', 'coins_display',
        'status_display', 'coins_credited_display', 'created_at'
    )
    list_filter = (
        'status', 'coins_credited', 'created_at', 'payment_method'
    )
    search_fields = (
        'user__username', 'user__email', 'khalti_pidx', 'khalti_transaction_id'
    )
    readonly_fields = (
        'id', 'user', 'khalti_pidx', 'khalti_transaction_id',
        'created_at', 'completed_at', 'refunded_at', 'webhook_data'
    )
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Transaction Info', {
            'fields': ('id', 'user', 'package')
        }),
        ('Payment Details', {
            'fields': (
                'amount_npr', 'coins_purchased', 'payment_method',
                'khalti_pidx', 'khalti_transaction_id'
            )
        }),
        ('Status', {
            'fields': ('status', 'coins_credited')
        }),
        ('Timeline', {
            'fields': ('created_at', 'completed_at', 'refunded_at')
        }),
        ('Metadata', {
            'fields': ('ip_address', 'user_agent', 'notes', 'webhook_data'),
            'classes': ('collapse',)
        })
    )

    actions = ['mark_completed', 'mark_failed', 'mark_refunded']

    def package_display(self, obj):
        """Display package name with coins."""
        return f"{obj.package.package_name} ({obj.coins_purchased} coins)"
    package_display.short_description = 'Package'

    def amount_display(self, obj):
        """Display amount in NPR."""
        return f"NPR {obj.amount_npr}"
    amount_display.short_description = 'Amount'

    def coins_display(self, obj):
        """Display coins in color."""
        return format_html(
            '<span style="color: gold; font-weight: bold;">{} coins</span>',
            obj.coins_purchased
        )
    coins_display.short_description = 'Coins'

    def status_display(self, obj):
        """Display status with color coding."""
        colors = {
            PaymentStatus.PENDING: 'orange',
            PaymentStatus.COMPLETED: 'green',
            PaymentStatus.FAILED: 'red',
            PaymentStatus.REFUNDED: 'blue',
            PaymentStatus.EXPIRED: 'gray',
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'

    def coins_credited_display(self, obj):
        """Display if coins have been credited."""
        if obj.coins_credited:
            return format_html(
                '<span style="color: green;">✓ Credited</span>'
            )
        return format_html(
            '<span style="color: orange;">⏳ Pending</span>'
        )
    coins_credited_display.short_description = 'Coins Credited'

    def mark_completed(self, request, queryset):
        """Mark selected transactions as completed."""
        for txn in queryset:
            if txn.status != PaymentStatus.COMPLETED:
                txn.mark_completed()
                # Attempt to credit coins if not already credited
                if not txn.coins_credited:
                    txn.credit_coins()
        self.message_user(request, f'{queryset.count()} transaction(s) marked as completed')
    mark_completed.short_description = 'Mark as Completed'

    def mark_failed(self, request, queryset):
        """Mark selected transactions as failed."""
        updated = queryset.exclude(status=PaymentStatus.COMPLETED).update(status=PaymentStatus.FAILED)
        self.message_user(request, f'{updated} transaction(s) marked as failed')
    mark_failed.short_description = 'Mark as Failed'

    def mark_refunded(self, request, queryset):
        """Mark selected transactions as refunded."""
        updated = queryset.exclude(status=PaymentStatus.REFUNDED).update(status=PaymentStatus.REFUNDED)
        self.message_user(request, f'{updated} transaction(s) marked as refunded')
    mark_refunded.short_description = 'Mark as Refunded'

    def has_add_permission(self, request):
        """Prevent manual transaction creation."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of payment transactions."""
        return False
