"""
Stripe payment URL configuration.
Routes for payment initiation, webhook handling, and payment queries.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views_stripe import (
    StripePaymentViewSet,
    StripeWebhookView,
    get_stripe_packages,
    create_checkout_session,
    process_refund,
)

router = DefaultRouter()
router.register(r'stripe', StripePaymentViewSet, basename='stripe-payment')

stripe_patterns = [
    # ViewSet routes (from router)
    path('', include(router.urls)),

    # Webhook (CRITICAL: Must match Stripe dashboard configuration)
    path('webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),

    # Legacy/compatibility endpoints
    path('packages/', get_stripe_packages, name='stripe-packages'),
    path('checkout/', create_checkout_session, name='stripe-checkout'),
    path('refund/', process_refund, name='stripe-refund'),
]

urlpatterns = [
    path('stripe/', include(stripe_patterns)),
]
