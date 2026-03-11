"""
PesaPal Payment Service
Handles Visa/Mastercard card payments via PesaPal v3 API.
Docs: https://developer.pesapal.com/how-to-integrate/e-commerce/api-30-json/api-reference
"""

import logging
import requests
import uuid
from decouple import config

logger = logging.getLogger(__name__)


class PesaPalService:

    def __init__(self):
        self.consumer_key = config('PESAPAL_CONSUMER_KEY', default='')
        self.consumer_secret = config('PESAPAL_CONSUMER_SECRET', default='')
        self.env = config('PESAPAL_ENV', default='sandbox')
        self.callback_url = config('PESAPAL_CALLBACK_URL', default='')
        self.ipn_url = config('PESAPAL_IPN_URL', default='')

        if self.env == 'production':
            self.base_url = 'https://pay.pesapal.com/v3'
        else:
            self.base_url = 'https://cybqa.pesapal.com/pesapalv3'

        self._token = None

    def _get_token(self) -> str:
        """Get OAuth token from PesaPal."""
        try:
            response = requests.post(
                f"{self.base_url}/api/Auth/RequestToken",
                json={
                    "consumer_key": self.consumer_key,
                    "consumer_secret": self.consumer_secret,
                },
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            token = data.get('token')
            if not token:
                raise Exception(f"No token in response: {data}")
            self._token = token
            return token
        except Exception as e:
            logger.error(f"PesaPal token request failed: {e}", exc_info=True)
            raise

    def _register_ipn(self, token: str) -> str:
        """Register IPN URL and return ipn_id."""
        try:
            response = requests.post(
                f"{self.base_url}/api/URLSetup/RegisterIPN",
                json={
                    "url": self.ipn_url,
                    "ipn_notification_type": "POST",
                },
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            return data.get('ipn_id', '')
        except Exception as e:
            logger.error(f"PesaPal IPN registration failed: {e}", exc_info=True)
            return ''

    def initiate_payment(self, user, token_pack, payment_id: str) -> dict:
        """
        Submit order to PesaPal and return redirect URL.
        """
        try:
            token = self._get_token()
            ipn_id = self._register_ipn(token)

            if not ipn_id:
                return {'success': False, 'error': 'Failed to register IPN with PesaPal'}

            order_ref = f"career-{payment_id}"
            full_name = f"{user.first_name} {user.last_name}".strip() or user.email

            payload = {
                "id": order_ref,
                "currency": "KES",
                "amount": float(token_pack.price_kes),
                "description": f"{token_pack.name}: {token_pack.credits} credits",
                "callback_url": self.callback_url,
                "notification_id": ipn_id,
                "billing_address": {
                    "email_address": user.email,
                    "phone_number": getattr(user, 'phone_number', '') or '',
                    "first_name": user.first_name or full_name,
                    "last_name": user.last_name or '',
                },
            }

            response = requests.post(
                f"{self.base_url}/api/Transactions/SubmitOrderRequest",
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            redirect_url = data.get('redirect_url')
            order_tracking_id = data.get('order_tracking_id')

            if redirect_url and order_tracking_id:
                return {
                    'success': True,
                    'payment_link': redirect_url,
                    'order_tracking_id': order_tracking_id,
                    'order_ref': order_ref,
                }

            return {'success': False, 'error': data.get('error', {}).get('message', 'Order submission failed')}

        except Exception as e:
            logger.error(f"PesaPal payment initiation failed: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def verify_transaction(self, order_tracking_id: str) -> dict:
        """Verify a completed PesaPal transaction by order_tracking_id."""
        try:
            token = self._get_token()

            response = requests.get(
                f"{self.base_url}/api/Transactions/GetTransactionStatus",
                params={"orderTrackingId": order_tracking_id},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            payment_status = data.get('payment_status_description', '').lower()

            if payment_status == 'completed':
                return {'success': True, 'data': data}
            return {'success': False, 'error': f"Payment status: {payment_status}", 'data': data}

        except Exception as e:
            logger.error(f"PesaPal verification failed: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}


pesapal_service = PesaPalService()
