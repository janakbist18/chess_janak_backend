"""
Comprehensive tests for Stripe payment integration.
Tests payment intent creation, webhook processing, coin crediting, and edge cases.
"""
import json
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from .models import (
    PaymentPackageStripe,
    StripePaymentIntent,
    StripeCustomer,
    StripeWebhookEvent,
    UserCoin,
    CoinTransaction,
    TransactionType,
)
from .services.stripe_service import (
    StripeService,
    StripePaymentException,
    StripeWebhookException,
)

User = get_user_model()


class PaymentPackageStripeTestCase(TestCase):
    """Test payment package model and operations."""

    def setUp(self):
        """Create test packages."""
        self.package_usd = PaymentPackageStripe.objects.create(
            name="100 Coins",
            coins=100,
            price_usd=Decimal("9.99"),
            price_eur=Decimal("8.99"),
            discount_percentage=0,
            is_popular=True,
            is_active=True,
        )

        self.package_inactive = PaymentPackageStripe.objects.create(
            name="Inactive Package",
            coins=50,
            price_usd=Decimal("4.99"),
            is_active=False,
        )

    def test_package_creation(self):
        """Test package creation."""
        self.assertEqual(self.package_usd.coins, 100)
        self.assertEqual(self.package_usd.price_usd, Decimal("9.99"))
        self.assertTrue(self.package_usd.is_active)

    def test_package_filtering(self):
        """Test filtering active packages."""
        active = PaymentPackageStripe.objects.filter(is_active=True)
        self.assertEqual(active.count(), 1)
        self.assertIn(self.package_usd, active)
        self.assertNotIn(self.package_inactive, active)

    def test_package_with_discount(self):
        """Test package with discount."""
        package = PaymentPackageStripe.objects.create(
            name="Discounted",
            coins=200,
            price_usd=Decimal("20.00"),
            discount_percentage=10,
            is_active=True,
        )
        self.assertEqual(package.discount_percentage, 10)


class StripePaymentServiceTestCase(TestCase):
    """Test Stripe payment service methods."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.user.device_id = 'test_device_123'
        self.user.save()

        self.package = PaymentPackageStripe.objects.create(
            name="Test Package",
            coins=100,
            price_usd=Decimal("9.99"),
            is_active=True,
        )

    @patch('stripe.Customer.create')
    def test_get_or_create_customer(self, mock_create):
        """Test customer creation."""
        mock_customer = MagicMock()
        mock_customer.id = 'cus_test123'
        mock_customer.email = 'test@example.com'
        mock_create.return_value = mock_customer

        customer = StripeService._get_or_create_customer(self.user)

        self.assertEqual(customer.id, 'cus_test123')
        mock_create.assert_called_once()

    @patch('stripe.PaymentIntent.create')
    @patch('stripe.Customer.retrieve')
    def test_create_payment_intent(self, mock_retrieve, mock_create_pi):
        """Test payment intent creation."""
        # Mock Stripe customer
        mock_customer = MagicMock()
        mock_customer.id = 'cus_test123'
        mock_customer.email = 'test@example.com'
        mock_retrieve.return_value = mock_customer

        # Mock payment intent
        mock_pi = MagicMock()
        mock_pi.id = 'pi_test123'
        mock_pi.client_secret = 'pi_test123_secret'
        mock_pi.status = 'requires_payment_method'
        mock_create_pi.return_value = mock_pi

        # Create customer first
        StripeCustomer.objects.create(
            device_id='test_device_123',
            stripe_customer_id='cus_test123',
            email='test@example.com'
        )

        with patch('stripe.Customer.create', return_value=mock_customer):
            result = StripeService.create_payment_intent(
                user=self.user,
                package_id=self.package.id,
                currency='usd'
            )

        self.assertEqual(result['payment_intent_id'], 'pi_test123')
        self.assertEqual(result['coins'], 100)
        self.assertEqual(result['currency'], 'usd')

    def test_create_payment_intent_invalid_package(self):
        """Test payment intent creation with invalid package."""
        with self.assertRaises(StripePaymentException):
            StripeService.create_payment_intent(
                user=self.user,
                package_id=9999,  # Non-existent
                currency='usd'
            )

    @patch('stripe.PaymentIntent.create')
    def test_create_payment_intent_with_discount(self, mock_create_pi):
        """Test payment intent respects package discount."""
        mock_pi = MagicMock()
        mock_pi.id = 'pi_test123'
        mock_pi.client_secret = 'secret'
        mock_pi.status = 'requires_payment_method'
        mock_create_pi.return_value = mock_pi

        package_discounted = PaymentPackageStripe.objects.create(
            name="Discounted",
            coins=100,
            price_usd=Decimal("10.00"),
            discount_percentage=20,
            is_active=True,
        )

        StripeCustomer.objects.create(
            device_id='test_device_123',
            stripe_customer_id='cus_test123'
        )

        with patch('stripe.Customer.retrieve', return_value=MagicMock(id='cus_test123')):
            result = StripeService.create_payment_intent(
                user=self.user,
                package_id=package_discounted.id,
                currency='usd'
            )

        # 10.00 * (100 - 20) / 100 = 8.00
        self.assertEqual(result['amount'], 8.0)
        self.assertEqual(result['discount_percentage'], 20)


class StripeWebhookServiceTestCase(TestCase):
    """Test webhook processing."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username='webhooktest',
            email='webhook@example.com'
        )
        self.user.device_id = 'webhook_device'
        self.user.save()

        self.package = PaymentPackageStripe.objects.create(
            name="Webhook Test",
            coins=100,
            price_usd=Decimal("9.99"),
            is_active=True,
        )

        self.stripe_customer = StripeCustomer.objects.create(
            device_id='webhook_device',
            stripe_customer_id='cus_webhook123'
        )

        self.payment_intent = StripePaymentIntent.objects.create(
            device_id='webhook_device',
            stripe_payment_intent_id='pi_webhook123',
            stripe_customer_id='cus_webhook123',
            amount=Decimal("9.99"),
            currency='usd',
            status='processing',
            package_id=self.package.id,
            coins_to_credit=100,
        )

    @patch('stripe.Webhook.construct_event')
    def test_webhook_signature_verification(self, mock_construct):
        """Test webhook signature verification."""
        mock_event = {
            'id': 'evt_test123',
            'type': 'payment_intent.succeeded',
            'data': {
                'object': {
                    'id': 'pi_webhook123',
                    'metadata': {'user_id': str(self.user.id)}
                }
            }
        }
        mock_construct.return_value = mock_event

        event = StripeService.verify_webhook_signature(
            b'payload',
            'sig_test'
        )

        self.assertEqual(event['type'], 'payment_intent.succeeded')
        mock_construct.assert_called_once()

    @patch('stripe.Webhook.construct_event')
    def test_webhook_invalid_signature(self, mock_construct):
        """Test webhook with invalid signature."""
        import stripe
        mock_construct.side_effect = stripe.error.SignatureVerificationError(
            'msg', 'sig'
        )

        with self.assertRaises(StripeWebhookException):
            StripeService.verify_webhook_signature(
                b'payload',
                'invalid_sig'
            )

    def test_process_payment_intent_succeeded(self):
        """Test processing successful payment."""
        event = {
            'type': 'payment_intent.succeeded',
            'data': {
                'object': {
                    'id': 'pi_webhook123',
                    'metadata': {'user_id': str(self.user.id)}
                }
            }
        }

        result = StripeService.process_payment_intent_succeeded(event)

        self.assertTrue(result['success'])
        self.assertEqual(result['coins'], 100)

        # Verify coins were credited
        coin_account = UserCoin.objects.get(user=self.user)
        self.assertEqual(coin_account.total_coins, 100)

        # Verify transaction record
        txn = CoinTransaction.objects.filter(user=self.user).first()
        self.assertIsNotNone(txn)
        self.assertEqual(txn.transaction_type, TransactionType.PURCHASE)

    def test_process_payment_intent_succeeded_prevents_duplicate(self):
        """Test that payment can't be processed twice."""
        # Mark as already succeeded
        self.payment_intent.status = 'succeeded'
        self.payment_intent.save()

        event = {
            'type': 'payment_intent.succeeded',
            'data': {
                'object': {
                    'id': 'pi_webhook123',
                    'metadata': {'user_id': str(self.user.id)}
                }
            }
        }

        result = StripeService.process_payment_intent_succeeded(event)

        self.assertTrue(result['success'])
        self.assertTrue(result['already_processed'])


class StripePaymentAPITestCase(APITestCase):
    """Test Stripe payment API endpoints."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='apitest',
            email='api@example.com',
            password='testpass123'
        )

        self.package = PaymentPackageStripe.objects.create(
            name="API Test",
            coins=100,
            price_usd=Decimal("9.99"),
            price_eur=Decimal("8.99"),
            is_active=True,
        )

    def test_list_packages_unauthenticated(self):
        """Test listing packages without authentication."""
        url = reverse('stripe-payment-list-packages')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('packages', response.data)

    def test_create_payment_intent_requires_auth(self):
        """Test payment intent creation requires authentication."""
        url = reverse('stripe-payment-create-payment-intent')
        response = self.client.post(url, {'package_id': self.package.id})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('stripe.Customer.create')
    @patch('stripe.PaymentIntent.create')
    def test_create_payment_intent_authenticated(self, mock_pi, mock_customer):
        """Test payment intent creation with authentication."""
        self.client.force_authenticate(user=self.user)

        mock_cust = MagicMock()
        mock_cust.id = 'cus_api123'
        mock_customer.return_value = mock_cust

        mock_pi_obj = MagicMock()
        mock_pi_obj.id = 'pi_api123'
        mock_pi_obj.client_secret = 'api_secret'
        mock_pi_obj.status = 'requires_payment_method'
        mock_pi.return_value = mock_pi_obj

        url = reverse('stripe-payment-create-payment-intent')
        response = self.client.post(url, {'package_id': self.package.id})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('client_secret', response.data)
        self.assertEqual(response.data['coins'], 100)

    def test_list_packages_with_currency(self):
        """Test listing packages with currency filter."""
        url = reverse('stripe-payment-list-packages')
        response = self.client.get(url, {'currency': 'eur'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class StripeWebhookAPITestCase(TestCase):
    """Test webhook endpoint."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='webhookapi',
            email='webhook@example.com'
        )

    @patch('stripe.Webhook.construct_event')
    def test_webhook_endpoint_invalid_signature(self, mock_construct):
        """Test webhook error handling."""
        import stripe
        mock_construct.side_effect = stripe.error.SignatureVerificationError(
            'msg', 'sig'
        )

        response = self.client.post(
            reverse('stripe-webhook'),
            data='{}',
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='invalid'
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_webhook_endpoint_missing_signature(self):
        """Test webhook missing signature header."""
        response = self.client.post(
            reverse('stripe-webhook'),
            data='{}',
            content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class IntegrationTestCase(TestCase):
    """End-to-end integration tests."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username='integration',
            email='integration@example.com'
        )
        self.user.device_id = 'integration_device'
        self.user.save()

        self.package = PaymentPackageStripe.objects.create(
            name="Integration",
            coins=500,
            price_usd=Decimal("49.99"),
            discount_percentage=5,
            is_active=True,
        )

    @patch('stripe.Customer.create')
    @patch('stripe.PaymentIntent.create')
    def test_complete_payment_flow(self, mock_pi_create, mock_cust_create):
        """Test complete payment flow from creation to coin crediting."""
        # Setup mocks
        mock_cust = MagicMock()
        mock_cust.id = 'cus_integration'
        mock_cust.email = self.user.email
        mock_cust_create.return_value = mock_cust

        mock_pi = MagicMock()
        mock_pi.id = 'pi_integration'
        mock_pi.client_secret = 'secret'
        mock_pi.status = 'requires_payment_method'
        mock_pi_create.return_value = mock_pi

        # Step 1: Create payment intent
        result = StripeService.create_payment_intent(
            user=self.user,
            package_id=self.package.id,
            currency='usd'
        )

        self.assertIsNotNone(result['client_secret'])
        self.assertEqual(result['coins'], 500)

        # Verify payment intent record created
        pi_record = StripePaymentIntent.objects.get(
            stripe_payment_intent_id='pi_integration'
        )
        self.assertEqual(pi_record.coins_to_credit, 500)

        # Step 2: Webhook notification
        event = {
            'type': 'payment_intent.succeeded',
            'data': {
                'object': {
                    'id': 'pi_integration',
                    'metadata': {'user_id': str(self.user.id)}
                }
            }
        }

        webhook_result = StripeService.process_payment_intent_succeeded(event)
        self.assertTrue(webhook_result['success'])

        # Verify coins were credited
        coin_account = UserCoin.objects.get(user=self.user)
        self.assertEqual(coin_account.total_coins, 500)
