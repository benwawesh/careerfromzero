"""
Job Application Workflow Views
API endpoints for complete job application workflow
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import get_user_model
import logging

from job_system.services.job_application_workflow import JobApplicationWorkflow
from job_system.models import Job, JobApplication, AutoApplicationBatch
from cv_builder.models import CV

User = get_user_model()
logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_cv_view(request):
    """
    Analyze user's CV
    
    POST /api/workflow/analyze-cv/
    Body: { "cv_id": "uuid" }
    """
    try:
        cv_id = request.data.get('cv_id')
        if not cv_id:
            return Response(
                {'error': 'cv_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        workflow = JobApplicationWorkflow()
        result = workflow.analyze_cv(request.user, cv_id)
        
        return Response(result)
    
    except Exception as e:
        logger.error(f"Error in analyze_cv_view: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def match_jobs_view(request):
    """
    Find jobs matching user's CV
    
    POST /api/workflow/match-jobs/
    Body: {
        "cv_id": "uuid",
        "filters": {
            "location": "Nairobi",
            "job_type": "full_time",
            "min_score": 70.0
        },
        "limit": 50,
        "min_score": 70.0
    }
    """
    try:
        cv_id = request.data.get('cv_id')
        if not cv_id:
            return Response(
                {'error': 'cv_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        filters = request.data.get('filters')
        limit = request.data.get('limit', 50)
        min_score = request.data.get('min_score', 70.0)
        
        workflow = JobApplicationWorkflow()
        result = workflow.match_jobs(request.user, cv_id, filters, limit, min_score)
        
        return Response(result)
    
    except Exception as e:
        logger.error(f"Error in match_jobs_view: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def batch_customize_view(request):
    """
    Generate customizations for selected jobs
    
    POST /api/workflow/batch-customize/
    Body: {
        "cv_id": "uuid",
        "job_ids": ["uuid1", "uuid2", "uuid3"],
        "options": {
            "generate_cv": true,
            "generate_cover_letter": false,
            "save_as_drafts": true
        }
    }
    """
    try:
        cv_id = request.data.get('cv_id')
        job_ids = request.data.get('job_ids', [])
        options = request.data.get('options')
        
        if not cv_id:
            return Response(
                {'error': 'cv_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not job_ids:
            return Response(
                {'error': 'job_ids is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        workflow = JobApplicationWorkflow()
        result = workflow.batch_customize(request.user, cv_id, job_ids, options)
        
        return Response(result)
    
    except Exception as e:
        logger.error(f"Error in batch_customize_view: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_application_batch_view(request):
    """
    Create application batch for approval
    
    POST /api/workflow/create-batch/
    Body: {
        "cv_id": "uuid",
        "job_ids": ["uuid1", "uuid2", "uuid3"],
        "customizations": [...]
    }
    """
    try:
        cv_id = request.data.get('cv_id')
        job_ids = request.data.get('job_ids', [])
        customizations = request.data.get('customizations', [])
        
        if not cv_id:
            return Response(
                {'error': 'cv_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        workflow = JobApplicationWorkflow()
        result = workflow.create_application_batch(
            request.user, cv_id, job_ids, customizations
        )
        
        return Response(result)
    
    except Exception as e:
        logger.error(f"Error in create_application_batch_view: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_progress_view(request):
    """
    Get current workflow progress
    
    GET /api/workflow/progress/
    """
    try:
        workflow = JobApplicationWorkflow()
        progress = workflow.get_progress(request.user.id)
        
        if progress:
            return Response(progress)
        else:
            return Response(
                {'status': 'no_progress'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    except Exception as e:
        logger.error(f"Error in get_progress_view: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_applications_view(request):
    """
    List user's job applications
    
    GET /api/workflow/applications/
    Query params: ?status=applied&company=Google
    """
    try:
        applications = JobApplication.objects.filter(user=request.user)
        
        # Filter by status
        status_filter = request.query_params.get('status')
        if status_filter:
            applications = applications.filter(status=status_filter)
        
        # Filter by company
        company_filter = request.query_params.get('company')
        if company_filter:
            applications = applications.filter(job__company__icontains=company_filter)
        
        # Order by created_at
        applications = applications.select_related('job', 'cv_version').order_by('-created_at')
        
        # Serialize
        applications_data = []
        for app in applications:
            applications_data.append({
                'id': str(app.id),
                'job_title': app.job.title,
                'company': app.job.company,
                'location': app.job.location,
                'status': app.status,
                'mode': app.mode,
                'application_date': app.application_date,
                'match_score': float(app.match_score) if app.match_score else None,
                'job_url': app.job.job_url,
                'created_at': app.created_at,
                'updated_at': app.updated_at
            })
        
        return Response({
            'count': len(applications_data),
            'applications': applications_data
        })
    
    except Exception as e:
        logger.error(f"Error in list_applications_view: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def application_detail_view(request, application_id):
    """
    Get application details
    
    GET /api/workflow/applications/{id}/
    """
    try:
        application = JobApplication.objects.get(
            id=application_id,
            user=request.user
        )
        
        data = {
            'id': str(application.id),
            'job': {
                'id': str(application.job.id),
                'title': application.job.title,
                'company': application.job.company,
                'location': application.job.location,
                'description': application.job.description,
                'requirements': application.job.requirements,
                'job_url': application.job.job_url
            },
            'status': application.status,
            'mode': application.mode,
            'cv_version': {
                'id': str(application.cv_version.id),
                'title': application.cv_version.title,
                'version_type': application.cv_version.version_type
            } if application.cv_version else None,
            'cover_letter': application.cover_letter,
            'application_date': application.application_date,
            'match_score': float(application.match_score) if application.match_score else None,
            'matched_skills': application.matched_skills,
            'missing_skills': application.missing_skills,
            'interview_date': application.interview_date,
            'interview_type': application.interview_type,
            'interview_notes': application.interview_notes,
            'follow_up_date': application.follow_up_date,
            'follow_up_completed': application.follow_up_completed,
            'notes': application.notes,
            'created_at': application.created_at,
            'updated_at': application.updated_at
        }
        
        return Response(data)
    
    except JobApplication.DoesNotExist:
        return Response(
            {'error': 'Application not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error in application_detail_view: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_application_view(request, application_id):
    """
    Update application details
    
    PUT /api/workflow/applications/{id}/
    Body: { "status": "applied", "notes": "..." }
    """
    try:
        application = JobApplication.objects.get(
            id=application_id,
            user=request.user
        )
        
        # Update fields
        if 'status' in request.data:
            application.status = request.data['status']
        
        if 'notes' in request.data:
            application.notes = request.data['notes']
        
        if 'interview_date' in request.data:
            application.interview_date = request.data['interview_date']
        
        if 'interview_type' in request.data:
            application.interview_type = request.data['interview_type']
        
        if 'interview_notes' in request.data:
            application.interview_notes = request.data['interview_notes']
        
        if 'follow_up_date' in request.data:
            application.follow_up_date = request.data['follow_up_date']
        
        if 'follow_up_completed' in request.data:
            application.follow_up_completed = request.data['follow_up_completed']
        
        application.save()
        
        return Response({
            'status': 'success',
            'message': 'Application updated'
        })
    
    except JobApplication.DoesNotExist:
        return Response(
            {'error': 'Application not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error in update_application_view: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_batches_view(request):
    """
    List user's application batches
    
    GET /api/workflow/batches/
    """
    try:
        batches = AutoApplicationBatch.objects.filter(user=request.user).order_by('-created_at')
        
        batches_data = []
        for batch in batches:
            batches_data.append({
                'id': str(batch.id),
                'status': batch.status,
                'total_jobs': batch.total_jobs,
                'approved_jobs': batch.approved_jobs,
                'rejected_jobs': batch.rejected_jobs,
                'successful_applications': batch.successful_applications,
                'failed_applications': batch.failed_applications,
                'progress_percentage': batch.progress_percentage,
                'started_at': batch.started_at,
                'completed_at': batch.completed_at,
                'created_at': batch.created_at
            })
        
        return Response({
            'count': len(batches_data),
            'batches': batches_data
        })
    
    except Exception as e:
        logger.error(f"Error in list_batches_view: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def batch_detail_view(request, batch_id):
    """
    Get batch details with items
    
    GET /api/workflow/batches/{id}/
    """
    try:
        batch = AutoApplicationBatch.objects.get(id=batch_id, user=request.user)
        
        # Get batch items
        items = batch.items.select_related('job').order_by('-match_score')
        
        items_data = []
        for item in items:
            items_data.append({
                'id': str(item.id),
                'job': {
                    'id': str(item.job.id),
                    'title': item.job.title,
                    'company': item.job.company,
                    'location': item.job.location
                },
                'user_approval_status': item.user_approval_status,
                'application_status': item.application_status,
                'match_score': float(item.match_score),
                'matched_skills': item.matched_skills,
                'missing_skills': item.missing_skills,
                'custom_cv': item.custom_cv,
                'custom_cover_letter': item.custom_cover_letter,
                'error_message': item.error_message,
                'applied_at': item.applied_at
            })
        
        return Response({
            'id': str(batch.id),
            'status': batch.status,
            'total_jobs': batch.total_jobs,
            'approved_jobs': batch.approved_jobs,
            'rejected_jobs': batch.rejected_jobs,
            'successful_applications': batch.successful_applications,
            'failed_applications': batch.failed_applications,
            'progress_percentage': batch.progress_percentage,
            'items': items_data,
            'started_at': batch.started_at,
            'completed_at': batch.completed_at,
            'created_at': batch.created_at
        })
    
    except AutoApplicationBatch.DoesNotExist:
        return Response(
            {'error': 'Batch not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error in batch_detail_view: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_batch_item_view(request, batch_id, item_id):
    """
    Approve or reject a batch item
    
    POST /api/workflow/batches/{batch_id}/items/{item_id}/approve/
    Body: { "approve": true }
    """
    try:
        batch = AutoApplicationBatch.objects.get(id=batch_id, user=request.user)
        item = batch.items.get(id=item_id)
        
        approve = request.data.get('approve', True)
        
        if approve:
            item.user_approval_status = 'approved'
        else:
            item.user_approval_status = 'rejected'
        
        item.save()
        
        # Update batch counts
        batch.approved_jobs = batch.items.filter(user_approval_status='approved').count()
        batch.rejected_jobs = batch.items.filter(user_approval_status='rejected').count()
        batch.save()
        
        return Response({
            'status': 'success',
            'message': f'Item {"approved" if approve else "rejected"}'
        })
    
    except AutoApplicationBatch.DoesNotExist:
        return Response(
            {'error': 'Batch not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error in approve_batch_item_view: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )