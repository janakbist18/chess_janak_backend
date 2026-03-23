"""
Stripe payment admin panel configuration.
Provides Django admin interface for managing payments, packages, and webhooks.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum, Count
from .models import (
    StripeCustomer,
    StripePaymentIntent,
    PaymentPackageStripe,
    StripeWebhookEvent,
)


@admin.register(PaymentPackageStripe)
class PaymentPackageStripeAdmin(admin.ModelAdmin):
    """Manage coin purchase packages."""
    list_display = [
        'name', 'coins_display', 'pricing_disp', 'discount_percentage',
        'is_popular', 'is_active', 'created_at'
    ]
    list_editable = ['is_popular', 'is_active']
    list_filter = ['is_active', 'is_popular', 'created_at']
    search_fields = ['name']
    fieldsets = (
        ('Package Info', {
            'fields': ('name', 'coins', 'is_popular', 'is_active')
        }),
        ('Pricing (set in settings if using dynamic)', {
            'fields': ('price_usd', 'price_eur', 'price_gbp', 'discount_percentage'),
            'description': 'Consider using Django settings for price management'
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at']

    def coins_display(self, obj):
        return f"{obj.coins:,}"
    coins_display.short_description = "Coins"

    def pricing_disp(self, obj):
        prices = []
        if obj.price_usd:
            prices.append(f"${obj.price_usd:.2f}")
        if obj.price_eur:
            prices.append(f"€{obj.price_eur:.2f}")
        if obj.price_gbp:
            prices.append(f"£{obj.price_gbp:.2f}")
        return " | ".join(prices) if prices else "No pricing"
    pricing_disp.short_description = "Prices"


@admin.register(StripePaymentIntent)
class StripePaymentIntentAdmin(admin.ModelAdmin):
    """Monitor and manage payment intents."""
    list_display = [
        'stripe_payment_intent_id_short', 'status_badge', 'device_id',
        'amount_display', 'coins_to_credit', 'created_at', 'actions_col'
    ]
    list_filter = ['status', 'currency', 'created_at']
    search_fields = ['stripe_payment_intent_id', 'device_id']
    readonly_fields = [
        'stripe_payment_intent_id', 'stripe_customer_id', 'created_at',
        'updated_at', 'metadata'
    ]
    fieldsets = (
        ('Payment Intent', {
            'fields': ('stripe_payment_intent_id', 'stripe_customer_id', 'status')
        }),
        ('Transaction Details', {
            'fields': ('amount', 'currency', 'coins_to_credit', 'package_id')
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    def stripe_payment_intent_id_short(self, obj):
        return obj.stripe_payment_intent_id[:20] + "..."
    stripe_payment_intent_id_short.short_description = "Payment Intent ID"

    def status_badge(self, obj):
        colors = {
            'succeeded': '#28a745',
            'processing': '#ffc107',
            'requires_action': '#fd7e14',
            'requires_payment_method': '#17a2b8',
            'payment_failed': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; border-radius: 3px;">{}</span>',
            color, obj.status.upper()
        )
    status_badge.short_description = "Status"

    def amount_display(self, obj):
        return f"{obj.amount:.2f} {obj.currency.upper()}"
    amount_display.short_description = "Amount"

    def actions_col(self, obj):
        if obj.status == 'succeeded':
            return format_html('<span style="color: green;">✓ Completed</span>')
        elif obj.status == 'payment_failed':
            return format_html('<span style="color: red;">✗ Failed</span>')
        else:
            return format_html('<span style="color: orange;">⏳ Pending</span>')
    actions_col.short_description = "Action"

    def has_delete_permission(self, request):
        # Prevent accidental deletion of payment records
        return request.user.is_superuser


@admin.register(StripeCustomer)
class StripeCustomerAdmin(admin.ModelAdmin):
    """Manage Stripe customer records."""
    list_display = [
        'device_id', 'stripe_customer_id_short', 'email', 'name',
        'created_at', 'payment_count'
    ]
    list_filter = ['created_at']
    search_fields = ['device_id', 'stripe_customer_id', 'email', 'name']
    readonly_fields = ['stripe_customer_id', 'created_at', 'updated_at']
    fieldsets = (
        ('Stripe Customer', {
            'fields': ('device_id', 'stripe_customer_id')
        }),
        ('Customer Info', {
            'fields': ('email', 'name')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def stripe_customer_id_short(self, obj):
        if obj.stripe_customer_id:
            return obj.stripe_customer_id[:20] + "..."
        return "N/A"
    stripe_customer_id_short.short_description = "Stripe ID"

    def payment_count(self, obj):
        count = StripePaymentIntent.objects.filter(
            stripe_customer_id=obj.stripe_customer_id
        ).count()
        return count
    payment_count.short_description = "Payments"

    def has_delete_permission(self, request):
        return request.user.is_superuser


@admin.register(StripeWebhookEvent)
class StripeWebhookEventAdmin(admin.ModelAdmin):
    """Monitor Stripe webhook events."""
    list_display = [
        'event_id_short', 'event_type', 'processed_status', 'created_at'
    ]
    list_filter = ['event_type', 'processed', 'created_at']
    search_fields = ['event_id', 'event_type']
    readonly_fields = ['event_id', 'created_at', 'payload']
    fieldsets = (
        ('Webhook Event', {
            'fields': ('event_id', 'event_type', 'processed')
        }),
        ('Payload', {
            'fields': ('payload',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    def event_id_short(self, obj):
        return obj.event_id[:30] + "..."
    event_id_short.short_description = "Event ID"

    def processed_status(self, obj):
        if obj.processed:
            return format_html('<span style="color: green;">✓ Processed</span>')
        return format_html('<span style="color: orange;">⏳ Pending</span>')
    processed_status.short_description = "Processed"

    def has_delete_permission(self, request):
        # Keep webhook records for audit trail
        return False

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
