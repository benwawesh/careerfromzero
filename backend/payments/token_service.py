"""
Token Service
Core logic for deducting and adding credits to user accounts.
"""

import logging
from django.db import transaction
from .models import UserTokenBalance, TokenTransaction, AIFeatureCost

logger = logging.getLogger(__name__)

# Default costs if admin hasn't configured them yet
DEFAULT_COSTS = {
    'cv_write': 50,
    'cv_revamp': 30,
    'cv_customize': 20,
    'cover_letter': 20,
    'career_guidance': 10,
    'job_match': 5,
    'interview_question': 15,
}


def get_or_create_balance(user):
    """Get or create a token balance for a user."""
    balance, _ = UserTokenBalance.objects.get_or_create(user=user)
    return balance


def get_feature_cost(feature: str) -> int:
    """Get credit cost for an AI feature. Falls back to defaults."""
    try:
        cost = AIFeatureCost.objects.get(feature=feature, is_active=True)
        return cost.credits_cost
    except AIFeatureCost.DoesNotExist:
        return DEFAULT_COSTS.get(feature, 10)


def check_balance(user, feature: str) -> dict:
    """
    Check if user has enough credits for a feature.
    Returns: { 'has_enough': bool, 'balance': int, 'cost': int }
    """
    balance = get_or_create_balance(user)
    cost = get_feature_cost(feature)
    return {
        'has_enough': balance.has_enough(cost),
        'balance': balance.balance,
        'cost': cost,
    }


@transaction.atomic
def deduct_credits(user, feature: str, description: str = '') -> dict:
    """
    Deduct credits for an AI feature use.
    Returns: { 'success': bool, 'balance': int, 'cost': int, 'error': str }
    """
    balance = get_or_create_balance(user)
    cost = get_feature_cost(feature)

    if not balance.has_enough(cost):
        return {
            'success': False,
            'balance': balance.balance,
            'cost': cost,
            'error': f'Insufficient credits. You need {cost} credits but have {balance.balance}.'
        }

    balance.deduct(cost)

    TokenTransaction.objects.create(
        user=user,
        transaction_type='usage',
        credits=-cost,
        balance_after=balance.balance,
        description=description or f'Used: {feature}',
        feature=feature,
    )

    logger.info(f"Deducted {cost} credits from {user.email} for {feature}. New balance: {balance.balance}")
    return {
        'success': True,
        'balance': balance.balance,
        'cost': cost,
    }


@transaction.atomic
def add_credits(user, amount: int, description: str, transaction_type: str = 'purchase', payment=None) -> dict:
    """
    Add credits to a user's account.
    Returns: { 'success': bool, 'balance': int }
    """
    balance = get_or_create_balance(user)
    balance.add(amount)

    TokenTransaction.objects.create(
        user=user,
        transaction_type=transaction_type,
        credits=amount,
        balance_after=balance.balance,
        description=description,
        payment=payment,
    )

    logger.info(f"Added {amount} credits to {user.email}. New balance: {balance.balance}")
    return {
        'success': True,
        'balance': balance.balance,
    }
