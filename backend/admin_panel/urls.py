"""
Admin Panel URLs
Uses obscure path for security
"""
from django.urls import path
from .views import (
    admin_dashboard, list_users, manage_user, bulk_delete_users,
    manage_token_packs, manage_token_pack, manage_feature_costs,
    credit_user_tokens, token_stats,
)

app_name = 'admin_panel'

urlpatterns = [
    path('', admin_dashboard, name='dashboard'),
    path('users/', list_users, name='list_users'),
    path('users/bulk-delete/', bulk_delete_users, name='bulk_delete_users'),
    path('users/<int:user_id>/', manage_user, name='manage_user'),

    # Token management
    path('tokens/packs/', manage_token_packs, name='token_packs'),
    path('tokens/packs/<int:pack_id>/', manage_token_pack, name='token_pack'),
    path('tokens/feature-costs/', manage_feature_costs, name='feature_costs'),
    path('tokens/credit-user/', credit_user_tokens, name='credit_user'),
    path('tokens/stats/', token_stats, name='token_stats'),
]
