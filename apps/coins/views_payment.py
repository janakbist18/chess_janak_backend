"""
Django REST Framework views for payment gateway integration.
Implements Khalti payment endpoints for coin purchases.
"""
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.throttling import UserRateThrottle
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import JsonResponse

from .models import PaymentPackage, PaymentTransaction, PaymentStatus
from .serializers import (
    PaymentPackageSerializer,
    InitiatePaymentSerializer,
    PaymentInitiationResponseSerializer,
    VerifyPaymentSerializer,
    PaymentVerificationResponseSerializer,
    PaymentTransactionSerializer,
    PaymentHistorySerializer,
    PaymentStatsSerializer,
)
from .services.payment_processor import PaymentProcessor

User = get_user_model()
logger = logging.getLogger(__name__)


class PaymentThrottle(UserRateThrottle):
    """Throttle for payment initiation (2 per minute per user)."""
    scope = 'payment_initiate'
    rate = '2/min'


class PaymentPagination(PageNumberPagination):
    """Pagination for payment history."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class PaymentViewSet(viewsets.ViewSet):
    """
    ViewSet for payment gateway operations.
    Handles coin package retrieval, payment initiation, verification, and history.
    """

    def get_client_ip(self, request):
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def get_user_agent(self, request):
        """Extract user agent from request."""
        return request.META.get('HTTP_USER_AGENT', '')

    @action(
        detail=False,
        methods=['GET'],
        permission_classes=[]  # Public endpoint
    )
    def packages(self, request):
        """
        GET /api/payments/packages/

        Get all available coin purchase packages.
        Returns list of active packages with prices and coin amounts.

        Response:
        [
            {
                "id": "uuid",
                "package_name": "Starter Pack",
                "coins": 100,
                "price_npr": 100,
                "discount_percent": 0,
                "final_price": "100.00",
                "coins_per_rupee": 1.0,
                "badge": ""
            }
        ]
        """
        try:
            processor = PaymentProcessor()
            packages = processor.get_active_packages()
            serializer = PaymentPackageSerializer(packages, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error fetching packages: {str(e)}")
            return Response(
                {
                    "success": False,
                    "error": "Failed to fetch packages",
                    "code": "PACKAGES_ERROR"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(
        detail=False,
        methods=['POST'],
        throttle_classes=[PaymentThrottle],
        permission_classes=[]  # Available to authenticated users
    )
    def initiate(self, request):
        """
        POST /api/payments/initiate/

        Initiate a coin purchase payment.
        Returns Khalti payment URL and transaction ID.

        Request Body:
        {
            "package_id": "uuid",
            "return_url": "https://app.example.com/payment/return",
            "website_url": "https://example.com"
        }

        Response:
        {
            "success": true,
            "pidx": "khalti_transaction_id",
            "payment_url": "https://khalti.com/...",
            "transaction_id": "local_transaction_uuid"
        }

        Status Codes:
        - 200: Payment initiated successfully
        - 400: Invalid request or package not found
        - 500: Server error
        """
        serializer = InitiatePaymentSerializer(data=request.data)
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
            package_id = serializer.validated_data['package_id']
            return_url = serializer.validated_data['return_url']
            website_url = serializer.validated_data['website_url']

            # Get or create user (support both authenticated and device_id based users)
            user = request.user if request.user.is_authenticated else None

            if not user:
                return Response(
                    {
                        "success": False,
                        "error": "Authentication required",
                        "code": "AUTH_REQUIRED"
                    },
                    status=status.HTTP_401_UNAUTHORIZED
                )

            ip_address = self.get_client_ip(request)
            user_agent = self.get_user_agent(request)

            processor = PaymentProcessor()
            success, result, error = processor.initiate_payment(
                user=user,
                package_id=str(package_id),
                return_url=return_url,
                website_url=website_url,
                ip_address=ip_address,
                user_agent=user_agent,
            )

            if not success:
                return Response(
                    {
                        "success": False,
                        "error": error,
                        "code": "INITIATION_ERROR"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get the transaction ID
            try:
                payment_txn = PaymentTransaction.objects.get(
                    khalti_pidx=result['pidx']
                )
                transaction_id = str(payment_txn.id)
            except PaymentTransaction.DoesNotExist:
                transaction_id = "unknown"

            return Response(
                {
                    "success": True,
                    "pidx": result['pidx'],
                    "payment_url": result['payment_url'],
                    "transaction_id": transaction_id
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"Error initiating payment: {str(e)}")
            return Response(
                {
                    "success": False,
                    "error": "Failed to initiate payment",
                    "code": "SYSTEM_ERROR"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(
        detail=False,
        methods=['GET'],
        permission_classes=[]
    )
    def verify(self, request):
        """
        GET /api/payments/verify/

        Verify a payment and credit coins to user.
        Called after user completes payment with Khalti.

        Query Parameters:
        - pidx: Khalti payment transaction ID (required)

        Response:
        {
            "success": true,
            "status": "completed",
            "coins_credited": 100,
            "new_balance": 150,
            "transaction_id": "transaction_uuid"
        }

        Status Codes:
        - 200: Payment verified and coins credited
        - 400: Payment verification failed
        - 404: Transaction not found
        - 500: Server error
        """
        pidx = request.query_params.get('pidx')
        if not pidx:
            return Response(
                {
                    "success": False,
                    "error": "Missing pidx parameter",
                    "code": "MISSING_PIDX"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            processor = PaymentProcessor()
            success, result, error = processor.verify_and_complete_payment(pidx)

            if not success:
                return Response(
                    {
                        "success": False,
                        "error": error,
                        "code": "VERIFICATION_FAILED"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response(
                {
                    "success": True,
                    "status": result.get("status", "completed"),
                    "coins_credited": result.get("coins_credited", 0),
                    "new_balance": result.get("new_balance", 0),
                    "transaction_id": result.get("transaction_id", "")
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"Error verifying payment: {str(e)}")
            return Response(
                {
                    "success": False,
                    "error": "Failed to verify payment",
                    "code": "SYSTEM_ERROR"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(
        detail=False,
        methods=['POST'],
        permission_classes=[]
    )
    def verify_post(self, request):
        """
        POST /api/payments/verify/

        Verify payment via POST request.
        Alternative to GET /api/payments/verify/?pidx=...

        Request Body:
        {
            "pidx": "khalti_transaction_id"
        }
        """
        serializer = VerifyPaymentSerializer(data=request.data)
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

        pidx = serializer.validated_data['pidx']

        try:
            processor = PaymentProcessor()
            success, result, error = processor.verify_and_complete_payment(pidx)

            if not success:
                return Response(
                    {
                        "success": False,
                        "error": error,
                        "code": "VERIFICATION_FAILED"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response(
                {
                    "success": True,
                    "status": result.get("status", "completed"),
                    "coins_credited": result.get("coins_credited", 0),
                    "new_balance": result.get("new_balance", 0),
                    "transaction_id": result.get("transaction_id", "")
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"Error verifying payment: {str(e)}")
            return Response(
                {
                    "success": False,
                    "error": "Failed to verify payment",
                    "code": "SYSTEM_ERROR"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(
        detail=False,
        methods=['POST'],
        permission_classes=[]
    )
    def webhook(self, request):
        """
        POST /api/payments/webhook/

        Khalti webhook endpoint for payment notifications.
        Receives payment completion notifications from Khalti.

        Request Body (from Khalti):
        {
            "pidx": "khalti_transaction_id",
            "transaction_id": "khalti_txn_id",
            "status": "Completed",
            "amount": 10000
        }

        This endpoint:
        - Validates webhook authenticity
        - Verifies payment with Khalti
        - Credits coins to user
        - Logs webhook data

        Response: {"success": true} with 200 status for webhook acknowledgment
        """
        try:
            webhook_data = request.data
            logger.info(f"Received Khalti webhook: {webhook_data}")

            processor = PaymentProcessor()
            success, error = processor.handle_webhook(webhook_data)

            if success:
                return Response({"success": True}, status=status.HTTP_200_OK)
            else:
                logger.warning(f"Webhook processing failed: {error}")
                return Response(
                    {"success": False, "error": error},
                    status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            # Return 200 anyway to acknowledge receipt and prevent Khalti retries
            return Response({"success": True}, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=['GET'],
        permission_classes=[]
    )
    def history(self, request):
        """
        GET /api/payments/history/

        Get user's payment transaction history.
        Paginated with filters.

        Query Parameters:
        - page: Page number (default: 1)
        - page_size: Items per page (default: 20, max: 100)
        - status: Filter by status (PENDING, COMPLETED, FAILED, REFUNDED)

        Response:
        {
            "count": 10,
            "next": "...",
            "previous": "...",
            "results": [
                {
                    "id": "uuid",
                    "package_name": "Popular Pack",
                    "coins_purchased": 500,
                    "amount_npr": "450.00",
                    "status": "COMPLETED",
                    "coins_credited": true,
                    "created_at": "2024-01-15T10:30:00Z"
                }
            ]
        }
        """
        try:
            user = request.user
            if not user.is_authenticated:
                return Response(
                    {
                        "success": False,
                        "error": "Authentication required",
                        "code": "AUTH_REQUIRED"
                    },
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # Filter by status if provided
            queryset = PaymentTransaction.objects.filter(user=user).order_by("-created_at")
            status_filter = request.query_params.get('status')
            if status_filter:
                if status_filter in dict(PaymentStatus.choices):
                    queryset = queryset.filter(status=status_filter)

            # Paginate
            paginator = PaymentPagination()
            page = paginator.paginate_queryset(queryset, request)

            if page is not None:
                serializer = PaymentHistorySerializer(page, many=True)
                return paginator.get_paginated_response(serializer.data)

            serializer = PaymentHistorySerializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error retrieving payment history: {str(e)}")
            return Response(
                {
                    "success": False,
                    "error": "Failed to retrieve history",
                    "code": "HISTORY_ERROR"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(
        detail=False,
        methods=['GET'],
        permission_classes=[]
    )
    def stats(self, request):
        """
        GET /api/payments/stats/

        Get user's payment statistics.
        Shows total spending and coin purchasing metrics.

        Response:
        {
            "total_transactions": 5,
            "total_spent_npr": 2500.0,
            "total_coins_purchased": 2000,
            "average_transaction": 500.0
        }
        """
        try:
            user = request.user
            if not user.is_authenticated:
                return Response(
                    {
                        "success": False,
                        "error": "Authentication required",
                        "code": "AUTH_REQUIRED"
                    },
                    status=status.HTTP_401_UNAUTHORIZED
                )

            processor = PaymentProcessor()
            stats = processor.get_payment_stats(user)

            return Response(stats, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error retrieving payment stats: {str(e)}")
            return Response(
                {
                    "success": False,
                    "error": "Failed to retrieve statistics",
                    "code": "STATS_ERROR"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
