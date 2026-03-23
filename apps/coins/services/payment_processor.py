"""
Payment processing logic for coin purchases.
Handles coin crediting, transaction management, and payment workflows.
"""
import logging
from typing import Dict, Optional, Tuple
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model

from ..models import (
    PaymentTransaction,
    PaymentPackage,
    PaymentStatus,
    UserCoin,
    TransactionType,
    CoinTransaction,
)
from .khalti_service import KhaltiService

logger = logging.getLogger(__name__)
User = get_user_model()


class PaymentProcessingError(Exception):
    """Base exception for payment processing errors."""
    pass


class InsufficientPackageError(PaymentProcessingError):
    """Package not found or inactive."""
    pass


class PaymentVerificationError(PaymentProcessingError):
    """Payment verification failed."""
    pass


class CoinCreditingError(PaymentProcessingError):
    """Error crediting coins to user."""
    pass


class PaymentProcessor:
    """
    Process payment transactions and credit coins.
    Ensures atomic operations and prevent double-crediting.
    """

    def __init__(self):
        """Initialize payment processor."""
        self.khalti = KhaltiService()

    def get_active_packages(self) -> list:
        """
        Get all active payment packages.

        Returns:
            list: List of active PaymentPackage objects
        """
        return PaymentPackage.objects.filter(is_active=True).order_by("display_order")

    def get_package_by_id(self, package_id: str) -> Optional[PaymentPackage]:
        """
        Get package by ID.

        Args:
            package_id: UUID of package

        Returns:
            PaymentPackage or None if not found/inactive
        """
        try:
            return PaymentPackage.objects.get(
                id=package_id,
                is_active=True
            )
        except PaymentPackage.DoesNotExist:
            return None

    @transaction.atomic
    def initiate_payment(
        self,
        user: User,
        package_id: str,
        return_url: str,
        website_url: str,
        ip_address: str = "",
        user_agent: str = "",
    ) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Initiate a coin purchase payment.

        Args:
            user: User making the purchase
            package_id: ID of package to purchase
            return_url: URL to redirect after payment
            website_url: Application website URL
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            tuple: (
                success: bool,
                result: dict with pidx and payment_url,
                error: str
            )
        """
        try:
            # Validate package
            package = self.get_package_by_id(package_id)
            if not package:
                return False, None, "Package not found or inactive"

            # Create transaction record in pending state
            payment_txn = PaymentTransaction.objects.create(
                user=user,
                package=package,
                amount_npr=package.price_npr,
                coins_purchased=package.coins,
                khalti_pidx="temp_" + str(user.id),  # Temporary, will be updated
                status=PaymentStatus.PENDING,
                ip_address=ip_address,
                user_agent=user_agent,
            )

            # Prepare Khalti payment
            amount_paisa = self.khalti.convert_npr_to_paisa(float(package.final_price))
            order_id = f"CHESS-{payment_txn.id}"

            success, result, error = self.khalti.initiate_payment(
                amount_paisa=amount_paisa,
                purchase_order_id=order_id,
                purchase_order_name=package.package_name,
                return_url=return_url,
                website_url=website_url,
                customer_name=user.name or user.username,
                customer_email=user.email or "",
                customer_phone="",
            )

            if not success:
                payment_txn.status = PaymentStatus.FAILED
                payment_txn.notes = error
                payment_txn.save()
                return False, None, error

            # Update transaction with pidx
            pidx = result["pidx"]
            payment_txn.khalti_pidx = pidx
            payment_txn.save(update_fields=["khalti_pidx"])

            logger.info(
                f"Payment initiated for user {user.id}: "
                f"{package.coins} coins @ NPR {package.final_price} (pidx: {pidx})"
            )

            return True, result, None

        except PaymentPackage.DoesNotExist:
            return False, None, "Package not found"
        except Exception as e:
            error_msg = f"Error initiating payment: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg

    @transaction.atomic
    def verify_and_complete_payment(
        self,
        pidx: str,
    ) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Verify payment with Khalti and credit coins.

        Args:
            pidx: Khalti payment transaction ID

        Returns:
            tuple: (
                success: bool,
                result: dict with transaction details,
                error: str
            )
        """
        try:
            # Find transaction by pidx
            payment_txn = PaymentTransaction.objects.get(khalti_pidx=pidx)

            # Avoid double verification
            if payment_txn.status == PaymentStatus.COMPLETED:
                return True, {
                    "status": "already_completed",
                    "coins_credited": payment_txn.coins_purchased,
                    "transaction_id": str(payment_txn.id),
                }, None

            # Verify with Khalti
            success, result, error = self.khalti.verify_payment(pidx)
            if not success:
                payment_txn.status = PaymentStatus.FAILED
                payment_txn.notes = error
                payment_txn.save()
                return False, None, error

            # Check payment status
            khalti_status = result.get("status", "").lower()
            if khalti_status != "completed":
                payment_txn.status = PaymentStatus.FAILED if khalti_status == "failed" else PaymentStatus.PENDING
                payment_txn.notes = f"Khalti status: {khalti_status}"
                payment_txn.save()
                return False, None, f"Payment status: {khalti_status}"

            # Verify amount
            khalti_amount = result.get("amount", 0)
            expected_amount = self.khalti.convert_npr_to_paisa(float(payment_txn.amount_npr))
            if khalti_amount != expected_amount:
                payment_txn.status = PaymentStatus.FAILED
                payment_txn.notes = f"Amount mismatch: expected {expected_amount}, got {khalti_amount}"
                payment_txn.save()
                return False, None, "Payment amount mismatch"

            # Store webhook data
            payment_txn.khalti_transaction_id = result.get("transaction_id")
            payment_txn.webhook_data = result.get("raw_response", {})

            # Credit coins to user
            credit_success, coin_txn, credit_error = self._credit_coins_to_user(payment_txn)
            if not credit_success:
                payment_txn.status = PaymentStatus.COMPLETED  # Payment succeeded but coin credit failed
                payment_txn.notes = f"Coin credit error: {credit_error}"
                payment_txn.save()
                return False, None, credit_error

            # Mark payment as completed
            payment_txn.mark_completed()

            logger.info(
                f"Payment completed for user {payment_txn.user.id}: "
                f"{payment_txn.coins_purchased} coins credited"
            )

            return True, {
                "status": "completed",
                "coins_credited": payment_txn.coins_purchased,
                "new_balance": payment_txn.user.coin_account.total_coins,
                "transaction_id": str(payment_txn.id),
            }, None

        except PaymentTransaction.DoesNotExist:
            return False, None, "Payment transaction not found"
        except Exception as e:
            error_msg = f"Error verifying payment: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg

    @staticmethod
    def _credit_coins_to_user(
        payment_txn: PaymentTransaction,
    ) -> Tuple[bool, Optional[CoinTransaction], Optional[str]]:
        """
        Credit coins to user's account.

        Args:
            payment_txn: PaymentTransaction instance

        Returns:
            tuple: (
                success: bool,
                coin_txn: CoinTransaction or None,
                error: str or None
            )
        """
        try:
            success, coin_txn, error = payment_txn.credit_coins()
            if not success:
                return False, None, error

            return True, coin_txn, None

        except Exception as e:
            error_msg = f"Error crediting coins: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg

    @transaction.atomic
    def handle_webhook(self, webhook_data: Dict) -> Tuple[bool, Optional[str]]:
        """
        Handle payment webhook from Khalti.

        Args:
            webhook_data: Webhook payload from Khalti

        Returns:
            tuple: (success: bool, error: str or None)
        """
        try:
            pidx = webhook_data.get("pidx")
            if not pidx:
                return False, "Missing pidx in webhook"

            # Verify and complete payment
            success, result, error = self.verify_and_complete_payment(pidx)

            if success:
                logger.info(f"Webhook processed successfully for pidx: {pidx}")
                return True, None
            else:
                logger.warning(f"Webhook processing failed for pidx {pidx}: {error}")
                return False, error

        except Exception as e:
            error_msg = f"Error handling webhook: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def get_user_payment_history(
        self,
        user: User,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[list, int]:
        """
        Get user's payment transaction history.

        Args:
            user: User instance
            limit: Number of transactions to return
            offset: Number of transactions to skip

        Returns:
            tuple: (transactions: list, total_count: int)
        """
        queryset = PaymentTransaction.objects.filter(user=user).order_by("-created_at")
        total_count = queryset.count()

        transactions = queryset[offset : offset + limit]

        return list(transactions), total_count

    def get_payment_stats(self, user: User) -> Dict:
        """
        Get payment statistics for a user.

        Args:
            user: User instance

        Returns:
            dict: Payment statistics
        """
        transactions = PaymentTransaction.objects.filter(
            user=user,
            status=PaymentStatus.COMPLETED
        )

        total_spent = transactions.aggregate(
            total=models.Sum("amount_npr")
        )["total"] or Decimal("0")

        total_coins_bought = transactions.aggregate(
            total=models.Sum("coins_purchased")
        )["total"] or 0

        return {
            "total_transactions": transactions.count(),
            "total_spent_npr": float(total_spent),
            "total_coins_purchased": total_coins_bought,
            "average_transaction": float(total_spent / transactions.count()) if transactions.count() > 0 else 0,
        }


# Utility functions
def get_payment_processor() -> PaymentProcessor:
    """Get payment processor instance."""
    return PaymentProcessor()


# Import models at the end to avoid circular imports
from django.db import models
