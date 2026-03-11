"""
Payments Views
API endpoints for token packs, payments and balance.
"""

import logging
from django.utils import timezone
from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import TokenPack, Payment, TokenTransaction
from .token_service import get_or_create_balance, add_credits
from .mpesa_service import mpesa_service
from .flutterwave_service import flutterwave_service

logger = logging.getLogger(__name__)


class TokenPacksView(APIView):
    """List all active token packs."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        packs = TokenPack.objects.filter(is_active=True)
        return Response([
            {
                'id': p.id,
                'name': p.name,
                'description': p.description,
                'credits': p.credits,
                'price_kes': float(p.price_kes),
                'is_featured': p.is_featured,
            }
            for p in packs
        ])


class TokenBalanceView(APIView):
    """Get current user's token balance and recent transactions."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        balance = get_or_create_balance(request.user)
        transactions = TokenTransaction.objects.filter(user=request.user)[:10]
        return Response({
            'balance': balance.balance,
            'total_purchased': balance.total_purchased,
            'total_used': balance.total_used,
            'recent_transactions': [
                {
                    'type': t.transaction_type,
                    'credits': t.credits,
                    'balance_after': t.balance_after,
                    'description': t.description,
                    'date': t.created_at.isoformat(),
                }
                for t in transactions
            ]
        })


class InitiateMpesaPaymentView(APIView):
    """Initiate M-Pesa STK Push payment."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        pack_id = request.data.get('pack_id')
        phone = request.data.get('phone', '').strip()

        if not pack_id or not phone:
            return Response({'error': True, 'message': 'pack_id and phone are required'}, status=400)

        try:
            pack = TokenPack.objects.get(id=pack_id, is_active=True)
        except TokenPack.DoesNotExist:
            return Response({'error': True, 'message': 'Token pack not found'}, status=404)

        payment = Payment.objects.create(
            user=request.user,
            token_pack=pack,
            payment_method='mpesa',
            amount_kes=pack.price_kes,
            credits_to_add=pack.credits,
            mpesa_phone=phone,
        )

        result = mpesa_service.stk_push(
            phone=phone,
            amount=int(pack.price_kes),
            payment_id=str(payment.id),
            description='Token purchase',
        )

        if result['success']:
            stk_data = result['data']
            payment.mpesa_checkout_request_id = stk_data.get('CheckoutRequestID', '')
            payment.mpesa_merchant_request_id = stk_data.get('MerchantRequestID', '')
            payment.gateway_response = stk_data
            payment.save()
            return Response({
                'success': True,
                'payment_id': str(payment.id),
                'checkout_request_id': payment.mpesa_checkout_request_id,
                'message': f'Check your phone and enter your M-Pesa PIN to complete payment.',
            })
        else:
            payment.status = 'failed'
            payment.save()
            return Response({'error': True, 'message': result.get('error', 'M-Pesa payment failed')}, status=400)


class CheckPaymentStatusView(APIView):
    """Poll payment status (used by frontend to check if payment completed)."""
    permission_classes = [IsAuthenticated]

    def get(self, request, payment_id):
        try:
            payment = Payment.objects.get(id=payment_id, user=request.user)
        except Payment.DoesNotExist:
            return Response({'error': True, 'message': 'Payment not found'}, status=404)

        return Response({
            'status': payment.status,
            'credits_added': payment.credits_added,
            'credits': payment.credits_to_add if payment.credits_added else 0,
            'payment_method': payment.payment_method,
        })


@method_decorator(csrf_exempt, name='dispatch')
class MpesaCallbackView(APIView):
    """Safaricom calls this after STK push completes."""
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            body = request.data.get('Body', {})
            stk_callback = body.get('stkCallback', {})
            result_code = stk_callback.get('ResultCode')
            checkout_request_id = stk_callback.get('CheckoutRequestID', '')

            payment = Payment.objects.filter(
                mpesa_checkout_request_id=checkout_request_id
            ).first()

            if not payment:
                logger.warning(f"M-Pesa callback: no payment for CheckoutRequestID {checkout_request_id}")
                return Response({'ResultCode': 0, 'ResultDesc': 'Accepted'})

            payment.gateway_response = stk_callback

            if result_code == 0:
                items = stk_callback.get('CallbackMetadata', {}).get('Item', [])
                receipt = next((i['Value'] for i in items if i['Name'] == 'MpesaReceiptNumber'), '')
                payment.mpesa_receipt_number = receipt
                payment.status = 'completed'
                payment.completed_at = timezone.now()
                payment.save()

                if not payment.credits_added:
                    add_credits(
                        user=payment.user,
                        amount=payment.credits_to_add,
                        description=f'Purchased {payment.credits_to_add} credits via M-Pesa (Ref: {receipt})',
                        transaction_type='purchase',
                        payment=payment,
                    )
                    payment.credits_added = True
                    payment.save()
            else:
                payment.status = 'failed'
                payment.save()

        except Exception as e:
            logger.error(f"M-Pesa callback error: {e}", exc_info=True)

        return Response({'ResultCode': 0, 'ResultDesc': 'Accepted'})


class InitiateCardPaymentView(APIView):
    """Initiate Flutterwave card payment — returns a payment link."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        pack_id = request.data.get('pack_id')
        if not pack_id:
            return Response({'error': True, 'message': 'pack_id is required'}, status=400)

        try:
            pack = TokenPack.objects.get(id=pack_id, is_active=True)
        except TokenPack.DoesNotExist:
            return Response({'error': True, 'message': 'Token pack not found'}, status=404)

        payment = Payment.objects.create(
            user=request.user,
            token_pack=pack,
            payment_method='card',
            amount_kes=pack.price_kes,
            credits_to_add=pack.credits,
        )

        result = flutterwave_service.initiate_payment(
            user=request.user,
            token_pack=pack,
            payment_id=str(payment.id),
        )

        if result['success']:
            payment.flutterwave_tx_ref = result['tx_ref']
            payment.save()
            return Response({
                'success': True,
                'payment_id': str(payment.id),
                'payment_link': result['payment_link'],
            })
        else:
            payment.status = 'failed'
            payment.save()
            return Response({'error': True, 'message': result.get('error', 'Card payment failed')}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class FlutterwaveWebhookView(APIView):
    """Flutterwave webhook + redirect handler after card payment."""
    permission_classes = [AllowAny]

    def post(self, request):
        """Webhook from Flutterwave servers."""
        try:
            event = request.data.get('event', '')
            data = request.data.get('data', {})

            if event != 'charge.completed':
                return Response({'status': 'ignored'})

            tx_ref = data.get('tx_ref', '')
            tx_id = str(data.get('id', ''))

            payment = Payment.objects.filter(flutterwave_tx_ref=tx_ref).first()
            if not payment:
                return Response({'status': 'not_found'})

            if data.get('status') == 'successful' and not payment.credits_added:
                verify = flutterwave_service.verify_transaction(tx_id)
                if verify['success']:
                    payment.flutterwave_tx_id = tx_id
                    payment.status = 'completed'
                    payment.completed_at = timezone.now()
                    payment.gateway_response = data
                    payment.save()

                    add_credits(
                        user=payment.user,
                        amount=payment.credits_to_add,
                        description=f'Purchased {payment.credits_to_add} credits via card (Ref: {tx_ref})',
                        transaction_type='purchase',
                        payment=payment,
                    )
                    payment.credits_added = True
                    payment.save()

        except Exception as e:
            logger.error(f"Flutterwave webhook error: {e}", exc_info=True)

        return Response({'status': 'ok'})

    def get(self, request):
        """Redirect URL after user completes card payment on Flutterwave."""
        status_param = request.GET.get('status', '')
        tx_ref = request.GET.get('tx_ref', '')
        tx_id = request.GET.get('transaction_id', '')

        payment = Payment.objects.filter(flutterwave_tx_ref=tx_ref).first()

        if status_param == 'successful' and payment and not payment.credits_added:
            verify = flutterwave_service.verify_transaction(tx_id)
            if verify['success']:
                payment.flutterwave_tx_id = tx_id
                payment.status = 'completed'
                payment.completed_at = timezone.now()
                payment.save()
                add_credits(
                    user=payment.user,
                    amount=payment.credits_to_add,
                    description=f'Purchased {payment.credits_to_add} credits via card',
                    transaction_type='purchase',
                    payment=payment,
                )
                payment.credits_added = True
                payment.save()

        payment_id = str(payment.id) if payment else ''
        if status_param == 'successful':
            return HttpResponseRedirect(f"http://localhost:3001/payments/success?payment_id={payment_id}")
        return HttpResponseRedirect("http://localhost:3001/payments/failed")
