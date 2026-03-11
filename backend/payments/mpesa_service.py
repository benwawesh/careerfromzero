"""
M-Pesa Daraja API Service
Handles STK Push and payment confirmation callbacks.
"""

import base64
import logging
import requests
from datetime import datetime
from decouple import config

logger = logging.getLogger(__name__)


class MpesaService:

    def __init__(self):
        self.consumer_key = config('MPESA_CONSUMER_KEY', default='')
        self.consumer_secret = config('MPESA_CONSUMER_SECRET', default='')
        self.shortcode = config('MPESA_SHORTCODE', default='')
        self.passkey = config('MPESA_PASSKEY', default='')
        self.callback_url = config('MPESA_CALLBACK_URL', default='')
        self.env = config('MPESA_ENV', default='sandbox')  # sandbox or production

        self.base_url = (
            'https://api.safaricom.co.ke'
            if self.env == 'production'
            else 'https://sandbox.safaricom.co.ke'
        )

    def _get_access_token(self) -> str:
        """Get OAuth access token from Safaricom."""
        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        credentials = base64.b64encode(
            f"{self.consumer_key}:{self.consumer_secret}".encode()
        ).decode()

        response = requests.get(
            url,
            headers={"Authorization": f"Basic {credentials}"},
            timeout=30
        )
        response.raise_for_status()
        return response.json()['access_token']

    def _get_password(self, timestamp: str) -> str:
        """Generate M-Pesa API password."""
        data = f"{self.shortcode}{self.passkey}{timestamp}"
        return base64.b64encode(data.encode()).decode()

    def stk_push(self, phone: str, amount: int, payment_id: str, description: str = 'Token purchase') -> dict:
        """
        Initiate STK Push — sends payment prompt to user's phone.
        phone: format 254XXXXXXXXX
        amount: in KES (whole number)
        payment_id: your payment record UUID (used as AccountReference)
        """
        try:
            token = self._get_access_token()
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            password = self._get_password(timestamp)

            # Normalize phone number to 254XXXXXXXXX
            phone = self._normalize_phone(phone)

            payload = {
                "BusinessShortCode": self.shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": int(amount),
                "PartyA": phone,
                "PartyB": self.shortcode,
                "PhoneNumber": phone,
                "CallBackURL": self.callback_url,
                "AccountReference": str(payment_id)[:12],
                "TransactionDesc": description[:13],
            }

            response = requests.post(
                f"{self.base_url}/mpesa/stkpush/v1/processrequest",
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"STK Push sent to {phone}: {data}")
            return {'success': True, 'data': data}

        except Exception as e:
            logger.error(f"STK Push failed: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def query_stk_status(self, checkout_request_id: str) -> dict:
        """Query the status of an STK push transaction."""
        try:
            token = self._get_access_token()
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            password = self._get_password(timestamp)

            payload = {
                "BusinessShortCode": self.shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "CheckoutRequestID": checkout_request_id,
            }

            response = requests.post(
                f"{self.base_url}/mpesa/stkpushquery/v1/query",
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                timeout=30
            )
            response.raise_for_status()
            return {'success': True, 'data': response.json()}

        except Exception as e:
            logger.error(f"STK query failed: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def _normalize_phone(self, phone: str) -> str:
        """Convert phone to 254XXXXXXXXX format."""
        phone = phone.strip().replace(' ', '').replace('-', '')
        if phone.startswith('0'):
            phone = '254' + phone[1:]
        elif phone.startswith('+'):
            phone = phone[1:]
        return phone


mpesa_service = MpesaService()
