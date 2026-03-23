import logging
from apps.coins.models import StripePaymentIntent, TransactionType
from apps.coins.utils import update_user_coins

logger = logging.getLogger(__name__)

class StripeWebhookHandler:
    
    @staticmethod
    def handle_payment_intent_succeeded(event):
        """Handle successful payment"""
        payment_intent = event['data']['object']
        metadata = payment_intent.get('metadata', {})
        
        device_id = metadata.get('device_id')
        package_id = metadata.get('package_id')
        coins = int(metadata.get('coins', 0))
        
        # Determine intent or session
        pi_id = payment_intent.get('id')
        
        if not device_id or not coins:
            logger.error(f"Missing metadata in payment {pi_id}")
            return False
            
        # Update intent in DB
        try:
            intent_obj = StripePaymentIntent.objects.get(stripe_payment_intent_id=pi_id)
            intent_obj.status = 'succeeded'
            intent_obj.save()
        except StripePaymentIntent.DoesNotExist:
            logger.warning(f"Payment intent {pi_id} not found in DB")
            
        # Credit coins to user
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            device = next((d for d in User.objects.all() if d.username == device_id or getattr(d, 'device_id', None) == device_id), None)
            if device:
                update_user_coins(
                    user=device,
                    amount=coins,
                    transaction_type=TransactionType.PURCHASE,
                    reference=f"stripe_{pi_id}"
                )
                return True
        except Exception as e:
            logger.error(f"Error crediting coins for intent {pi_id}: {str(e)}")
            
        return False
    
    @staticmethod
    def handle_payment_intent_failed(event):
        """Handle failed payment"""
        payment_intent = event['data']['object']
        pi_id = payment_intent.get('id')
        
        try:
            intent_obj = StripePaymentIntent.objects.get(stripe_payment_intent_id=pi_id)
            intent_obj.status = 'failed'
            intent_obj.save()
        except StripePaymentIntent.DoesNotExist:
            pass
            
    @staticmethod
    def handle_checkout_session_completed(event):
        """Handle completed checkout session"""
        session = event['data']['object']
        
        # Payment is successful, create/update intent record and credit coins
        metadata = session.get('metadata', {})
        pi_id = session.get('payment_intent')
        if not pi_id:
            return False
            
        # Optional: check if we already handled payment_intent.succeeded
        
        return StripeWebhookHandler.handle_payment_intent_succeeded({
            'data': {'object': {'id': pi_id, 'metadata': metadata}}
        })
    
    @staticmethod
    def handle_charge_refunded(event):
        """Handle refunds"""
        charge = event['data']['object']
        pi_id = charge.get('payment_intent')
        
        # Deduct coins from user
        try:
            intent_obj = StripePaymentIntent.objects.get(stripe_payment_intent_id=pi_id)
            intent_obj.status = 'refunded'
            intent_obj.save()
            
            # Additional logic to deduct coins could go here
        except StripePaymentIntent.DoesNotExist:
            pass
