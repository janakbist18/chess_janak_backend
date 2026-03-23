"""
Stripe payment service module.
Handles all Stripe API interactions, payment processing, and webhook verification.
Security: Always verify webhook signatures, validate amounts server-side, use HTTPS only.
"""
import stripe
import logging
from decimal import Decimal
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.coins.models import (
    StripeCustomer,
    StripePaymentIntent,
    PaymentPackageStripe,
    StripeWebhookEvent,
    UserCoin,
    CoinTransaction,
    TransactionType
)

logger = logging.getLogger(__name__)

# Configure Stripe API key (optional - only if configured in settings)
stripe_key = getattr(settings, 'STRIPE_SECRET_KEY', None)
if stripe_key:
    stripe.api_key = stripe_key
    stripe.api_version = getattr(settings, 'STRIPE_API_VERSION', '2023-10-16')


class StripeException(Exception):
    """Base exception for Stripe payment operations."""
    pass


class StripePaymentException(StripeException):
    """Raised for payment-related errors."""
    pass


class StripeWebhookException(StripeException):
    """Raised for webhook verification/processing errors."""
    pass


class StripeService:
    """
    Production-ready Stripe payment service.
    Handles payment processing, webhook verification, and coin crediting.
    """

    @staticmethod
    def _validate_amount(amount):
        """Validate payment amount is positive."""
        if not isinstance(amount, (int, float, Decimal)):
            raise ValidationError("Amount must be a number")
        if Decimal(str(amount)) <= 0:
            raise ValidationError("Amount must be greater than 0")

    @staticmethod
    def _get_or_create_customer(user, email=None):
        """
        Get or create a Stripe customer.

        Args:
            user: Django User instance
            email: User email (optional)

        Returns:
            stripe.Customer object

        Raises:
            StripePaymentException: If customer creation fails
        """
        try:
            device_id = getattr(user, 'device_id', f'user_{user.id}')
            stripe_customer_rec, created = StripeCustomer.objects.get_or_create(
                device_id=device_id,
                defaults={
                    'email': email or user.email,
                    'name': user.get_full_name() or user.username,
                }
            )

            if created or not stripe_customer_rec.stripe_customer_id:
                customer = stripe.Customer.create(
                    email=email or user.email,
                    name=user.get_full_name() or user.username,
                    metadata={
                        'user_id': str(user.id),
                        'username': user.username,
                        'device_id': device_id,
                    }
                )

                stripe_customer_rec.stripe_customer_id = customer.id
                stripe_customer_rec.email = customer.email
                stripe_customer_rec.name = customer.name
                stripe_customer_rec.save(update_fields=['stripe_customer_id', 'email', 'name'])

                logger.info(f"Created Stripe customer {customer.id} for user {user.username}")
                return customer
            else:
                return stripe.Customer.retrieve(stripe_customer_rec.stripe_customer_id)

        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error: {str(e)}")
            raise StripePaymentException(f"Failed to create payment customer: {str(e)}")

    @staticmethod
    def create_payment_intent(user, package_id, currency='usd'):
        """
        Create a Stripe Payment Intent for purchasing coins.

        Args:
            user: Django User instance
            package_id: ID of PaymentPackageStripe
            currency: Currency code (usd, eur, gbp)

        Returns:
            dict with 'client_secret', 'amount', 'currency', etc.

        Raises:
            StripePaymentException: If payment intent creation fails
        """
        try:
            try:
                package = PaymentPackageStripe.objects.get(
                    id=package_id,
                    is_active=True
                )
            except PaymentPackageStripe.DoesNotExist:
                raise StripePaymentException(f"Invalid or inactive package: {package_id}")

            # Get price in selected currency
            currency_lower = currency.lower()
            if currency_lower == 'usd':
                amount = float(package.price_usd)
            elif currency_lower == 'eur':
                if not package.price_eur:
                    raise StripePaymentException(f"EUR pricing not available")
                amount = float(package.price_eur)
            elif currency_lower == 'gbp':
                if not package.price_gbp:
                    raise StripePaymentException(f"GBP pricing not available")
                amount = float(package.price_gbp)
            else:
                raise StripePaymentException(f"Unsupported currency: {currency}")

            StripeService._validate_amount(amount)

            # Get or create Stripe customer
            customer = StripeService._get_or_create_customer(user)

            # Calculate final price with discount
            discount_multiplier = (100 - package.discount_percentage) / 100
            amount_after_discount = amount * discount_multiplier

            # Create payment intent
            payment_intent = stripe.PaymentIntent.create(
                amount=int(amount_after_discount * 100),  # Stripe uses cents
                currency=currency_lower,
                customer=customer.id,
                metadata={
                    'user_id': str(user.id),
                    'username': user.username,
                    'package_id': str(package.id),
                    'package_name': package.name,
                    'coins': str(package.coins),
                },
                description=f"{package.name} - {package.coins} coins",
                statement_descriptor=f"Chess Janak - {package.coins} coins",
            )

            # Store payment intent record
            StripePaymentIntent.objects.create(
                device_id=getattr(user, 'device_id', f'user_{user.id}'),
                stripe_payment_intent_id=payment_intent.id,
                stripe_customer_id=customer.id,
                amount=Decimal(str(amount_after_discount)),
                currency=currency_lower,
                status=payment_intent.status,
                package_id=package.id,
                coins_to_credit=package.coins,
                metadata={
                    'discount_percentage': package.discount_percentage,
                    'original_amount': str(amount),
                }
            )

            logger.info(f"Created payment intent {payment_intent.id} for user {user.username}")

            return {
                'client_secret': payment_intent.client_secret,
                'payment_intent_id': payment_intent.id,
                'amount': amount_after_discount,
                'amount_cents': int(amount_after_discount * 100),
                'currency': currency_lower,
                'package_id': package.id,
                'coins': package.coins,
                'discount_percentage': package.discount_percentage,
            }

        except StripePaymentException:
            raise
        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error creating payment intent: {str(e)}")
            raise StripePaymentException(f"Failed to create payment intent: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error creating payment intent: {str(e)}", exc_info=True)
            raise StripePaymentException(f"Payment initiation failed: {str(e)}")

    @staticmethod
    def verify_webhook_signature(payload_bytes, signature_header):
        """
        Verify Stripe webhook signature.
        SECURITY-CRITICAL: Always verify signatures.

        Args:
            payload_bytes: Raw request body bytes
            signature_header: Stripe-Signature header value

        Returns:
            dict: Parsed event data

        Raises:
            StripeWebhookException: If signature verification fails
        """
        try:
            event = stripe.Webhook.construct_event(
                payload_bytes,
                signature_header,
                settings.STRIPE_WEBHOOK_SECRET
            )
            return event
        except ValueError:
            raise StripeWebhookException("Invalid payload")
        except stripe.error.SignatureVerificationError:
            logger.warning("Invalid Stripe webhook signature")
            raise StripeWebhookException("Invalid signature")

    @staticmethod
    def process_payment_intent_succeeded(event):
        """
        Process payment_intent.succeeded webhook event.
        Credits coins to user after successful payment.

        Args:
            event: Stripe webhook event

        Returns:
            dict: Processing result

        Raises:
            StripeWebhookException: If processing fails
        """
        payment_intent = event['data']['object']
        payment_intent_id = payment_intent['id']

        try:
            with transaction.atomic():
                try:
                    pi_record = StripePaymentIntent.objects.select_for_update().get(
                        stripe_payment_intent_id=payment_intent_id
                    )
                except StripePaymentIntent.DoesNotExist:
                    raise StripeWebhookException(f"Payment intent not found: {payment_intent_id}")

                # Prevent duplicate processing
                if pi_record.status == 'succeeded':
                    logger.info(f"Payment already processed: {payment_intent_id}")
                    return {'success': True, 'already_processed': True}

                pi_record.status = 'succeeded'
                pi_record.save(update_fields=['status'])

                user_id = payment_intent.get('metadata', {}).get('user_id')
                if not user_id:
                    raise StripeWebhookException("User ID missing in payment metadata")

                from django.contrib.auth import get_user_model
                User = get_user_model()
                try:
                    user = User.objects.get(id=user_id)
                except User.DoesNotExist:
                    raise StripeWebhookException(f"User not found: {user_id}")

                coin_account, _ = UserCoin.objects.get_or_create(user=user)

                coin_account.add_coins(
                    amount=pi_record.coins_to_credit,
                    transaction_type=TransactionType.PURCHASE,
                    description=f"Stripe payment: {pi_record.coins_to_credit} coins"
                )

                logger.info(f"Credited {pi_record.coins_to_credit} coins to user {user.username}")

                return {'success': True, 'user_id': user.id, 'coins': pi_record.coins_to_credit}

        except StripeWebhookException:
            raise
        except Exception as e:
            logger.error(f"Error processing payment: {str(e)}", exc_info=True)
            raise StripeWebhookException(f"Failed to process payment: {str(e)}")

    @staticmethod
    def process_payment_intent_failed(event):
        """Process payment_intent.payment_failed webhook event."""
        payment_intent = event['data']['object']
        payment_intent_id = payment_intent['id']

        try:
            pi_record = StripePaymentIntent.objects.get(
                stripe_payment_intent_id=payment_intent_id
            )
            pi_record.status = 'payment_failed'
            pi_record.save(update_fields=['status'])
            logger.warning(f"Payment failed: {payment_intent_id}")
        except StripePaymentIntent.DoesNotExist:
            logger.error(f"Payment intent not found: {payment_intent_id}")

    @staticmethod
    def record_webhook_event(event):
        """Record webhook event for audit trail."""
        try:
            StripeWebhookEvent.objects.create(
                event_id=event['id'],
                event_type=event['type'],
                payload=event,
                processed=False
            )
        except Exception as e:
            logger.error(f"Failed to record webhook event: {str(e)}", exc_info=True)

    @staticmethod
    def get_payment_status(payment_intent_id):
        """Get current payment status."""
        try:
            pi_record = StripePaymentIntent.objects.get(
                stripe_payment_intent_id=payment_intent_id
            )
            return {
                'status': pi_record.status,
                'coins': pi_record.coins_to_credit,
                'amount': str(pi_record.amount),
                'currency': pi_record.currency,
            }
        except StripePaymentIntent.DoesNotExist:
            raise StripeWebhookException(f"Payment intent not found")

    @staticmethod
    def list_packages(currency='usd', active_only=True):
        """List available coin packages."""
        query = PaymentPackageStripe.objects.all()
        if active_only:
            query = query.filter(is_active=True)

        packages = []
        for pkg in query.order_by('-is_popular', 'coins'):
            if currency.lower() == 'usd':
                price = pkg.price_usd
            elif currency.lower() == 'eur':
                price = pkg.price_eur
            elif currency.lower() == 'gbp':
                price = pkg.price_gbp
            else:
                continue

            if price is None:
                continue

            packages.append({
                'id': pkg.id,
                'name': pkg.name,
                'coins': pkg.coins,
                'price': str(price),
                'currency': currency.upper(),
                'discount_percentage': pkg.discount_percentage,
                'is_popular': pkg.is_popular,
                'value_per_coin': str(float(price) / pkg.coins if pkg.coins > 0 else 0),
            })

        return packages
