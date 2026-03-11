"""
CV Builder Views
Handles CV upload, parsing, and management
"""

from rest_framework import generics, status, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework.pagination import PageNumberPagination
from django.http import HttpResponse

from .models import CV, CVData, CVAnalysis, CVVersion, JobDescription
from .serializers import (
    CVSerializer, CVListSerializer, CVDetailSerializer,
    CVDataSerializer, CVAnalysisSerializer,
    CVVersionSerializer, CVVersionCreateSerializer,
    JobDescriptionSerializer
)
from .services.cv_parser import CVParser
from .services.pdf_generator import CVPDFGenerator
from ai_agents.services.ollama_service import ollama_service
import json, re, logging, threading

logger = logging.getLogger(__name__)


class CustomPagination(PageNumberPagination):
    """Custom pagination for CV listings"""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


class CVUploadView(generics.CreateAPIView):
    """Upload a new CV"""
    serializer_class = CVSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def perform_create(self, serializer):
        # Associate CV with current user
        serializer.save(user=self.request.user)
        logger.info(f"CV uploaded by user {self.request.user.email}")
    
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        
        # Trigger parsing asynchronously (for now, synchronous)
        cv = CV.objects.get(id=response.data['id'])
        try:
            self._parse_cv(cv)
        except Exception as e:
            logger.error(f"Failed to parse CV {cv.id}: {str(e)}")
        
        return Response(
            CVSerializer(cv, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )
    
    def _parse_cv(self, cv):
        """Parse CV file and extract data"""
        try:
            logger.info(f"Parsing CV {cv.id}: {cv.file.path}")
            
            # Create CVData entry with processing status
            cv_data = CVData.objects.create(
                cv=cv,
                raw_text="",
                parsing_status='processing'
            )
            
            # Parse CV file
            parser = CVParser(cv.file.path, cv.file_type)
            parsed_data = parser.parse()
            
            # Update CVData with parsed information
            cv_data.raw_text = parsed_data.get('raw_text', '')
            cv_data.email = parsed_data.get('email')
            cv_data.phone = parsed_data.get('phone')
            cv_data.location = parsed_data.get('location')
            cv_data.linkedin_url = parsed_data.get('linkedin_url')
            cv_data.github_url = parsed_data.get('github_url')
            cv_data.website_url = parsed_data.get('website_url')
            cv_data.summary = parsed_data.get('summary')
            cv_data.skills = parsed_data.get('skills', [])
            cv_data.experience = parsed_data.get('experience', [])
            cv_data.education = parsed_data.get('education', [])
            cv_data.projects = parsed_data.get('projects', [])
            cv_data.certifications = parsed_data.get('certifications', [])
            cv_data.languages = parsed_data.get('languages', [])
            cv_data.interests = parsed_data.get('interests', [])
            cv_data.parsing_status = 'completed'
            cv_data.save()
            
            # Update CV status
            cv.is_parsed = True
            cv.save()
            
            logger.info(f"Successfully parsed CV {cv.id}")
            
        except Exception as e:
            logger.error(f"Error parsing CV {cv.id}: {str(e)}", exc_info=True)
            if hasattr(cv, 'data'):
                cv.data.parsing_status = 'failed'
                cv.data.parsing_error = str(e)
                cv.data.save()
            raise


class CVListView(generics.ListAPIView):
    """List user's CVs"""
    serializer_class = CVListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination
    
    def get_queryset(self):
        """Get CVs for current user"""
        return CV.objects.filter(user=self.request.user, is_active=True)


class CVDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, or delete a specific CV"""
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return CVDetailSerializer
        return CVSerializer
    
    def get_queryset(self):
        return CV.objects.filter(user=self.request.user)
    
    def retrieve(self, request, *args, **kwargs):
        """Get CV details"""
        cv = self.get_object()
        serializer = self.get_serializer(cv)
        return Response(serializer.data)
    
    def update(self, request, *args, **kwargs):
        """Update CV title"""
        cv = self.get_object()
        serializer = self.get_serializer(cv, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        logger.info(f"CV {cv.id} updated by user {request.user.email}")
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete CV"""
        cv = self.get_object()
        cv.delete()  # Uses soft delete
        logger.info(f"CV {cv.id} soft-deleted by user {request.user.email}")
        return Response(
            {'message': 'CV deleted successfully'},
            status=status.HTTP_200_OK
        )


class CVAnalysisView(generics.RetrieveAPIView):
    """Get CV analysis"""
    serializer_class = CVAnalysisSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_object(self):
        """Get CV analysis"""
        from rest_framework.exceptions import ValidationError, NotFound
        cv = get_object_or_404(CV, id=self.kwargs['id'], user=self.request.user)

        if not cv.is_parsed:
            raise ValidationError({'error': 'CV has not been parsed yet'})

        try:
            return cv.data.analysis
        except CVAnalysis.DoesNotExist:
            raise NotFound({'error': 'Analysis not available. Please analyze the CV first.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_cv(request, cv_id):
    """
    Trigger AI analysis of a CV using the CVAnalysisCrew (2 agents).

    Returns 202 immediately. The crew runs in a background thread so the
    request doesn't hang. Frontend polls GET /api/cv/{id}/ until
    is_analyzed=True, then loads the analysis.
    """
    cv = get_object_or_404(CV, id=cv_id, user=request.user)

    if not cv.is_parsed:
        return Response(
            {'error': 'CV has not been parsed yet'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Mark analysis as in-progress immediately
    try:
        analysis = cv.data.analysis
        analysis.analysis_status = 'processing'
        analysis.save()
    except CVAnalysis.DoesNotExist:
        analysis = CVAnalysis.objects.create(
            cv_data=cv.data,
            analysis_status='processing'
        )

    cv_text = cv.data.raw_text

    def run_analysis():
        from django.db import connection
        try:
            prompt = f"""You are a senior ATS consultant and CV expert. Analyse this CV.
Return ONLY a valid JSON object — no explanation, no markdown fences.

{{
  "ats_score": <integer 0-100>,
  "overall_score": <integer 0-100>,
  "content_quality_score": <integer 0-100>,
  "formatting_score": <integer 0-100>,
  "strengths": ["strength 1", "strength 2", "strength 3"],
  "weaknesses": ["weakness 1", "weakness 2", "weakness 3"],
  "suggestions": ["suggestion 1", "suggestion 2", "suggestion 3"],
  "missing_keywords": ["keyword 1", "keyword 2", "keyword 3"],
  "missing_sections": ["section 1"]
}}

CV TEXT:
{cv_text[:800]}

Return ONLY the JSON object."""

            raw = ollama_service.generate(prompt=prompt, temperature=0.2, max_tokens=600)
            logger.info(f"Ollama analysis raw output length: {len(raw)} chars")

            # Extract JSON from response
            cleaned = re.sub(r'```(?:json)?\s*', '', raw).strip().rstrip('`').strip()
            match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            result = json.loads(match.group()) if match else {}

            allowed = {
                'ats_score', 'overall_score', 'content_quality_score',
                'formatting_score', 'strengths', 'weaknesses', 'suggestions',
                'formatting_issues', 'missing_keywords', 'missing_sections',
            }
            for key, value in result.items():
                if key in allowed:
                    setattr(analysis, key, value)
            analysis.analysis_status = 'completed'
            analysis.save()

            cv.is_analyzed = True
            cv.save()
            logger.info(f"CV analysis completed for CV {cv_id}")
        except Exception as e:
            logger.error(f"CV analysis background thread failed: {e}", exc_info=True)
            analysis.analysis_status = 'failed'
            analysis.analysis_error = str(e)
            analysis.save()
        finally:
            connection.close()

    thread = threading.Thread(target=run_analysis, daemon=True)
    thread.start()

    return Response(
        {
            'status': 'processing',
            'message': 'Analysis started. Poll GET /api/cv/{id}/ until is_analyzed=true.',
            'agents': ['CV Parser Agent', 'ATS Analyst Agent'],
        },
        status=status.HTTP_202_ACCEPTED
    )


class CVVersionViewSet(viewsets.ModelViewSet):
    """Manage CV versions"""
    serializer_class = CVVersionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CVVersionCreateSerializer
        return CVVersionSerializer
    
    def get_queryset(self):
        """Get versions for a specific CV"""
        cv_id = self.kwargs.get('cv_id')
        if cv_id:
            return CVVersion.objects.filter(cv_id=cv_id, cv__user=self.request.user)
        return CVVersion.objects.filter(cv__user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        """Create new CV version"""
        cv_id = kwargs.get('cv_id')
        cv = get_object_or_404(CV, id=cv_id, user=request.user)
        
        # Auto-generate version number if not provided
        request_data = request.data.copy()
        if 'version_number' not in request_data:
            max_version = CVVersion.objects.filter(cv=cv).count()
            request_data['version_number'] = max_version + 1
        
        serializer = self.get_serializer(data=request_data)
        serializer.is_valid(raise_exception=True)
        serializer.save(cv=cv)
        
        logger.info(f"CV version created for CV {cv_id}")
        
        return Response(
            CVVersionSerializer(serializer.instance).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def set_current(self, request, cv_id=None, pk=None):
        """Set this version as current"""
        version = self.get_object()
        version.is_current = True
        version.save()
        
        return Response(
            {'message': 'Version set as current'},
            status=status.HTTP_200_OK
        )


class JobDescriptionViewSet(viewsets.ModelViewSet):
    """Manage job descriptions"""
    serializer_class = JobDescriptionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get job descriptions for current user"""
        return JobDescription.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """Associate job description with current user"""
        serializer.save(user=self.request.user)
        logger.info(f"Job description created by user {self.request.user.email}")
    
    @action(detail=True, methods=['post'])
    def parse(self, request, pk=None):
        """Parse job description and extract keywords"""
        job = self.get_object()
        
        agent = CVAgent()
        result = agent.extract_job_keywords(job.description)
        job.keywords = result.get('keywords', [])
        job.required_skills = result.get('required_skills', [])
        job.preferred_skills = result.get('preferred_skills', [])
        job.is_parsed = True
        job.save()
        
        return Response(
            {'message': 'Job description parsed successfully'},
            status=status.HTTP_200_OK
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def match_cv_to_job(request, cv_id, job_id):
    """Match CV to job description"""
    try:
        cv = get_object_or_404(CV, id=cv_id, user=request.user)
        job = get_object_or_404(JobDescription, id=job_id, user=request.user)
        
        if not cv.is_parsed:
            return Response(
                {'error': 'CV has not been parsed yet'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not job.is_parsed:
            return Response(
                {'error': 'Job description has not been parsed yet'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Normalize to lowercase for case-insensitive matching
        cv_skills = {s.lower().strip() for s in cv.data.skills}
        job_skills = {s.lower().strip() for s in job.required_skills}
        matched_skills = cv_skills & job_skills
        
        match_score = int((len(matched_skills) / len(job_skills)) * 100) if job_skills else 0
        
        result = {
            'match_score': match_score,
            'matched_skills': list(matched_skills),
            'missing_skills': list(job_skills - cv_skills),
            'additional_skills': list(cv_skills - job_skills),
            'suggestions': [
                'Add Python experience to your CV' if 'Python' not in cv_skills else None,
                'Include SQL projects' if 'SQL' not in cv_skills else None,
                'Highlight AWS certifications' if 'AWS' not in cv_skills else None
            ]
        }
        
        # Filter out None suggestions
        result['suggestions'] = [s for s in result['suggestions'] if s]
        
        logger.info(f"CV {cv_id} matched to job {job_id} with score {match_score}")
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error matching CV to job: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Failed to match CV to job', 'detail': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def optimize_cv(request, cv_id, job_id=None):
    """
    Tailor a CV using the CVTailoringCrew (3 agents: Job Analyst → Gap Analyst → CV Writer).

    Returns 202 immediately. The crew runs in a background thread.
    Frontend polls GET /api/cv/{id}/ and checks versions[] for the new entry.
    """
    cv = get_object_or_404(CV, id=cv_id, user=request.user)

    if not cv.is_parsed:
        return Response(
            {'error': 'CV has not been parsed yet'},
            status=status.HTTP_400_BAD_REQUEST
        )

    job = get_object_or_404(JobDescription, id=job_id, user=request.user) if job_id else None

    cv_text = cv.data.raw_text
    job_description = job.description if job else (
        "Improve this CV for general ATS compatibility. "
        "Focus on keyword density, formatting, and impact statements."
    )
    version_label = f"Optimized for {job.title} at {job.company}" if job else f"ATS Optimized"
    version_type = 'job_tailored' if job else 'ats_optimized'
    optimization_target = f"{job.title} at {job.company}" if job else None

    def run_tailor():
        from django.db import connection
        try:
            prompt = f"""You are a Certified Professional CV Writer (CPRW).
Rewrite the CV below to match the job description provided.
Return ONLY a valid JSON object — no explanation, no markdown fences.

{{
  "optimized_text": "<full rewritten CV as plain text>",
  "keywords_added": ["keyword 1", "keyword 2", "keyword 3"],
  "changes_made": ["change 1", "change 2", "change 3"],
  "ats_score": <integer 0-100>,
  "overall_score": <integer 0-100>
}}

JOB DESCRIPTION:
{job_description[:600]}

ORIGINAL CV:
{cv_text[:800]}

Return ONLY the JSON object."""

            raw = ollama_service.generate(prompt=prompt, temperature=0.4, max_tokens=800)
            logger.info(f"Ollama tailoring raw output length: {len(raw)} chars")

            cleaned = re.sub(r'```(?:json)?\s*', '', raw).strip().rstrip('`').strip()
            match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            result = json.loads(match.group()) if match else {}

            version_number = CVVersion.objects.filter(cv=cv).count() + 1
            CVVersion.objects.create(
                cv=cv,
                version_number=version_number,
                title=version_label,
                description="AI-tailored CV version",
                version_type=version_type,
                optimization_target=optimization_target,
                optimized_text=result.get('optimized_text', cv_text),
                keywords_added=result.get('keywords_added', []),
                changes_made=result.get('changes_made', []),
                ats_score=result.get('ats_score', 0),
                overall_score=result.get('overall_score', 0),
                is_current=True,
            )
            logger.info(f"CV tailoring completed for CV {cv_id}")
        except Exception as e:
            logger.error(f"CV tailoring background thread failed: {e}", exc_info=True)
        finally:
            connection.close()

    thread = threading.Thread(target=run_tailor, daemon=True)
    thread.start()

    agents = ['Job Analyst Agent', 'Gap Analyst Agent', 'CV Writer Agent']
    return Response(
        {
            'status': 'processing',
            'message': (
                f'Tailoring started. Three AI agents are working: '
                f'{" → ".join(agents)}. '
                'Poll GET /api/cv/{id}/ and watch versions[] for the new entry.'
            ),
            'agents': agents,
        },
        status=status.HTTP_202_ACCEPTED
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_cv_version_pdf(request, cv_id, version_id):
    """
    Download a CV version as PDF
    
    Returns a PDF file of the CV version with proper formatting
    """
    try:
        cv = get_object_or_404(CV, id=cv_id, user=request.user)
        version = get_object_or_404(CVVersion, id=version_id, cv=cv)
        
        # Generate PDF
        generator = CVPDFGenerator(version)
        pdf_bytes = generator.generate_pdf()
        
        # Create response with PDF
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        filename = f"{cv.title.replace(' ', '_')}_v{version.version_number}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        logger.info(f"PDF downloaded for CV version {version_id}")
        return response
        
    except Exception as e:
        logger.error(f"Error generating PDF for version {version_id}: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Failed to generate PDF', 'detail': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def view_cv_version(request, cv_id, version_id):
    """
    View a CV version's detailed content
    
    Returns the full content of a CV version including all sections
    """
    try:
        cv = get_object_or_404(CV, id=cv_id, user=request.user)
        version = get_object_or_404(CVVersion, id=version_id, cv=cv)
        
        # Get CV data
        cv_data = cv.data
        
        # Return detailed content
        return Response({
            'version': {
                'id': version.id,
                'title': version.title,
                'version_number': version.version_number,
                'version_type': version.version_type,
                'description': version.description,
                'optimization_target': version.optimization_target,
                'optimized_text': version.optimized_text,
                'keywords_added': version.keywords_added,
                'changes_made': version.changes_made,
                'ats_score': version.ats_score,
                'overall_score': version.overall_score,
                'is_current': version.is_current,
                'created_at': version.created_at,
            },
            'cv_data': {
                'email': cv_data.email,
                'phone': cv_data.phone,
                'location': cv_data.location,
                'linkedin_url': cv_data.linkedin_url,
                'github_url': cv_data.github_url,
                'website_url': cv_data.website_url,
                'summary': cv_data.summary,
                'skills': cv_data.skills,
                'experience': cv_data.experience,
                'education': cv_data.education,
                'projects': cv_data.projects,
                'certifications': cv_data.certifications,
                'languages': cv_data.languages,
                'interests': cv_data.interests,
            }
        })
        
    except Exception as e:
        logger.error(f"Error viewing CV version {version_id}: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Failed to load CV version', 'detail': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
