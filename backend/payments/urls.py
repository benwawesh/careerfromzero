from django.urls import path
from .views import (
    TokenPacksView, TokenBalanceView,
    InitiateMpesaPaymentView, CheckPaymentStatusView, MpesaCallbackView,
    InitiateCardPaymentView, PesaPalCallbackView, PesaPalIPNView,
)

urlpatterns = [
    path('packs/', TokenPacksView.as_view(), name='token_packs'),
    path('balance/', TokenBalanceView.as_view(), name='token_balance'),

    # M-Pesa
    path('mpesa/initiate/', InitiateMpesaPaymentView.as_view(), name='mpesa_initiate'),
    path('mpesa/callback/', MpesaCallbackView.as_view(), name='mpesa_callback'),

    # Card (PesaPal)
    path('card/initiate/', InitiateCardPaymentView.as_view(), name='card_initiate'),
    path('card/callback/', PesaPalCallbackView.as_view(), name='card_callback'),
    path('card/ipn/', PesaPalIPNView.as_view(), name='card_ipn'),

    # Shared
    path('status/<uuid:payment_id>/', CheckPaymentStatusView.as_view(), name='payment_status'),
]
