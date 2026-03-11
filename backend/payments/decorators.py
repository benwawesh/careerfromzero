"""
Token deduction decorator for AI feature endpoints.
Usage:
    @require_tokens('cv_write')
    def my_view(request):
        ...
"""

from functools import wraps
from rest_framework.response import Response
from .token_service import deduct_credits, check_balance


def require_tokens(feature: str):
    """
    Decorator that checks and deducts tokens before running an AI feature.
    If user has insufficient balance, returns 402 Payment Required.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(self_or_request, *args, **kwargs):
            # Handle both function-based (request) and class-based (self, request) views
            request = self_or_request if hasattr(self_or_request, 'user') else args[0]

            check = check_balance(request.user, feature)
            if not check['has_enough']:
                return Response({
                    'error': True,
                    'message': f'Insufficient credits. You need {check["cost"]} credits but have {check["balance"]}. Please top up to continue.',
                    'balance': check['balance'],
                    'required': check['cost'],
                    'feature': feature,
                    'top_up_required': True,
                }, status=402)

            # Deduct tokens
            result = deduct_credits(request.user, feature)
            if not result['success']:
                return Response({
                    'error': True,
                    'message': result['error'],
                    'top_up_required': True,
                }, status=402)

            return view_func(self_or_request, *args, **kwargs)
        return wrapped
    return decorator
