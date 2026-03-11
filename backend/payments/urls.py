from django.urls import path
from .views import (
    TokenPacksView, TokenBalanceView,
    InitiateMpesaPaymentView, CheckPaymentStatusView, MpesaCallbackView,
    InitiateCardPaymentView, FlutterwaveWebhookView,
)

urlpatterns = [
    path('packs/', TokenPacksView.as_view(), name='token_packs'),
    path('balance/', TokenBalanceView.as_view(), name='token_balance'),

    # M-Pesa
    path('mpesa/initiate/', InitiateMpesaPaymentView.as_view(), name='mpesa_initiate'),
    path('mpesa/callback/', MpesaCallbackView.as_view(), name='mpesa_callback'),

    # Card (Flutterwave)
    path('card/initiate/', InitiateCardPaymentView.as_view(), name='card_initiate'),
    path('card/webhook/', FlutterwaveWebhookView.as_view(), name='card_webhook'),

    # Shared
    path('status/<uuid:payment_id>/', CheckPaymentStatusView.as_view(), name='payment_status'),
]
