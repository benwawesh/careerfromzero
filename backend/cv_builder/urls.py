"""
CV Builder URLs
Handles CV upload, parsing, and management endpoints
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CVUploadView,
    CVListView,
    CVDetailView,
    CVAnalysisView,
    CVVersionViewSet,
    JobDescriptionViewSet,
    analyze_cv,
    match_cv_to_job,
    optimize_cv,
    download_cv_version_pdf,
    view_cv_version
)

router = DefaultRouter()
router.register(r'versions', CVVersionViewSet, basename='cvversion')
router.register(r'jobs', JobDescriptionViewSet, basename='jobdescription')

app_name = 'cv_builder'

urlpatterns = [
    # CV upload
    path('upload/', CVUploadView.as_view(), name='upload'),
    
    # CV listing
    path('', CVListView.as_view(), name='list'),
    
    # CV detail (retrieve, update, delete)
    path('<uuid:id>/', CVDetailView.as_view(), name='detail'),
    
    # CV analysis
    path('<uuid:id>/analysis/', CVAnalysisView.as_view(), name='analysis'),
    path('<uuid:cv_id>/analyze/', analyze_cv, name='analyze'),

    # CV operations
    path('<uuid:cv_id>/match/<int:job_id>/', match_cv_to_job, name='match'),
    path('<uuid:cv_id>/optimize/', optimize_cv, name='optimize'),
    path('<uuid:cv_id>/optimize/<int:job_id>/', optimize_cv, name='optimize_for_job'),
    
    # CV Version operations (must come before ViewSet routes)
    path('<uuid:cv_id>/versions/<int:version_id>/download/', download_cv_version_pdf, name='download_version_pdf'),
    path('<uuid:cv_id>/versions/<int:version_id>/', view_cv_version, name='view_version'),
    
    # ViewSet routes (versions, jobs)
    path('<uuid:cv_id>/', include(router.urls)),
]
