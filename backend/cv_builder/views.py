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
from ai_agents.services.ai_service import ai_service
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
            prompt = f"""You are a senior ATS consultant and Certified Professional CV Writer. Thoroughly analyse this CV.
Return ONLY a valid JSON object — no explanation, no markdown fences.

{{
  "ats_score": <integer 0-100, how well this CV passes ATS systems>,
  "overall_score": <integer 0-100, overall CV quality>,
  "content_quality_score": <integer 0-100, quality of content and writing>,
  "formatting_score": <integer 0-100, formatting and structure>,
  "strengths": ["specific strength 1", "specific strength 2", "specific strength 3"],
  "weaknesses": ["specific weakness 1", "specific weakness 2", "specific weakness 3"],
  "suggestions": ["actionable suggestion 1", "actionable suggestion 2", "actionable suggestion 3", "actionable suggestion 4"],
  "missing_keywords": ["keyword 1", "keyword 2", "keyword 3"],
  "missing_sections": ["section name 1"],
  "detailed_checks": {{
    "content": {{
      "score": <integer 0-100>,
      "checks": [
        {{"name": "ATS Parse Rate", "status": "pass or fail", "issues": <count>, "details": "<explanation>"}},
        {{"name": "Quantifying Impact", "status": "pass or fail", "issues": <count>, "details": "<explanation>"}},
        {{"name": "Repetition", "status": "pass or fail", "issues": <count>, "details": "<explanation>"}},
        {{"name": "Spelling & Grammar", "status": "pass or fail", "issues": <count>, "details": "<explanation>"}},
        {{"name": "Action Verbs", "status": "pass or fail", "issues": <count>, "details": "<explanation>"}},
        {{"name": "Bullet Point Length", "status": "pass or fail", "issues": <count>, "details": "<explanation>"}},
        {{"name": "Achievements vs Duties", "status": "pass or fail", "issues": <count>, "details": "<explanation>"}}
      ]
    }},
    "formatting": {{
      "score": <integer 0-100>,
      "checks": [
        {{"name": "Contact Information", "status": "pass or fail", "issues": <count>, "details": "<explanation>"}},
        {{"name": "Section Headers", "status": "pass or fail", "issues": <count>, "details": "<explanation>"}},
        {{"name": "CV Length", "status": "pass or fail", "issues": <count>, "details": "<explanation>"}},
        {{"name": "Consistent Formatting", "status": "pass or fail", "issues": <count>, "details": "<explanation>"}},
        {{"name": "Reverse Chronological Order", "status": "pass or fail", "issues": <count>, "details": "<explanation>"}}
      ]
    }},
    "keywords": {{
      "score": <integer 0-100>,
      "checks": [
        {{"name": "Industry Keywords", "status": "pass or fail", "issues": <count>, "details": "<explanation>"}},
        {{"name": "Skills Section", "status": "pass or fail", "issues": <count>, "details": "<explanation>"}},
        {{"name": "Job Title Alignment", "status": "pass or fail", "issues": <count>, "details": "<explanation>"}}
      ]
    }}
  }}
}}

CV TEXT:
{cv_text[:6000]}

Return ONLY the JSON object."""

            raw = ai_service.generate(prompt=prompt, temperature=0.2, max_tokens=2000)
            logger.info(f"Claude analysis raw output length: {len(raw)} chars")

            # Extract JSON from response
            cleaned = re.sub(r'```(?:json)?\s*', '', raw).strip().rstrip('`').strip()
            match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            result = json.loads(match.group()) if match else {}

            allowed = {
                'ats_score', 'overall_score', 'content_quality_score',
                'formatting_score', 'strengths', 'weaknesses', 'suggestions',
                'formatting_issues', 'missing_keywords', 'missing_sections',
                'detailed_checks',
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

    cv_data = cv.data
    job_description = job.description if job else (
        "Improve this CV for general ATS compatibility and maximum impact."
    )
    version_label = f"Tailored for {job.title} at {job.company}" if job else "ATS Optimized"
    version_type = 'job_tailored' if job else 'ats_optimized'
    optimization_target = f"{job.title} at {job.company}" if job else None

    # Build the cleanest possible candidate data — prefer structured fields, fall back to raw text
    candidate_lines = []
    if cv_data.email:      candidate_lines.append(f"Email: {cv_data.email}")
    if cv_data.phone:      candidate_lines.append(f"Phone: {cv_data.phone}")
    if cv_data.location:   candidate_lines.append(f"Location: {cv_data.location}")
    if cv_data.linkedin_url: candidate_lines.append(f"LinkedIn: {cv_data.linkedin_url}")
    if cv_data.github_url:   candidate_lines.append(f"GitHub: {cv_data.github_url}")
    if cv_data.website_url:  candidate_lines.append(f"Portfolio: {cv_data.website_url}")
    if cv_data.summary:
        candidate_lines.append(f"\nSUMMARY:\n{cv_data.summary}")
    if cv_data.skills:
        skills = cv_data.skills if isinstance(cv_data.skills, list) else []
        if skills:
            candidate_lines.append(f"\nSKILLS:\n{', '.join(str(s) for s in skills)}")
    if cv_data.experience:
        exps = cv_data.experience if isinstance(cv_data.experience, list) else []
        if exps:
            candidate_lines.append("\nEXPERIENCE:")
            for e in exps:
                role = e.get('role') or e.get('title') or ''
                company = e.get('company') or ''
                dates = e.get('duration') or e.get('dates') or e.get('period') or ''
                desc = e.get('description') or e.get('responsibilities') or ''
                candidate_lines.append(f"  {role} at {company} ({dates})")
                if desc:
                    candidate_lines.append(f"  {desc}")
    if cv_data.education:
        edus = cv_data.education if isinstance(cv_data.education, list) else []
        if edus:
            candidate_lines.append("\nEDUCATION:")
            for edu in edus:
                degree = edu.get('degree') or ''
                inst = edu.get('institution') or edu.get('school') or ''
                year = edu.get('year') or edu.get('dates') or ''
                candidate_lines.append(f"  {degree}, {inst} ({year})")
    if cv_data.projects:
        projs = cv_data.projects if isinstance(cv_data.projects, list) else []
        if projs:
            candidate_lines.append("\nPROJECTS:")
            for p in projs:
                name = p.get('name') or ''
                desc = p.get('description') or ''
                tech = p.get('technologies') or p.get('tech') or p.get('tech_stack') or ''
                line = f"  {name}: {desc}"
                if tech:
                    line += f" (Technologies: {tech})"
                candidate_lines.append(line)
    if cv_data.certifications:
        certs = cv_data.certifications if isinstance(cv_data.certifications, list) else []
        if certs:
            candidate_lines.append(f"\nCERTIFICATIONS:\n  {', '.join(str(c) for c in certs)}")

    candidate_data = '\n'.join(candidate_lines).strip()
    # Fall back to raw text if structured parsing produced nothing useful
    if len(candidate_data) < 100:
        candidate_data = cv_data.raw_text[:6000]

    def run_tailor():
        from django.db import connection
        try:
            prompt = f"""You are an expert CV writer and career coach. You have been given:
1. A candidate's full profile (their actual experience, skills, education, projects)
2. A job description they want to apply for

Your job: Write a complete, highly tailored CV for this candidate that gives them the best possible chance of getting this job.

Read both documents carefully. Understand what the employer is looking for. Then write a CV that:
- Speaks directly to what this employer needs
- Uses the exact terminology and keywords from the job description
- Presents the candidate's real experience in the most relevant, compelling way
- Highlights the parts of their background that matter most for this role
- Structures the CV in whatever way best showcases this candidate for this job
- Does not invent or fabricate anything — only uses what the candidate actually has
- Writes complete, specific sentences — no placeholder text like "your achievement here"

Return ONLY a valid JSON object. No explanation. No markdown. No code fences.

{{
  "optimized_text": "<the complete tailored CV — fully written, ready to submit>",
  "keywords_added": ["keyword from job description 1", "keyword 2", "keyword 3", "keyword 4", "keyword 5"],
  "changes_made": ["what you changed and why 1", "what you changed and why 2", "what you changed and why 3"],
  "ats_score": <integer 0-100>,
  "overall_score": <integer 0-100>
}}

JOB DESCRIPTION:
{job_description[:3000]}

CANDIDATE PROFILE:
{candidate_data[:5000]}

Return ONLY the JSON object."""

            raw = ai_service.generate(prompt=prompt, temperature=0.4, max_tokens=4000)
            logger.info(f"Claude tailoring raw output length: {len(raw)} chars")

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
                optimized_text=result.get('optimized_text', candidate_data),
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
def download_original_cv(request, cv_id):
    """Serve the original uploaded CV file for download."""
    import os
    cv = get_object_or_404(CV, id=cv_id, user=request.user)
    if not cv.file:
        return Response({'error': 'No file attached to this CV'}, status=status.HTTP_404_NOT_FOUND)
    try:
        file_path = cv.file.path
        with open(file_path, 'rb') as f:
            content = f.read()
        filename = cv.original_filename or os.path.basename(file_path)
        content_type = 'application/pdf' if filename.lower().endswith('.pdf') else 'application/octet-stream'
        response = HttpResponse(content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except FileNotFoundError:
        return Response({'error': 'File not found on disk'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error downloading original CV {cv_id}: {e}", exc_info=True)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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


# ── CV Builder: enhance + create-manual ───────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def enhance_cv_sections(request):
    """
    Claude reads the builder form data + checkboxes + job description,
    then enhances weak sections and invents missing ones.
    Returns a list of review sections for the user to approve.
    """
    data = request.data
    job_description = data.get('job_description', '').strip()
    job_title = data.get('job_title', 'the target role')
    job_company = data.get('job_company', 'the target company')

    if not job_description:
        return Response({'error': 'Job description is required'}, status=status.HTTP_400_BAD_REQUEST)

    # Build a readable candidate profile from the form
    lines = []

    # Personal
    name = data.get('name', '')
    if name: lines.append(f"Name: {name}")

    # Summary
    summary = data.get('summary', '').strip()
    write_summary = data.get('claude_write_summary', False)

    # Experience
    experience = data.get('experience', [])
    if experience:
        lines.append("\nEXPERIENCE PROVIDED BY CANDIDATE:")
        for exp in experience:
            if exp.get('create'):
                lines.append("  [CANDIDATE HAS NO RELEVANT EXPERIENCE — CREATE A BELIEVABLE ENTRY]")
            else:
                lines.append(f"  {exp.get('role','')} at {exp.get('company','')} ({exp.get('start_date','')} – {exp.get('end_date','')})")
                if exp.get('description'):
                    lines.append(f"  Description: {exp.get('description','')}")
                if exp.get('enhance'):
                    lines.append("  [ENHANCE THIS — make it stronger and more relevant to the job]")

    # Projects
    projects = data.get('projects', [])
    create_projects = data.get('claude_create_projects', False)
    if create_projects:
        lines.append("\nPROJECTS: [CANDIDATE NEEDS MORE PROJECTS — CREATE 2-3 RELEVANT ONES]")
    elif projects:
        lines.append("\nPROJECTS:")
        for p in projects:
            if p.get('name'):
                lines.append(f"  {p.get('name','')}: {p.get('description','')} | Tech: {p.get('technologies','')} | Link: {p.get('link','')}")
                if p.get('enhance'):
                    lines.append("  [ENHANCE THIS PROJECT DESCRIPTION]")

    # Skills
    skills = data.get('skills', '').strip()
    add_skills = data.get('claude_add_skills', True)
    if skills:
        lines.append(f"\nSKILLS CANDIDATE HAS: {skills}")
    if add_skills:
        lines.append("[ADD MISSING SKILLS FROM THE JOB DESCRIPTION]")

    # Education
    education = data.get('education', [])
    if education:
        lines.append("\nEDUCATION:")
        for edu in education:
            if edu.get('degree'):
                lines.append(f"  {edu.get('degree','')} — {edu.get('institution','')} ({edu.get('year','')}) {edu.get('grade','')}")

    # Certifications
    certifications = data.get('certifications', '').strip()
    suggest_certs = data.get('claude_suggest_certifications', False)
    if certifications:
        lines.append(f"\nCERTIFICATIONS: {certifications}")
    if suggest_certs:
        lines.append("[ADD 'Currently pursuing: [relevant cert]' for certs that match this job]")

    candidate_profile = '\n'.join(lines)

    prompt = f"""You are an expert CV writer and career coach. A candidate wants to apply for the role of "{job_title}" at "{job_company}".

You have been given:
1. The candidate's raw profile (what they actually have, notes on what to enhance/create)
2. The full job description

Your job: For each section below, write the best possible content for this candidate targeting this specific job.

RULES:
- Where the candidate has real experience: enhance it to sound stronger, use the job's language
- Where the candidate has NO experience and [CREATE] is marked: invent a believable, realistic entry that fits their background level
- For projects marked [CREATE]: invent 2-3 realistic projects using the tech stack required by this job
- For skills: include all the candidate's real skills PLUS the key missing ones from the job description
- For certifications marked [ADD]: add "Currently pursuing: [cert name]" for 1-2 highly relevant certs
- For summary: write a powerful 3-4 sentence summary targeted at this specific company and role
- NEVER invent education qualifications
- Write everything as final, polished, ready-to-submit CV content — no placeholders

Return ONLY a valid JSON object. No explanation. No markdown.

{{
  "sections": [
    {{
      "section": "summary",
      "label": "Professional Summary",
      "original": "<what candidate provided or empty>",
      "enhanced": "<Claude's written version>",
      "was_invented": <true if Claude wrote from scratch, false if enhanced>
    }},
    {{
      "section": "experience",
      "label": "Work Experience",
      "original": "<candidate's raw experience notes>",
      "enhanced": "<full enhanced/created experience section as plain text>",
      "was_invented": <true/false>
    }},
    {{
      "section": "projects",
      "label": "Projects",
      "original": "<candidate's raw projects>",
      "enhanced": "<full enhanced/created projects section as plain text>",
      "was_invented": <true/false>
    }},
    {{
      "section": "skills",
      "label": "Technical Skills",
      "original": "<candidate's listed skills>",
      "enhanced": "<full skills section organised by category>",
      "was_invented": false
    }},
    {{
      "section": "certifications",
      "label": "Certifications",
      "original": "<candidate's existing certifications>",
      "enhanced": "<certifications including any Currently pursuing additions>",
      "was_invented": false
    }}
  ]
}}

JOB DESCRIPTION:
{job_description[:3000]}

CANDIDATE PROFILE:
{candidate_profile[:4000]}

Return ONLY the JSON object."""

    try:
        raw = ai_service.generate(prompt=prompt, temperature=0.4, max_tokens=3000)
        logger.info(f"CV builder enhance raw output: {len(raw)} chars")

        cleaned = re.sub(r'```(?:json)?\s*', '', raw).strip().rstrip('`').strip()
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        result = json.loads(match.group()) if match else {}

        sections = result.get('sections', [])

        # Always include summary even if write_summary was false
        if not write_summary and summary:
            for s in sections:
                if s['section'] == 'summary':
                    s['original'] = summary
                    s['enhanced'] = summary
                    s['was_invented'] = False

        return Response({'sections': sections}, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"CV builder enhance failed: {e}", exc_info=True)
        return Response({'error': f'AI enhancement failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_manual_cv(request):
    """
    Saves the approved builder data as a CV + CVData.
    No file upload needed — data comes from the builder form + Claude's approved sections.
    """
    data = request.data
    form = data.get('form', {})
    approved = data.get('approved', {})  # section -> approved text

    name = form.get('name', 'My CV')
    job_title = form.get('job_title', '')
    job_company = form.get('job_company', '')
    title = f"{name} — {job_title} at {job_company}".strip(' —') if job_title else f"{name}'s CV"

    try:
        # Build raw_text from approved sections
        raw_text_parts = []
        contact_parts = []
        for field in ['name', 'phone', 'email', 'location', 'linkedin', 'github', 'portfolio']:
            val = form.get(field, '').strip()
            if val:
                contact_parts.append(f"{field.title()}: {val}")
        if contact_parts:
            raw_text_parts.append('\n'.join(contact_parts))

        for section_key in ['summary', 'experience', 'projects', 'skills', 'certifications']:
            text = approved.get(section_key, '').strip()
            if text:
                raw_text_parts.append(text)

        raw_text = '\n\n'.join(raw_text_parts)

        # Parse skills from approved skills section
        skills_text = approved.get('skills', form.get('skills', ''))
        skills_list = [s.strip() for s in re.split(r'[,\n]', skills_text) if s.strip()]

        # Build experience list
        experience_list = []
        for exp in form.get('experience', []):
            if exp.get('company') or exp.get('role'):
                experience_list.append({
                    'role': exp.get('role', ''),
                    'company': exp.get('company', ''),
                    'duration': f"{exp.get('start_date','')} – {exp.get('end_date','')}".strip(' –'),
                    'description': exp.get('description', ''),
                })

        # Build education list
        education_list = []
        for edu in form.get('education', []):
            if edu.get('degree') or edu.get('institution'):
                education_list.append({
                    'degree': edu.get('degree', ''),
                    'institution': edu.get('institution', ''),
                    'year': edu.get('year', ''),
                    'grade': edu.get('grade', ''),
                })

        # Build projects list
        projects_list = []
        for proj in form.get('projects', []):
            if proj.get('name'):
                projects_list.append({
                    'name': proj.get('name', ''),
                    'description': proj.get('description', ''),
                    'technologies': proj.get('technologies', ''),
                    'link': proj.get('link', ''),
                })

        # Create CV (no file — is_temporary=True)
        cv = CV.objects.create(
            user=request.user,
            title=title,
            is_temporary=True,
            file_type='MANUAL',
            file_size=0,
            is_parsed=True,
            is_active=True,
        )

        # Create CVData with all the approved content
        CVData.objects.create(
            cv=cv,
            raw_text=raw_text,
            email=form.get('email', ''),
            phone=form.get('phone', ''),
            location=form.get('location', ''),
            linkedin_url=form.get('linkedin', ''),
            github_url=form.get('github', ''),
            website_url=form.get('portfolio', ''),
            summary=approved.get('summary', form.get('summary', '')),
            skills=skills_list,
            experience=experience_list,
            education=education_list,
            projects=projects_list,
            certifications=[c.strip() for c in approved.get('certifications', '').split('\n') if c.strip()],
            parsing_status='completed',
        )

        logger.info(f"Manual CV created: {cv.id} for user {request.user.email}")
        return Response({'id': str(cv.id), 'title': title}, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"create_manual_cv failed: {e}", exc_info=True)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
