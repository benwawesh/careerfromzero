from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from decouple import config
from django.http import JsonResponse
from django.db import connection
import logging

logger = logging.getLogger(__name__)

# Obscure admin URL path for security
ADMIN_URL_PATH = config('ADMIN_URL_PATH', default='sys-mgmt-8832')


def health_check(request):
    """
    Health check endpoint for monitoring
    Checks database connection and returns system status
    """
    try:
        # Test database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        logger.info("Health check passed")
        return JsonResponse({
            'status': 'healthy',
            'database': 'connected',
            'debug_mode': settings.DEBUG
        }, status=200)
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JsonResponse({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e)
        }, status=503)


urlpatterns = [
    # Health check endpoint (no authentication required)
    path('api/health/', health_check, name='health_check'),
    
    # Regular API endpoints
    path('api/auth/', include('users.urls')),
    
    # CV Builder endpoints
    path('api/cv/', include('cv_builder.urls')),
    
    # Job System endpoints
    path('api/jobs/', include('job_system.urls')),
    
    # Payments & tokens
    path('api/payments/', include('payments.urls')),

    # AI Agents
    path('api/ai/', include('ai_agents.urls')),

    # Interview Simulator
    path('api/interview/', include('interview_system.urls')),

    # Custom admin panel with obscure URL
    # Admins login through the same endpoint as regular users
    # Admin status is determined by is_staff flag
    path(f'api/{ADMIN_URL_PATH}/', include('admin_panel.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)