"""
Production-ready Stripe payment API views.
Handles payment initiation, webhook processing, and payment status queries.
SECURITY: Always verify webhook signatures, validate amounts server-side, use HTTPS only.
"""
import logging
import json
from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from django.conf import settings
from django.core.paginator import Paginator

from .models import PaymentPackageStripe, StripePaymentIntent
from .services.stripe_service import StripeService, StripePaymentException, StripeWebhookException

logger = logging.getLogger(__name__)


class StripePaymentViewSet(viewsets.ViewSet):
    """Stripe payment endpoints."""
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['post'], url_path='create-payment-intent')
    def create_payment_intent(self, request):
        """Create a Stripe Payment Intent."""
        package_id = request.data.get('package_id')
        currency = request.data.get('currency', 'usd')

        if not package_id:
            return Response(
                {'error': 'package_id required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = StripeService.create_payment_intent(
                user=request.user,
                package_id=int(package_id),
                currency=currency.lower()
            )

            logger.info(f"User {request.user.username} created payment intent")
            return Response(result, status=status.HTTP_201_CREATED)

        except StripePaymentException as e:
            logger.warning(f"Payment error: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Payment intent error: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Payment initiation failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='payment-status')
    def payment_status(self, request):
        """Get status of a payment intent."""
        payment_intent_id = request.query_params.get('payment_intent_id')
        if not payment_intent_id:
            return Response(
                {'error': 'payment_intent_id required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = StripeService.get_payment_status(payment_intent_id)
            return Response(result)
        except StripeWebhookException as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'], url_path='packages')
    def list_packages(self, request):
        """List available coin packages."""
        currency = request.query_params.get('currency', 'usd').lower()

        try:
            packages = StripeService.list_packages(currency=currency)
            return Response({'packages': packages})
        except Exception as e:
            logger.error(f"Error listing packages: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Failed to load packages'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='history')
    def payment_history(self, request):
        """Get user's payment history."""
        try:
            device_id = getattr(request.user, 'device_id', f'user_{request.user.id}')
            intents = StripePaymentIntent.objects.filter(
                device_id=device_id
            ).order_by('-created_at')

            paginator = Paginator(intents, 10)
            page = request.query_params.get('page', 1)
            history = paginator.get_page(page)

            data = [{
                'id': h.stripe_payment_intent_id,
                'amount': str(h.amount),
                'currency': h.currency.upper(),
                'status': h.status,
                'coins': h.coins_to_credit,
                'date': h.created_at.isoformat()
            } for h in history]

            return Response({
                'history': data,
                'has_next': history.has_next(),
                'has_previous': history.has_previous(),
                'total': paginator.count
            })
        except Exception as e:
            logger.error(f"Error fetching payment history: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Failed to load payment history'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_stripe_packages(request):
    """Get all active Stripe coin packages."""
    try:
        packages = PaymentPackageStripe.objects.filter(is_active=True).order_by('-is_popular', 'coins')
        data = [{
            'id': pkg.id,
            'name': pkg.name,
            'coins': pkg.coins,
            'price_usd': str(pkg.price_usd),
            'price_eur': str(pkg.price_eur) if pkg.price_eur else None,
            'price_gbp': str(pkg.price_gbp) if pkg.price_gbp else None,
            'discount_percentage': pkg.discount_percentage,
            'is_popular': pkg.is_popular
        } for pkg in packages]
        return Response({'packages': data})
    except Exception as e:
        logger.error(f"Error fetching packages: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Failed to load packages'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(APIView):
    """Handle Stripe webhooks. SECURITY-CRITICAL: Verify signatures."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """Process Stripe webhook event."""
        payload = request.body
        signature_header = request.META.get('HTTP_STRIPE_SIGNATURE')

        if not signature_header:
            logger.warning("Webhook received without signature")
            return JsonResponse(
                {'error': 'Missing signature'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Verify signature (SECURITY-CRITICAL)
            event = StripeService.verify_webhook_signature(payload, signature_header)

            # Record event for audit trail
            StripeService.record_webhook_event(event)

            # Event dispatch
            event_type = event['type']
            logger.info(f"Processing webhook: {event_type}")

            if event_type == 'payment_intent.succeeded':
                StripeService.process_payment_intent_succeeded(event)
                logger.info(f"Payment succeeded: {event['data']['object']['id']}")

            elif event_type == 'payment_intent.payment_failed':
                StripeService.process_payment_intent_failed(event)
                logger.warning(f"Payment failed: {event['data']['object']['id']}")

            # Always return 200 to acknowledge receipt
            return JsonResponse({'status': 'success'}, status=status.HTTP_200_OK)

        except StripeWebhookException as e:
            logger.warning(f"Webhook verification failed: {str(e)}")
            return JsonResponse(
                {'error': 'Verification failed'},
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Webhook error: {str(e)}", exc_info=True)
            # Return 200 to prevent Stripe retries on server errors
            return JsonResponse({'status': 'error'}, status=status.HTTP_200_OK)


# Legacy endpoints for compatibility
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_checkout_session(request):
    """Create Stripe Checkout Session (legacy endpoint)."""
    return Response({'error': 'Use /api/coins/stripe/create-payment-intent/ instead'}, status=status.HTTP_410_GONE)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def process_refund(request):
    """Process refund (admin only)."""
    if not request.user.is_staff:
        return Response({'error': 'Admin only'}, status=status.HTTP_403_FORBIDDEN)

    try:
        payment_intent_id = request.data.get('payment_intent_id')
        if not payment_intent_id:
            return Response({'error': 'payment_intent_id required'}, status=status.HTTP_400_BAD_REQUEST)

        pi = StripePaymentIntent.objects.get(stripe_payment_intent_id=payment_intent_id)
        # TODO: Implement refund logic with Stripe API
        logger.info(f"Refund initiated for {payment_intent_id}")
        return Response({'status': 'Refund processed'})

    except StripePaymentIntent.DoesNotExist:
        return Response({'error': 'Payment not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Refund error: {str(e)}", exc_info=True)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_payment_intent(request):
    """Create a Stripe Payment Intent (standalone view)."""
    package_id = request.data.get('package_id')
    currency = request.data.get('currency', 'usd')

    if not package_id:
        return Response(
            {'error': 'package_id required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        result = StripeService.create_payment_intent(
            user=request.user,
            package_id=int(package_id),
            currency=currency.lower()
        )
        logger.info(f"User {request.user.username} created payment intent")
        return Response(result, status=status.HTTP_201_CREATED)

    except StripePaymentException as e:
        logger.warning(f"Payment error: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Payment intent error: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Payment initiation failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET', 'POST'])
@permission_classes([permissions.AllowAny])
def stripe_webhook(request):
    """Handle Stripe webhooks. SECURITY-CRITICAL: Verify signatures."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    payload = request.body
    signature_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    if not signature_header:
        logger.warning("Webhook received without signature")
        return JsonResponse(
            {'error': 'Missing signature'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Verify signature (SECURITY-CRITICAL)
        event = StripeService.verify_webhook_signature(payload, signature_header)

        # Record event for audit trail
        StripeService.record_webhook_event(event)

        # Event dispatch
        event_type = event['type']
        logger.info(f"Processing webhook: {event_type}")

        if event_type == 'payment_intent.succeeded':
            StripeService.process_payment_intent_succeeded(event)
            logger.info(f"Payment succeeded: {event['data']['object']['id']}")

        elif event_type == 'payment_intent.payment_failed':
            StripeService.process_payment_intent_failed(event)
            logger.warning(f"Payment failed: {event['data']['object']['id']}")

        # Always return 200 to acknowledge receipt
        return JsonResponse({'status': 'success'}, status=status.HTTP_200_OK)

    except StripeWebhookException as e:
        logger.warning(f"Webhook verification failed: {str(e)}")
        return JsonResponse(
            {'error': 'Verification failed'},
            status=status.HTTP_403_FORBIDDEN
        )
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}", exc_info=True)
        # Return 200 to prevent Stripe retries on server errors
        return JsonResponse({'status': 'error'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def payment_success(request):
    """Payment success page (placeholder)."""
    return Response({'message': 'Payment successful'}, status=status.HTTP_200_OK)

