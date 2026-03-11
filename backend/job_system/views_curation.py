"""
Curation Views
Handle AI curation workflow start
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
import threading
import logging

from cv_builder.models import CV, CVData, CVVersion
from job_system.models import Job, JobMatch
from ai_agents.job_matcher_agent import JobMatcherAgent

User = get_user_model()
logger = logging.getLogger(__name__)


class StartCurationView(APIView):
    """
    Start AI job curation by either:
    1. Using an existing CV
    2. Creating a new CV from manual data entry
    
    This endpoint sets the current CV for curation and triggers AI job matching using the JobMatcherAgent.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Start curation
        
        Expected data for Option A (Existing CV):
        {
            "existing_cv_id": "uuid"
        }
        
        Expected data for Option B (Manual CV):
        {
            "full_name": "John Doe",
            "email": "john@example.com",
            "phone": "+1234567890",
            "location": "Nairobi, Kenya",
            "job_title": "Software Engineer",
            "years_experience": 5,
            "skills": ["Python", "Django", "React"],
            "education": [...],
            "work_experience": [...],
            "summary": "Experienced software engineer...",
            "linkedin_url": "",
            "github_url": "",
            "website_url": "",
            "save_as_cv": true
        }
        """
        user = request.user
        data = request.data
        cv = None

        # Option A: Use existing CV
        if 'existing_cv_id' in data:
            cv_id = data.get('existing_cv_id')
            logger.info(f"Looking for CV {cv_id} for user {user.email}")
            
            # Debug: Check if CV exists at all
            all_cvs = CV.objects.filter(id=cv_id)
            if all_cvs.exists():
                for test_cv in all_cvs:
                    logger.warning(f"CV {cv_id} EXISTS but user={test_cv.user.email}, is_active={test_cv.is_active}")
            else:
                logger.warning(f"CV {cv_id} DOES NOT EXIST in database")
            
            try:
                cv = CV.objects.get(id=cv_id, user=user, is_active=True)
                logger.info(f"Found CV {cv.id}: title='{cv.title}', is_active={cv.is_active}, is_parsed={cv.is_parsed}")
                
                # Check if CVData exists
                if hasattr(cv, 'data'):
                    logger.info(f"CV {cv.id} has data, status={cv.data.parsing_status}")
                else:
                    logger.warning(f"CV {cv.id} does NOT have CVData yet")
                
            except CV.DoesNotExist:
                logger.error(f"CV {cv_id} not found for user {user.email}")
                return Response({
                    'success': False,
                    'error': 'CV not found or you do not have access to it'
                }, status=status.HTTP_404_NOT_FOUND)

        # Option B: Create CV from manual data
        else:
            # Validate required fields
            required_fields = ['full_name', 'email', 'job_title', 'skills']
            for field in required_fields:
                if field not in data or not data[field]:
                    return Response({
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }, status=status.HTTP_400_BAD_REQUEST)

            try:
                # Create CV record
                save_as_cv = data.get('save_as_cv', True)
                cv = CV.objects.create(
                    user=user,
                    title=f"{data['job_title']} - {data['full_name']}",
                    file=None,
                    original_filename='',
                    file_type='MANUAL',
                    file_size=0,
                    is_temporary=not save_as_cv,
                    is_parsed=True,
                    is_analyzed=False
                )

                # Create CVData record
                cv_data = CVData.objects.create(
                    cv=cv,
                    raw_text=self._build_cv_text(data),
                    email=data.get('email', ''),
                    phone=data.get('phone', ''),
                    location=data.get('location', ''),
                    linkedin_url=data.get('linkedin_url', ''),
                    github_url=data.get('github_url', ''),
                    website_url=data.get('website_url', ''),
                    summary=data.get('summary', ''),
                    skills=data.get('skills', []),
                    experience=data.get('work_experience', []),
                    education=data.get('education', []),
                    projects=data.get('projects', []),
                    certifications=data.get('certifications', []),
                    languages=data.get('languages', []),
                    interests=data.get('interests', []),
                    parsing_status='completed'
                )

                logger.info(f"Created manual CV {cv.id} for curation")

            except Exception as e:
                logger.error(f"Failed to create CV: {str(e)}", exc_info=True)
                return Response({
                    'success': False,
                    'error': f'Failed to create CV: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Trigger AI matching in background using JobMatcherAgent
        if cv and hasattr(cv, 'data') and cv.data:
            self._trigger_ai_matching(cv, user)
        elif cv and not hasattr(cv, 'data'):
            # CV might not have data yet, wait for parsing
            logger.warning(f"CV {cv.id} has no data yet, skipping AI matching")
        
        return Response({
            'success': True,
            'cv_id': str(cv.id),
            'cv_title': cv.title,
            'is_temporary': cv.is_temporary,
            'message': 'AI job matching started. Check back in a few moments.'
        }, status=status.HTTP_200_OK)

    def _build_cv_text(self, data: dict) -> str:
        """Build CV text from manual data"""
        parts = []
        
        parts.append(f"{data.get('full_name', '')}")
        parts.append(f"{data.get('email', '')}")
        parts.append(f"{data.get('phone', '')}")
        parts.append(f"{data.get('location', '')}")
        
        if data.get('summary'):
            parts.append(f"\nSUMMARY:\n{data['summary']}")
        
        if data.get('skills'):
            parts.append(f"\nSKILLS:\n{', '.join(data['skills'])}")
        
        if data.get('work_experience'):
            parts.append("\nWORK EXPERIENCE:")
            for exp in data['work_experience']:
                parts.append(f"- {exp.get('company', '')} - {exp.get('role', '')}")
                if exp.get('description'):
                    parts.append(f"  {exp['description']}")
        
        if data.get('education'):
            parts.append("\nEDUCATION:")
            for edu in data['education']:
                parts.append(f"- {edu.get('degree', '')} at {edu.get('institution', '')}")
        
        return '\n'.join(parts)

    def _trigger_ai_matching(self, cv, user):
        """Trigger AI job matching in background thread using JobMatcherAgent"""
        def run_matching():
            from django.db import close_old_connections
            try:
                logger.info(f"Starting AI matching for CV {cv.id} using JobMatcherAgent")
                
                # Initialize AI agent
                matcher = JobMatcherAgent()
                
                # Get CV data
                cv_data = cv.data
                if not cv_data:
                    logger.warning(f"CV {cv.id} has no data, skipping matching")
                    return

                # Try to get existing CVVersion or create one
                cv_version = CVVersion.objects.filter(cv=cv, is_current=True).first()
                if not cv_version:
                    # Create an original version from the CV data
                    cv_version = CVVersion.objects.create(
                        cv=cv,
                        version_number=1,
                        title="Original",
                        description="Original CV content",
                        version_type='original',
                        optimized_text=cv_data.raw_text or "",
                        is_current=True
                    )
                    logger.info(f"Created CV version {cv_version.id} for matching")

                # Get all active jobs
                jobs = Job.objects.filter(is_active=True)
                logger.info(f"Processing {jobs.count()} jobs for AI matching")

                matches_created = 0
                matches_updated = 0

                for job in jobs:
                    try:
                        # Use AI agent to calculate match
                        match_data = matcher.calculate_match(user, job, cv_version)
                        
                        if 'error' in match_data:
                            logger.warning(f"AI matching failed for job {job.id}: {match_data['error']}")
                            continue
                        
                        # Save match result
                        matcher.save_match_result(user, job, cv_version, match_data)
                        matches_created += 1
                        
                    except Exception as e:
                        logger.error(f"Error matching job {job.id}: {str(e)}", exc_info=True)
                        continue

                logger.info(f"AI matching completed for CV {cv.id}. Created/Updated {matches_created} matches")

            except Exception as e:
                logger.error(f"AI matching failed for CV {cv.id}: {str(e)}", exc_info=True)
            finally:
                close_old_connections()

        # Start background thread
        thread = threading.Thread(target=run_matching, daemon=True)
        thread.start()