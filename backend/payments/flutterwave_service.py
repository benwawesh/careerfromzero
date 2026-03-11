"""
Flutterwave Payment Service
Handles Visa/Mastercard card payments via Flutterwave.
"""

import logging
import requests
import uuid
from decouple import config

logger = logging.getLogger(__name__)


class FlutterwaveService:

    def __init__(self):
        self.secret_key = config('FLUTTERWAVE_SECRET_KEY', default='')
        self.public_key = config('FLUTTERWAVE_PUBLIC_KEY', default='')
        self.redirect_url = config('FLUTTERWAVE_REDIRECT_URL', default='')
        self.base_url = 'https://api.flutterwave.com/v3'

    def initiate_payment(self, user, token_pack, payment_id: str) -> dict:
        """
        Create a Flutterwave payment link for card payment.
        Returns a redirect URL the user opens to pay.
        """
        try:
            tx_ref = f"career-ai-{payment_id}"

            payload = {
                "tx_ref": tx_ref,
                "amount": str(token_pack.price_kes),
                "currency": "KES",
                "redirect_url": self.redirect_url,
                "meta": {
                    "payment_id": str(payment_id),
                    "user_id": str(user.id),
                    "credits": token_pack.credits,
                },
                "customer": {
                    "email": user.email,
                    "name": f"{user.first_name} {user.last_name}".strip() or user.email,
                    "phonenumber": getattr(user, 'phone_number', '') or '',
                },
                "customizations": {
                    "title": "Career AI — Token Purchase",
                    "description": f"{token_pack.name}: {token_pack.credits} credits",
                    "logo": "",
                },
            }

            response = requests.post(
                f"{self.base_url}/payments",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.secret_key}",
                    "Content-Type": "application/json",
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            if data.get('status') == 'success':
                return {
                    'success': True,
                    'payment_link': data['data']['link'],
                    'tx_ref': tx_ref,
                }
            return {'success': False, 'error': data.get('message', 'Payment initiation failed')}

        except Exception as e:
            logger.error(f"Flutterwave payment initiation failed: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def verify_transaction(self, transaction_id: str) -> dict:
        """Verify a completed Flutterwave transaction by ID."""
        try:
            response = requests.get(
                f"{self.base_url}/transactions/{transaction_id}/verify",
                headers={"Authorization": f"Bearer {self.secret_key}"},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            if data.get('status') == 'success' and data['data']['status'] == 'successful':
                return {'success': True, 'data': data['data']}
            return {'success': False, 'error': 'Transaction not successful', 'data': data}

        except Exception as e:
            logger.error(f"Flutterwave verification failed: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}


flutterwave_service = FlutterwaveService()
