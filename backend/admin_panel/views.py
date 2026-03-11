"""
Custom Admin Panel Views
Admin uses the same JWT authentication as regular users
Admin status is determined by is_staff flag
"""
from datetime import date
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from django.db.models import Q, Sum
from rest_framework.pagination import PageNumberPagination
from users.serializers import UserProfileSerializer, AdminUserSerializer
from users.permissions import IsAdminUser
from payments.models import TokenPack, AIFeatureCost, UserTokenBalance, Payment
from payments.token_service import add_credits
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


class CustomPagination(PageNumberPagination):
    """Custom pagination for admin panel"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_dashboard(request):
    """Admin dashboard overview"""
    stats = {
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
        'staff_users': User.objects.filter(is_staff=True).count(),
        'superusers': User.objects.filter(is_superuser=True).count(),
        'users_created_today': User.objects.filter(
            created_at__date=date.today()
        ).count(),
    }
    logger.info(f"Admin dashboard accessed by {request.user.email}")
    return Response({
        'message': 'Admin Dashboard',
        'stats': stats
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def list_users(request):
    """List all users with search and pagination (admin only)"""
    # Get query parameters
    search = request.query_params.get('search', '')
    is_active = request.query_params.get('is_active')
    is_staff = request.query_params.get('is_staff')
    
    # Build query
    queryset = User.objects.all()
    
    # Search functionality
    if search:
        queryset = queryset.filter(
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(username__icontains=search)
        )
    
    # Filter by status
    if is_active is not None:
        queryset = queryset.filter(is_active=is_active.lower() == 'true')
    
    if is_staff is not None:
        queryset = queryset.filter(is_staff=is_staff.lower() == 'true')
    
    # Order by most recent
    queryset = queryset.order_by('-created_at')
    
    # Paginate results
    paginator = CustomPagination()
    paginated_queryset = paginator.paginate_queryset(queryset, request)
    
    serializer = UserProfileSerializer(paginated_queryset, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAdminUser])
def manage_user(request, user_id):
    """Manage a specific user (admin only)"""
    try:
        user = User.objects.get(id=user_id)
        
        if request.method == 'DELETE':
            username = user.username
            user.delete()
            logger.info(f"User {username} deleted by admin {request.user.email}")
            return Response({'message': 'User deleted successfully'}, status=status.HTTP_200_OK)
        
        if request.method == 'GET':
            serializer = UserProfileSerializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        if request.method == 'PUT':
            serializer = AdminUserSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                logger.info(f"User {user.username} updated by admin {request.user.email}")
                return Response({
                    'message': 'User updated successfully',
                    'user': UserProfileSerializer(user).data
                }, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except User.DoesNotExist:
        logger.warning(f"Attempt to access non-existent user {user_id} by admin {request.user.email}")
        return Response({
            'error': 'User not found',
            'message': f'User with ID {user_id} does not exist'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error managing user {user_id}: {str(e)}")
        return Response({
            'error': 'Internal server error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def bulk_delete_users(request):
    """Bulk delete users (admin only)"""
    user_ids = request.data.get('user_ids', [])

    if not user_ids:
        return Response({
            'error': 'No user IDs provided',
            'message': 'Please provide a list of user IDs to delete'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        users = User.objects.filter(id__in=user_ids)
        count = users.count()
        users.delete()

        logger.info(f"Bulk deleted {count} users by admin {request.user.email}")
        return Response({
            'message': f'Successfully deleted {count} users',
            'deleted_count': count
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error in bulk delete: {str(e)}")
        return Response({
            'error': 'Failed to delete users',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ─── Token Pack Management ────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAdminUser])
def manage_token_packs(request):
    """List all token packs or create a new one."""
    if request.method == 'GET':
        packs = TokenPack.objects.all()
        return Response([
            {
                'id': p.id,
                'name': p.name,
                'description': p.description,
                'credits': p.credits,
                'price_kes': float(p.price_kes),
                'is_active': p.is_active,
                'is_featured': p.is_featured,
                'sort_order': p.sort_order,
            }
            for p in packs
        ])

    # POST — create new pack
    data = request.data
    pack = TokenPack.objects.create(
        name=data.get('name', ''),
        description=data.get('description', ''),
        credits=int(data.get('credits', 0)),
        price_kes=float(data.get('price_kes', 0)),
        is_active=data.get('is_active', True),
        is_featured=data.get('is_featured', False),
        sort_order=int(data.get('sort_order', 0)),
    )
    logger.info(f"Token pack '{pack.name}' created by admin {request.user.email}")
    return Response({'message': 'Pack created', 'id': pack.id}, status=201)


@api_view(['PUT', 'DELETE'])
@permission_classes([IsAdminUser])
def manage_token_pack(request, pack_id):
    """Update or delete a specific token pack."""
    try:
        pack = TokenPack.objects.get(id=pack_id)
    except TokenPack.DoesNotExist:
        return Response({'error': True, 'message': 'Pack not found'}, status=404)

    if request.method == 'DELETE':
        pack.delete()
        return Response({'message': 'Pack deleted'})

    # PUT — update pack
    data = request.data
    for field in ['name', 'description', 'credits', 'price_kes', 'is_active', 'is_featured', 'sort_order']:
        if field in data:
            setattr(pack, field, data[field])
    pack.save()
    logger.info(f"Token pack '{pack.name}' updated by admin {request.user.email}")
    return Response({'message': 'Pack updated'})


@api_view(['GET', 'PUT'])
@permission_classes([IsAdminUser])
def manage_feature_costs(request):
    """List or update AI feature costs."""
    if request.method == 'GET':
        costs = AIFeatureCost.objects.all()
        return Response([
            {
                'feature': c.feature,
                'display_name': c.get_feature_display(),
                'credits_cost': c.credits_cost,
                'is_active': c.is_active,
            }
            for c in costs
        ])

    # PUT — update costs (send list of {feature, credits_cost})
    updates = request.data.get('costs', [])
    for item in updates:
        AIFeatureCost.objects.filter(feature=item['feature']).update(
            credits_cost=item['credits_cost']
        )
    logger.info(f"Feature costs updated by admin {request.user.email}")
    return Response({'message': f'Updated {len(updates)} feature costs'})


@api_view(['POST'])
@permission_classes([IsAdminUser])
def credit_user_tokens(request):
    """Manually add credits to a user's account."""
    user_id = request.data.get('user_id')
    amount = request.data.get('amount')
    reason = request.data.get('reason', 'Admin credit')

    if not user_id or not amount:
        return Response({'error': True, 'message': 'user_id and amount are required'}, status=400)

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': True, 'message': 'User not found'}, status=404)

    result = add_credits(
        user=user,
        amount=int(amount),
        description=f'Admin credit: {reason}',
        transaction_type='bonus',
    )
    logger.info(f"Admin {request.user.email} credited {amount} tokens to {user.email}")
    return Response({
        'message': f'Added {amount} credits to {user.email}',
        'new_balance': result['balance'],
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def token_stats(request):
    """Token and payment statistics for admin dashboard."""
    total_revenue = Payment.objects.filter(status='completed').aggregate(
        total=Sum('amount_kes')
    )['total'] or 0

    total_credits_sold = Payment.objects.filter(
        status='completed', credits_added=True
    ).aggregate(total=Sum('credits_to_add'))['total'] or 0

    return Response({
        'total_revenue_kes': float(total_revenue),
        'total_credits_sold': total_credits_sold,
        'total_payments': Payment.objects.filter(status='completed').count(),
        'pending_payments': Payment.objects.filter(status='pending').count(),
        'users_with_balance': UserTokenBalance.objects.filter(balance__gt=0).count(),
    })
