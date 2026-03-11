"""
Job System URL Configuration
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    JobViewSet, SavedJobViewSet, JobApplicationViewSet,
    JobMatchViewSet, JobSearchViewSet,
    JobCategoryViewSet, UserApplicationPreferenceViewSet,
    AutoApplicationBatchViewSet, AutoApplicationItemViewSet,
    RealTimeSearchViewSet
)
from .views_workflow import (
    analyze_cv_view, match_jobs_view, batch_customize_view,
    create_application_batch_view, get_progress_view,
    list_applications_view, application_detail_view, update_application_view,
    list_batches_view, batch_detail_view, approve_batch_item_view
)
from .views_curation import StartCurationView

router = DefaultRouter()
router.register(r'jobs', JobViewSet, basename='job')
router.register(r'saved', SavedJobViewSet, basename='savedjob')
router.register(r'applications', JobApplicationViewSet, basename='jobapplication')
router.register(r'matches', JobMatchViewSet, basename='jobmatch')
router.register(r'searches', JobSearchViewSet, basename='jobsearch')
router.register(r'categories', JobCategoryViewSet, basename='jobcategory')
router.register(r'preferences', UserApplicationPreferenceViewSet, basename='userpreference')
router.register(r'batches', AutoApplicationBatchViewSet, basename='autobatch')
router.register(r'items', AutoApplicationItemViewSet, basename='autoitem')
router.register(r'realtime', RealTimeSearchViewSet, basename='realtimesearch')

# Workflow endpoints
urlpatterns = [
    path('', include(router.urls)),
    path('workflow/analyze-cv/', analyze_cv_view, name='workflow_analyze_cv'),
    path('workflow/match-jobs/', match_jobs_view, name='workflow_match_jobs'),
    path('workflow/batch-customize/', batch_customize_view, name='workflow_batch_customize'),
    path('workflow/create-batch/', create_application_batch_view, name='workflow_create_batch'),
    path('workflow/progress/', get_progress_view, name='workflow_progress'),
    path('workflow/applications/', list_applications_view, name='workflow_list_applications'),
    path('workflow/applications/<uuid:application_id>/', application_detail_view, name='workflow_application_detail'),
    path('workflow/applications/<uuid:application_id>/update/', update_application_view, name='workflow_update_application'),
    path('workflow/batches/', list_batches_view, name='workflow_list_batches'),
    path('workflow/batches/<uuid:batch_id>/', batch_detail_view, name='workflow_batch_detail'),
    path('workflow/batches/<uuid:batch_id>/items/<uuid:item_id>/approve/', approve_batch_item_view, name='workflow_approve_item'),
    path('workflow/start-curation/', StartCurationView.as_view(), name='workflow_start_curation'),
]
