"""
Coach Bot Payments
Integration with YooKassa and Stripe
"""

import logging
import uuid
from typing import Optional, Dict, Any
from datetime import datetime
import requests
import json

from .db import CoachDB
from .config import config

logger = logging.getLogger(__name__)


class PaymentProcessor:
    """Handle payments for coach bot subscriptions"""
    
    def __init__(self):
        self.db = CoachDB()
        self.yookassa_shop_id = config.yookassa_shop_id
        self.yookassa_secret = config.yookassa_secret_key
        self.stripe_secret = config.stripe_secret_key
    
    def create_yookassa_payment(
        self,
        user_id: int,
        amount: int = 999,
        description: str = "Подписка на Coach Bot",
        return_url: str = None,
    ) -> Dict[str, Any]:
        """
        Create a YooKassa payment
        
        Returns:
            Dict with payment_id, confirmation_url, and status
        """
        if not self.yookassa_shop_id or not self.yookassa_secret:
            logger.warning("YooKassa credentials not configured")
            return {
                "status": "error",
                "message": "Payment system not configured",
            }
        
        payment_id = f"coach_{user_id}_{uuid.uuid4().hex[:8]}"
        
        # Create payment in YooKassa
        url = "https://api.yookassa.ru/v3/payments"
        headers = {
            "Content-Type": "application/json",
            "Idempotence-Key": payment_id,
        }
        
        # Basic auth with shop_id and secret
        auth = (self.yookassa_shop_id, self.yookassa_secret)
        
        payload = {
            "amount": {
                "value": str(amount),
                "currency": "RUB",
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url or "https://t.me/civis_matcher_bot",
            },
            "capture": True,
            "description": description,
            "metadata": {
                "user_id": str(user_id),
                "payment_id": payment_id,
            }
        }
        
        try:
            response = requests.post(url, headers=headers, auth=auth, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Save subscription record
            self.db.create_subscription(
                user_id=user_id,
                payment_id=payment_id,
                amount=amount,
                plan_type="monthly",
            )
            
            return {
                "status": "pending",
                "payment_id": payment_id,
                "confirmation_url": data.get("confirmation", {}).get("confirmation_url"),
                "yookassa_id": data.get("id"),
            }
        except Exception as e:
            logger.error(f"YooKassa payment creation error: {e}")
            return {
                "status": "error",
                "message": str(e),
            }
    
    def confirm_yookassa_payment(self, payment_id: str) -> Dict[str, Any]:
        """
        Confirm a YooKassa payment after webhook notification
        """
        if not self.yookassa_shop_id or not self.yookassa_secret:
            return {"status": "error", "message": "Payment system not configured"}
        
        url = f"https://api.yookassa.ru/v3/payments/{payment_id}"
        auth = (self.yookassa_shop_id, self.yookassa_secret)
        
        try:
            response = requests.get(url, auth=auth, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") == "succeeded":
                # Activate subscription
                user_id = data.get("metadata", {}).get("user_id")
                if user_id:
                    self.db.activate_subscription(int(user_id), months=1)
                    self.db.confirm_subscription(payment_id)
                    
                    return {
                        "status": "success",
                        "user_id": user_id,
                        "payment_id": payment_id,
                    }
            
            return {
                "status": data.get("status", "unknown"),
                "payment_id": payment_id,
            }
        except Exception as e:
            logger.error(f"YooKassa payment confirmation error: {e}")
            return {"status": "error", "message": str(e)}
    
    def create_stripe_payment(
        self,
        user_id: int,
        amount: int = 15,
        currency: str = "usd",
    ) -> Dict[str, Any]:
        """
        Create a Stripe payment session
        
        Returns:
            Dict with checkout_url and payment_id
        """
        if not self.stripe_secret:
            logger.warning("Stripe credentials not configured")
            return {
                "status": "error",
                "message": "Payment system not configured",
            }
        
        try:
            import stripe
            stripe.api_key = self.stripe_secret
            
            # Create checkout session
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": currency,
                        "product_data": {
                            "name": "Coach Bot Subscription",
                            "description": "Monthly access to AI coaching",
                        },
                        "unit_amount": amount * 100,  # Stripe uses cents
                    },
                    "quantity": 1,
                }],
                mode="payment",
                success_url="https://t.me/civis_matcher_bot?start=success",
                cancel_url="https://t.me/civis_matcher_bot?start=cancel",
                metadata={
                    "user_id": str(user_id),
                },
            )
            
            payment_id = session.id
            
            # Save subscription record
            self.db.create_subscription(
                user_id=user_id,
                payment_id=payment_id,
                amount=amount,
                plan_type="monthly",
            )
            
            return {
                "status": "pending",
                "payment_id": payment_id,
                "checkout_url": session.url,
            }
        except Exception as e:
            logger.error(f"Stripe payment creation error: {e}")
            return {
                "status": "error",
                "message": str(e),
            }
    
    def handle_yookassa_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle YooKassa webhook notification
        
        Expected payload format from YooKassa:
        {
            "event": "payment.succeeded",
            "object": {
                "id": "payment_id",
                "status": "succeeded",
                "metadata": {"user_id": "123"}
            }
        }
        """
        try:
            event = payload.get("event")
            payment_data = payload.get("object", {})
            
            if event == "payment.succeeded":
                payment_id = payment_data.get("id")
                if payment_id:
                    return self.confirm_yookassa_payment(payment_id)
            
            return {
                "status": "ignored",
                "event": event,
            }
        except Exception as e:
            logger.error(f"Webhook handling error: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_subscription_status(self, user_id: int) -> Dict[str, Any]:
        """Get user's subscription status"""
        user = self.db.get_user(user_id)
        if not user:
            return {"status": "not_found"}
        
        status = user.get("status", "free")
        result = {
            "status": status,
            "plan": "free",
        }
        
        if status == "trial":
            result["plan"] = "trial"
            result["ends_at"] = user.get("trial_end")
            result["days_left"] = self._days_until(user.get("trial_end")) if user.get("trial_end") else 0
        elif status == "paid":
            result["plan"] = "monthly"
            result["ends_at"] = user.get("subscription_end")
            result["days_left"] = self._days_until(user.get("subscription_end")) if user.get("subscription_end") else 0
        
        return result
    
    @staticmethod
    def _days_until(date_str: Optional[str]) -> int:
        """Calculate days until a date"""
        if not date_str:
            return 0
        from datetime import date
        try:
            target = date.fromisoformat(date_str)
            delta = target - date.today()
            return max(0, delta.days)
        except (ValueError, TypeError):
            return 0
