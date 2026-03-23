"""
Khalti payment gateway integration service.
Handles API communication with Khalti payment system.
"""
import logging
import requests
from typing import Dict, Optional, Tuple
from django.conf import settings

logger = logging.getLogger(__name__)


class KhaltiPaymentError(Exception):
    """Base exception for Khalti payment errors."""
    pass


class KhaltiInitiationError(KhaltiPaymentError):
    """Error during payment initiation."""
    pass


class KhaltiVerificationError(KhaltiPaymentError):
    """Error during payment verification."""
    pass


class KhaltiService:
    """
    Khalti payment gateway integration.
    Handles initialization and verification of payments.
    """

    # Khalti API endpoints
    INITIATOR_URL = "https://a.khalti.com/api/v2/epayment/initiate/"
    LOOKUP_URL = "https://a.khalti.com/api/v2/epayment/lookup/"
    VERIFY_URL = "https://a.khalti.com/api/v2/epayment/complete/"

    def __init__(self):
        """Initialize Khalti service with configuration."""
        self.secret_key = settings.KHALTI_SECRET_KEY
        self.test_secret_key = settings.KHALTI_TEST_SECRET_KEY
        self.is_test = settings.KHALTI_TEST_MODE
        self.merchant_code = settings.KHALTI_MERCHANT_CODE
        self.timeout = 10  # seconds

        if not self.secret_key or not self.merchant_code:
            logger.warning("Khalti configuration incomplete: Missing secret key or merchant code")

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for Khalti API requests."""
        secret_key = self.test_secret_key if self.is_test else self.secret_key
        return {
            "Authorization": f"Key {secret_key}",
            "Content-Type": "application/json",
        }

    def initiate_payment(
        self,
        amount_paisa: int,
        purchase_order_id: str,
        purchase_order_name: str,
        return_url: str,
        website_url: str,
        customer_name: str = "Chess Player",
        customer_email: str = "",
        customer_phone: str = "",
    ) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Initiate a payment with Khalti.

        Args:
            amount_paisa: Amount in paisa (1 NPR = 100 paisa)
            purchase_order_id: Unique order ID
            purchase_order_name: Human-readable order name
            return_url: URL to redirect after payment
            website_url: Your website URL
            customer_name: Customer name
            customer_email: Customer email
            customer_phone: Customer phone number

        Returns:
            tuple: (success: bool, result: dict with pidx and payment_url, error: str)
        """
        try:
            payload = {
                "return_url": return_url,
                "website_url": website_url,
                "amount": amount_paisa,
                "purchase_order_id": purchase_order_id,
                "purchase_order_name": purchase_order_name,
                "customer_info": {
                    "name": customer_name,
                    "email": customer_email,
                    "phone": customer_phone,
                },
            }

            logger.info(
                f"Initiating Khalti payment for order {purchase_order_id} "
                f"(Amount: {amount_paisa} paisa)"
            )

            response = requests.post(
                self.INITIATOR_URL,
                json=payload,
                headers=self._get_headers(),
                timeout=self.timeout,
            )

            if response.status_code not in [200, 201]:
                error_msg = f"Khalti API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False, None, error_msg

            data = response.json()

            # Extract pidx and payment_url
            pidx = data.get("pidx")
            payment_url = data.get("payment_url")

            if not pidx or not payment_url:
                error_msg = f"Invalid Khalti response: Missing pidx or payment_url"
                logger.error(f"{error_msg}. Response: {data}")
                return False, None, error_msg

            logger.info(f"Successfully initiated payment with pidx: {pidx}")

            return True, {"pidx": pidx, "payment_url": payment_url}, None

        except requests.exceptions.Timeout:
            error_msg = "Khalti API timeout"
            logger.error(error_msg)
            return False, None, error_msg
        except requests.exceptions.RequestException as e:
            error_msg = f"Khalti API request error: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
        except Exception as e:
            error_msg = f"Unexpected error initiating Khalti payment: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg

    def verify_payment(self, pidx: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Verify a payment with Khalti.

        Args:
            pidx: Payment transaction ID from initiation response

        Returns:
            tuple: (
                success: bool,
                result: dict with transaction details,
                error: str
            )
        """
        try:
            payload = {"pidx": pidx}

            logger.info(f"Verifying Khalti payment with pidx: {pidx}")

            response = requests.post(
                self.LOOKUP_URL,
                json=payload,
                headers=self._get_headers(),
                timeout=self.timeout,
            )

            if response.status_code not in [200, 201]:
                error_msg = f"Khalti verification failed: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False, None, error_msg

            data = response.json()

            # Map Khalti response to our data structure
            result = {
                "pidx": data.get("pidx"),
                "transaction_id": data.get("transaction_id"),
                "amount": data.get("amount"),
                "status": data.get("status"),  # "Completed", "Pending", "Failed"
                "mobile": data.get("mobile"),
                "purchase_order_id": data.get("purchase_order_id"),
                "purchase_order_name": data.get("purchase_order_name"),
                "raw_response": data,
            }

            logger.info(
                f"Khalti payment verification - Status: {data.get('status')}, "
                f"Transaction ID: {data.get('transaction_id')}"
            )

            return True, result, None

        except requests.exceptions.Timeout:
            error_msg = "Khalti verification timeout"
            logger.error(error_msg)
            return False, None, error_msg
        except requests.exceptions.RequestException as e:
            error_msg = f"Khalti verification request error: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
        except Exception as e:
            error_msg = f"Unexpected error verifying Khalti payment: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg

    def validate_webhook_signature(
        self, webhook_data: Dict, signature: str
    ) -> bool:
        """
        Validate Khalti webhook signature.

        Currently not implemented as Khalti doesn't require signature validation.
        This method is placeholder for future use.

        Args:
            webhook_data: Webhook payload
            signature: Signature header from webhook

        Returns:
            bool: True if signature is valid
        """
        # Khalti webhooks don't require signature validation by default
        # This is a placeholder for future enhanced security
        return True

    @staticmethod
    def convert_npr_to_paisa(amount_npr: float) -> int:
        """
        Convert NPR amount to paisa (100 paisa = 1 NPR).

        Args:
            amount_npr: Amount in NPR

        Returns:
            int: Amount in paisa
        """
        return int(amount_npr * 100)

    @staticmethod
    def convert_paisa_to_npr(amount_paisa: int) -> float:
        """
        Convert paisa to NPR amount.

        Args:
            amount_paisa: Amount in paisa

        Returns:
            float: Amount in NPR
        """
        return amount_paisa / 100
