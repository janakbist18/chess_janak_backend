"""
URL routing for coin system API endpoints.
All endpoints require JWT authentication.
"""
from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import CoinViewSet
from .views_payment import PaymentViewSet

app_name = 'coins'

router = DefaultRouter()
router.register(r'', CoinViewSet, basename='coins')
router.register(r'payments', PaymentViewSet, basename='payments')

urlpatterns = [
    # Coin Endpoints (routed via CoinViewSet)
    # GET  /api/coins/balance/              - Get user's coin balance
    # POST /api/coins/claim-ad-reward/      - Claim reward for watching ad
    # GET  /api/coins/can-watch-ad/         - Check if user can watch ad
    # GET  /api/coins/transactions/         - Get transaction history
    # POST /api/coins/daily-reward/         - Claim daily login bonus
    # POST /api/coins/spend/                - Spend coins
    # POST /api/coins/game-win/             - Reward for game win
    # GET  /api/coins/config/               - Get reward configuration
    # GET  /api/coins/stats/                - Get user coin statistics
    # GET  /api/coins/leaderboard/          - Get top coin holders (admin)

    # Payment Endpoints (routed via PaymentViewSet)
    # GET  /api/coins/payments/packages/    - Get coin packages
    # POST /api/coins/payments/initiate/    - Initiate payment
    # GET  /api/coins/payments/verify/      - Verify payment
    # POST /api/coins/payments/verify-post/ - Verify payment (POST)
    # POST /api/coins/payments/webhook/     - Khalti webhook
    # GET  /api/coins/payments/history/     - Get payment history
    # GET  /api/coins/payments/stats/       - Get payment statistics
]

urlpatterns += router.urls

from .views_stripe import (
    get_stripe_packages, create_checkout_session, create_payment_intent,
    payment_success, stripe_webhook, payment_history, process_refund
)

# Stripe Endpoints
urlpatterns += [
    path('stripe/packages/', get_stripe_packages, name='stripe-packages'),
    path('stripe/create-checkout-session/', create_checkout_session, name='stripe-create-checkout-session'),
    path('stripe/create-payment-intent/', create_payment_intent, name='stripe-create-payment-intent'),
    path('stripe/payment-success/<str:session_id>/', payment_success, name='stripe-payment-success'),
    path('stripe/webhook/', stripe_webhook, name='stripe-webhook'),
    path('stripe/payment-history/', payment_history, name='stripe-payment-history'),
    path('stripe/refund/', process_refund, name='stripe-refund'),
]
from .views_stripe import get_stripe_packages, create_checkout_session, create_payment_intent, payment_success, stripe_webhook, payment_history, process_refund
urlpatterns += [
    path('stripe/packages/', get_stripe_packages),
    path('stripe/create-checkout-session/', create_checkout_session),
    path('stripe/create-payment-intent/', create_payment_intent),
    path('stripe/payment-success/<str:session_id>/', payment_success),
    path('stripe/webhook/', stripe_webhook),
    path('stripe/payment-history/', payment_history),
    path('stripe/refund/', process_refund),
]
