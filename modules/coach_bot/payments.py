"""
Payment processing for Coach Bot
Supports YooKassa (Russian) and Stripe (international)
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

from .config import config
from .db import CoachDB

logger = logging.getLogger(__name__)


class PaymentProcessor:
    """Handle subscriptions and payments"""
    
    def __init__(self):
        self.db = CoachDB()
    
    def create_yookassa_payment(self, user_id: int, plan: str, amount: int) -> Dict[str, Any]:
        """Create a YooKassa payment"""
        if not config.yookassa_shop_id or not config.yookassa_secret_key:
            return {'error': 'YooKassa not configured'}
        
        import requests
        
        payment_id = f"coach_{user_id}_{uuid.uuid4().hex[:8]}"
        
        url = "https://api.yookassa.ru/v3/payments"
        auth = (config.yookassa_shop_id, config.yookassa_secret_key)
        
        data = {
            "amount": {
                "value": str(amount),
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": "https://t.me/civis_matcher_bot"  # Will be configurable
            },
            "capture": True,
            "description": f"Coach Bot {plan} subscription",
            "metadata": {
                "user_id": str(user_id),
                "plan": plan,
                "payment_id": payment_id
            }
        }
        
        try:
            response = requests.post(url, json=data, auth=auth)
            response.raise_for_status()
            result = response.json()
            
            # Save payment record
            self.db.create_payment(user_id, amount, plan, payment_id)
            
            return {
                'payment_id': payment_id,
                'confirmation_url': result['confirmation']['confirmation_url'],
                'status': result['status'],
            }
        except Exception as e:
            logger.error(f"YooKassa payment error: {e}")
            return {'error': str(e)}
    
    def create_stripe_payment(self, user_id: int, plan: str, amount: int, currency: str = 'usd') -> Dict[str, Any]:
        """Create a Stripe payment"""
        if not config.stripe_api_key:
            return {'error': 'Stripe not configured'}
        
        import stripe
        stripe.api_key = config.stripe_api_key
        
        # Convert RUB to USD (approximate)
        if currency == 'rub':
            amount_usd = int(amount / 75)  # Approximate conversion
        else:
            amount_usd = amount
        
        try:
            # Create checkout session
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f'Coach Bot {plan} Subscription',
                            'description': 'Personal AI coach for goal setting and achievement',
                        },
                        'unit_amount': amount_usd * 100,  # Stripe uses cents
                        'recurring': {
                            'interval': 'month',
                        }
                    },
                    'quantity': 1,
                }],
                mode='subscription',
                success_url='https://t.me/civis_matcher_bot?start=success',
                cancel_url='https://t.me/civis_matcher_bot?start=cancel',
                metadata={
                    'user_id': str(user_id),
                    'plan': plan,
                }
            )
            
            # Save payment record
            self.db.create_payment(user_id, amount, plan, session.id)
            
            return {
                'payment_id': session.id,
                'confirmation_url': session.url,
                'status': 'pending',
            }
        except Exception as e:
            logger.error(f"Stripe payment error: {e}")
            return {'error': str(e)}
    
    def confirm_payment(self, payment_id: str, provider: str = 'yookassa') -> bool:
        """Confirm payment and activate subscription"""
        try:
            self.db.confirm_payment(payment_id)
            return True
        except Exception as e:
            logger.error(f"Payment confirmation error: {e}")
            return False
    
    def get_subscription_status(self, user_id: int) -> Dict[str, Any]:
        """Get user's subscription status"""
        user = self.db.get_or_create_user(user_id)
        status = self.db.get_user_status(user_id)
        
        return {
            'status': status['status'],
            'is_subscribed': status['is_subscribed'],
            'is_trial_active': status['is_trial_active'],
            'trial_days_left': self._get_trial_days_left(user),
            'subscription_days_left': self._get_subscription_days_left(user),
            'today_messages': status['today_messages'],
            'free_limit': status['free_limit'],
        }
    
    def _get_trial_days_left(self, user: Dict) -> Optional[int]:
        """Get days left in trial"""
        if not user.get('trial_end'):
            return None
        try:
            end_date = datetime.strptime(user['trial_end'], '%Y-%m-%d').date()
            delta = end_date - datetime.now().date()
            return max(0, delta.days)
        except:
            return None
    
    def _get_subscription_days_left(self, user: Dict) -> Optional[int]:
        """Get days left in subscription"""
        if not user.get('subscription_end'):
            return None
        try:
            end_date = datetime.strptime(user['subscription_end'], '%Y-%m-%d').date()
            delta = end_date - datetime.now().date()
            return max(0, delta.days)
        except:
            return None


# Webhook handlers

def handle_yookassa_webhook(request_data: Dict) -> Dict[str, Any]:
    """Handle YooKassa webhook"""
    event = request_data.get('event')
    
    if event == 'payment.succeeded':
        payment_data = request_data.get('object', {})
        metadata = payment_data.get('metadata', {})
        payment_id = metadata.get('payment_id')
        
        if payment_id:
            processor = PaymentProcessor()
            success = processor.confirm_payment(payment_id, 'yookassa')
            return {'status': 'ok', 'confirmed': success}
    
    return {'status': 'ok'}


def handle_stripe_webhook(payload: bytes, sig_header: str) -> Dict[str, Any]:
    """Handle Stripe webhook"""
    if not config.stripe_api_key:
        return {'error': 'Stripe not configured'}
    
    import stripe
    stripe.api_key = config.stripe_api_key
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, 'whsec_placeholder'  # Should be configurable
        )
    except Exception as e:
        logger.error(f"Stripe webhook error: {e}")
        return {'error': str(e)}
    
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = session.get('metadata', {}).get('user_id')
        
        if user_id:
            processor = PaymentProcessor()
            processor.db.confirm_payment(session['id'])
            
            # Activate subscription
            from .db import CoachDB
            db = CoachDB()
            end_date = datetime.now().date() + timedelta(days=30)
            db.update_user(
                int(user_id),
                status='paid',
                subscription_end=end_date.isoformat()
            )
            
            return {'status': 'ok'}
    
    return {'status': 'ok'}
