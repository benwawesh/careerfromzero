"""
Job System Views
API views for job discovery, applications, and matching
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count
from django.utils import timezone
import logging
import json
import re

from .models import (
    Job, SavedJob, JobApplication, JobMatch, JobSearch,
    AutoApplicationBatch, AutoApplicationItem, UserApplicationPreference,
    JobCategory, JobCache
)
from .serializers import (
    JobSerializer, JobDetailSerializer,
    SavedJobSerializer, JobApplicationSerializer, JobApplicationStatusSerializer,
    JobMatchSerializer, JobSearchSerializer, JobSearchQuerySerializer,
    AutoApplicationBatchSerializer, AutoApplicationItemSerializer,
    UserApplicationPreferenceSerializer, JobCategorySerializer
)
from .services.job_search_engine import JobSearchEngine
from .services.approval_manager import ApprovalManager
from .services.application_executor import ApplicationExecutor
from ai_agents.application_strategy_agent import ApplicationStrategyAgent

logger = logging.getLogger(__name__)


class JobViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Job model - READ ONLY (jobs from external sources)"""
    
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'company', 'description', 'location']
    ordering_fields = ['created_at', 'salary_max', 'salary_min', 'title', 'company']
    
    def get_queryset(self):
        """Get jobs with filtering"""
        queryset = Job.objects.filter(is_active=True)
        
        # Basic filters
        query = self.request.query_params.get('query')
        location = self.request.query_params.get('location')
        job_type = self.request.query_params.get('job_type')
        experience_level = self.request.query_params.get('experience_level')
        salary_min = self.request.query_params.get('salary_min')
        salary_max = self.request.query_params.get('salary_max')
        sources = self.request.query_params.getlist('sources')
        
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) |
                Q(company__icontains=query) |
                Q(description__icontains=query)
            )
        
        if location:
            queryset = queryset.filter(location__icontains=location)
        
        if job_type:
            queryset = queryset.filter(job_type=job_type)
        
        if experience_level:
            queryset = queryset.filter(experience_level=experience_level)
        
        if salary_min:
            queryset = queryset.filter(salary_max__gte=salary_min)
        
        if salary_max:
            queryset = queryset.filter(salary_min__lte=salary_max)
        
        if sources:
            queryset = queryset.filter(source__in=sources)
        
        return queryset.distinct()
    
    def get_serializer_class(self):
        """Get appropriate serializer based on action"""
        if self.action == 'retrieve':
            return JobDetailSerializer
        return JobSerializer
    
    def retrieve(self, request, *args, **kwargs):
        """Get job details and increment view count"""
        instance = self.get_object()
        instance.view_count += 1
        instance.save(update_fields=['view_count'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def fetch_description(self, request, pk=None):
        """
        Fetches the live job description from the source URL.
        Uses source-specific selectors to extract only the job body,
        stripping navigation, sidebar, social share buttons, etc.
        """
        import requests as _requests
        from bs4 import BeautifulSoup as _BS

        job = self.get_object()
        if not job.job_url:
            return Response({'error': 'No source URL'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            r = _requests.get(
                job.job_url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                                  'Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,*/*;q=0.9',
                    'Accept-Language': 'en-US,en;q=0.9',
                },
                timeout=15,
            )
            r.raise_for_status()
        except _requests.exceptions.Timeout:
            return Response({'error': 'Source site timed out'}, status=status.HTTP_504_GATEWAY_TIMEOUT)
        except _requests.exceptions.RequestException as e:
            return Response({'error': f'Could not reach source: {e}'}, status=status.HTTP_502_BAD_GATEWAY)

        soup = _BS(r.text, 'html.parser')

        # ── Remove boilerplate elements ───────────────────────────────────────
        NOISE_SELECTORS = (
            'nav, header, footer, script, style, noscript, iframe, '
            '[class*="nav-"], [class*="header-"], [class*="footer-"], '
            '[class*="sidebar"], [class*="widget"], '
            '[class*="share"], [class*="social"], '
            '[class*="modal"], [class*="cookie"], [class*="banner"], '
            '[class*="advertisement"], [class*="ad-"], '
            '[class*="related-jobs"], [class*="similar-jobs"], '
            '[class*="apply-button"], [class*="apply-now"], '
            'button, form[class*="apply"], [class*="login-prompt"]'
        )
        for tag in soup.select(NOISE_SELECTORS):
            tag.decompose()

        # ── Source-specific extraction ────────────────────────────────────────
        source = job.source
        content_elem = None
        combined_html = None

        if source == 'brightermonday':
            # BrighterMonday uses Tailwind utility classes (mt-6) inside article.job__details
            # We combine all the content divs to get the full description
            article = soup.select_one('article.job__details, [class*="job__details"]')
            if not article:
                # Fallback: try any article with substantial text
                for a in soup.select('article'):
                    if len(a.get_text(strip=True)) > 300:
                        article = a
                        break
            if article:
                # Remove noise within the article
                for tag in article.select(
                    '[class*="share"], [class*="social"], button, '
                    '[class*="apply"], [class*="login"], aside'
                ):
                    tag.decompose()
                # Collect the content divs (mt-6 sections contain the actual job text)
                # Match both exact and compound Tailwind classes like "mt-6 flex-wrap"
                sections = article.select('div[class*="mt-6"]')
                # Filter to sections with actual content (not just metadata badges)
                content_sections = [s for s in sections if len(s.get_text(strip=True)) > 100]
                if content_sections:
                    combined_html = ''.join(str(s) for s in content_sections)
                elif sections:
                    combined_html = ''.join(str(s) for s in sections)
                else:
                    combined_html = str(article)

        elif source == 'myjobmag':
            # MyJobMag individual job page: description is in .job-desc or article content
            for sel in [
                '[class*="job-desc"]', '[class*="job_desc"]',
                '[class*="job-description"]', '[class*="description-content"]',
                '.description', 'article .content', '.post-content',
                'article', '[role="main"] .content', '[role="main"]',
            ]:
                elem = soup.select_one(sel)
                if elem and len(elem.get_text(strip=True)) > 150:
                    for tag in elem.select('[class*="share"], button, aside'):
                        tag.decompose()
                    content_elem = elem
                    break

        elif source == 'corporatestaffing':
            for sel in ['.entry-content', 'article .post-content',
                        '[class*="job-description"]', 'article']:
                elem = soup.select_one(sel)
                if elem and len(elem.get_text(strip=True)) > 150:
                    content_elem = elem
                    break

        elif source in ('jobwebkenya', 'kenyajob', 'nationkenya'):
            for sel in ['.entry-content', '[class*="job-description"]',
                        'article .content', 'article', '[role="main"]']:
                elem = soup.select_one(sel)
                if elem and len(elem.get_text(strip=True)) > 150:
                    content_elem = elem
                    break

        elif source == 'ngojobs':
            for sel in ['[class*="body"]', '[class*="field-description"]',
                        '.field-items', 'article', '[role="main"]']:
                elem = soup.select_one(sel)
                if elem and len(elem.get_text(strip=True)) > 150:
                    content_elem = elem
                    break

        elif source == 'linkedin':
            for sel in ['[class*="description__text"]', '[class*="show-more-less-html"]',
                        '[class*="job-description"]']:
                elem = soup.select_one(sel)
                if elem and len(elem.get_text(strip=True)) > 150:
                    content_elem = elem
                    break

        elif source == 'indeed':
            for sel in ['[class*="jobDescriptionText"]', '[id*="jobDescriptionText"]',
                        '[class*="job-description"]']:
                elem = soup.select_one(sel)
                if elem and len(elem.get_text(strip=True)) > 150:
                    content_elem = elem
                    break

        elif source in ('jobberman', 'career24', 'fuzu'):
            for sel in ['[class*="job-description"]', '[class*="description"]',
                        '.description', 'article', '[role="main"] .content', '[role="main"]']:
                elem = soup.select_one(sel)
                if elem and len(elem.get_text(strip=True)) > 150:
                    content_elem = elem
                    break

        # ── Generic fallback for any source ──────────────────────────────────
        if not content_elem and not combined_html:
            GENERIC_SELECTORS = [
                '[itemprop="description"]',
                '[class*="job-description"]', '[class*="job-detail"]',
                '[class*="description-body"]', '[class*="job-content"]',
                '[class*="content-body"]', '[class*="main-content"]',
                'main article', 'article', '[role="main"]', 'main',
            ]
            for sel in GENERIC_SELECTORS:
                elem = soup.select_one(sel)
                if elem and len(elem.get_text(strip=True)) > 150:
                    content_elem = elem
                    break

        if not content_elem and not combined_html:
            return Response(
                {'error': 'Could not extract description from source page'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # ── Build final HTML and plain text ──────────────────────────────────
        if combined_html:
            # Already combined (e.g. BrighterMonday multi-section)
            html = combined_html
            plain = _BS(html, 'html.parser').get_text(separator='\n', strip=True)
        else:
            # Clean up remaining noise inside the found element
            for tag in content_elem.select(
                '[class*="share"], [class*="social"], button, '
                '[class*="apply"], [class*="login"], [class*="signup"], '
                'aside, [class*="sidebar"]'
            ):
                tag.decompose()
            html = str(content_elem)
            plain = content_elem.get_text(separator='\n', strip=True)

        plain = re.sub(r'\n{3,}', '\n\n', plain)

        return Response({
            'description_html': html,
            'description_text': plain[:8000],
            'source': job.source,
        })

    @action(detail=True, methods=['post'])
    def save(self, request, pk=None):
        """Save/bookmark a job"""
        job = self.get_object()
        
        # Check if already saved
        if SavedJob.objects.filter(user=request.user, job=job).exists():
            return Response(
                {'detail': 'Job already saved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        saved_job = SavedJob.objects.create(
            user=request.user,
            job=job
        )
        serializer = SavedJobSerializer(saved_job)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['delete'])
    def unsave(self, request, pk=None):
        """Unsave/unbookmark a job"""
        job = self.get_object()
        try:
            saved_job = SavedJob.objects.get(user=request.user, job=job)
            saved_job.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except SavedJob.DoesNotExist:
            return Response(
                {'detail': 'Job not saved'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['get'])
    def check_saved(self, request, pk=None):
        """Check if job is saved by current user"""
        job = self.get_object()
        is_saved = SavedJob.objects.filter(user=request.user, job=job).exists()
        return Response({'saved': is_saved})

    # ------------------------------------------------------------------
    # Match scores (fast keyword-based, no Ollama)
    # ------------------------------------------------------------------

    @action(detail=False, methods=['get'])
    def my_matches(self, request):
        """Return keyword-based match scores for all active jobs vs user's current CV."""
        from cv_builder.models import CVVersion

        cv_version = CVVersion.objects.filter(
            cv__user=request.user,
            is_current=True
        ).select_related('cv').first()

        if not cv_version:
            return Response({'matches': {}, 'has_cv': False, 'cv_skills': []})

        # Build user skill set from CVData + full text
        cv_skills = set()
        cv_text = ''
        try:
            cv_data = cv_version.cv.data
            cv_skills = set(s.lower() for s in (cv_data.skills or []))
        except Exception:
            pass
        cv_text = (cv_version.optimized_text or '').lower()

        jobs = Job.objects.filter(is_active=True).values('id', 'skills_required', 'title', 'description')

        matches = {}
        for job in jobs:
            job_skills = set(s.lower() for s in (job['skills_required'] or []))
            if job_skills:
                skill_hits = len(cv_skills & job_skills)
                text_hits = sum(1 for s in job_skills if s in cv_text)
                total = max(skill_hits, text_hits)
                score = min(95, int(total / len(job_skills) * 100))
            else:
                score = 40  # no skills listed — default neutral
            matches[str(job['id'])] = score

        return Response({
            'matches': matches,
            'has_cv': True,
            'cv_skills': list(cv_skills),
        })

    # ------------------------------------------------------------------
    # IDs for saved / applied (used by frontend to mark cards)
    # ------------------------------------------------------------------

    @action(detail=False, methods=['get'])
    def saved_ids(self, request):
        """Return list of job IDs saved by the current user."""
        ids = SavedJob.objects.filter(user=request.user).values_list('job_id', flat=True)
        return Response({'saved_ids': [str(i) for i in ids]})

    @action(detail=False, methods=['get'])
    def applied_ids(self, request):
        """Return list of job IDs the current user has applied to."""
        ids = JobApplication.objects.filter(user=request.user).values_list('job_id', flat=True)
        return Response({'applied_ids': [str(i) for i in ids]})

    # ------------------------------------------------------------------
    # AI-powered CV tailoring for a specific job (uses Ollama)
    # ------------------------------------------------------------------

    @action(detail=True, methods=['post'])
    def tailor_cv(self, request, pk=None):
        """
        Use Ollama to generate a tailored CV summary + cover letter for this job.
        Returns: {tailored_summary, key_skills, changes_made, cover_letter}
        Note: runs Ollama on CPU, takes 1-3 minutes.
        """
        from ai_agents.services.ollama_service import ollama_service
        from cv_builder.models import CVVersion

        job = self.get_object()

        # Resolve CV version
        cv_version_id = request.data.get('cv_version_id')
        cv_version = None
        if cv_version_id:
            try:
                cv_version = CVVersion.objects.get(id=cv_version_id, cv__user=request.user)
            except CVVersion.DoesNotExist:
                return Response({'error': 'CV version not found'}, status=status.HTTP_404_NOT_FOUND)

        if not cv_version:
            cv_version = CVVersion.objects.filter(
                cv__user=request.user,
                is_current=True
            ).first()

        if not cv_version:
            return Response({'error': 'No CV found. Upload a CV first.'}, status=status.HTTP_400_BAD_REQUEST)

        cv_text = (cv_version.optimized_text or '').strip()
        if not cv_text:
            try:
                cv_text = cv_version.cv.data.raw_text or ''
            except Exception:
                cv_text = ''

        if not cv_text:
            return Response({'error': 'CV has no text content yet.'}, status=status.HTTP_400_BAD_REQUEST)

        skills_str = ', '.join((job.skills_required or [])[:10]) or 'Not specified'
        prompt = f"""You are an expert CV writer. Customize the candidate's CV for this job.
Return ONLY valid JSON — no extra text.

JOB: {job.title} at {job.company}
Required skills: {skills_str}
Description (first 400 chars): {job.description[:400]}

CANDIDATE CV (first 1200 chars):
{cv_text[:1200]}

Return ONLY this JSON object:
{{
  "tailored_summary": "2-3 sentence professional summary tailored to this specific role",
  "key_skills": ["skill1", "skill2", "skill3", "skill4", "skill5"],
  "changes_made": ["Change 1 description", "Change 2 description", "Change 3 description"],
  "cover_letter": "Dear Hiring Manager,\\n\\n[2-3 paragraph cover letter for {job.title} at {job.company}]\\n\\nSincerely,\\n[Candidate Name]"
}}"""

        try:
            raw = ollama_service.generate(prompt=prompt, temperature=0.3, max_tokens=800)
            cleaned = re.sub(r'```(?:json)?\s*', '', raw).strip().rstrip('`').strip()
            match_obj = re.search(r'\{.*\}', cleaned, re.DOTALL)
            result = json.loads(match_obj.group()) if match_obj else {}
            return Response({
                'tailored_summary': result.get('tailored_summary', ''),
                'key_skills': result.get('key_skills', []),
                'changes_made': result.get('changes_made', []),
                'cover_letter': result.get('cover_letter', ''),
            })
        except Exception as e:
            logger.error(f"tailor_cv error: {e}")
            return Response({'error': f'Tailoring failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # ------------------------------------------------------------------
    # Bulk CV customization for multiple selected jobs
    # ------------------------------------------------------------------

    @action(detail=False, methods=['post'])
    def bulk_tailor_cvs(self, request):
        """
        Generate customized CVs and cover letters for multiple selected jobs.
        Body: {job_ids: [uuid, ...], cv_version_id (optional)}
        Returns: {batch_id, status, total_jobs, results}
        """
        from ai_agents.services.ollama_service import ollama_service
        from cv_builder.models import CVVersion

        job_ids = request.data.get('job_ids', [])
        cv_version_id = request.data.get('cv_version_id')

        if not job_ids:
            return Response(
                {'error': 'No job IDs provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Resolve CV version
        cv_version = None
        if cv_version_id:
            try:
                cv_version = CVVersion.objects.get(id=cv_version_id, cv__user=request.user)
            except CVVersion.DoesNotExist:
                return Response({'error': 'CV version not found'}, status=status.HTTP_404_NOT_FOUND)

        if not cv_version:
            cv_version = CVVersion.objects.filter(
                cv__user=request.user,
                is_current=True
            ).first()

        if not cv_version:
            return Response({'error': 'No CV found. Upload a CV first.'}, status=status.HTTP_400_BAD_REQUEST)

        # Get CV text
        cv_text = (cv_version.optimized_text or '').strip()
        if not cv_text:
            try:
                cv_text = cv_version.cv.data.raw_text or ''
            except Exception:
                cv_text = ''

        if not cv_text:
            return Response({'error': 'CV has no text content yet.'}, status=status.HTTP_400_BAD_REQUEST)

        # Get jobs
        jobs = Job.objects.filter(id__in=job_ids, is_active=True)
        if jobs.count() != len(job_ids):
            return Response(
                {'error': f'Only {jobs.count()} of {len(job_ids)} jobs found'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Process each job
        results = []
        for job in jobs:
            try:
                skills_str = ', '.join((job.skills_required or [])[:10]) or 'Not specified'
                prompt = f"""You are an expert CV writer. Customize the candidate's CV for this job.
Return ONLY valid JSON — no extra text.

JOB: {job.title} at {job.company}
Required skills: {skills_str}
Description (first 400 chars): {job.description[:400]}

CANDIDATE CV (first 1200 chars):
{cv_text[:1200]}

Return ONLY this JSON object:
{{
  "tailored_summary": "2-3 sentence professional summary tailored to this specific role",
  "key_skills": ["skill1", "skill2", "skill3", "skill4", "skill5"],
  "changes_made": ["Change 1 description", "Change 2 description", "Change 3 description"],
  "cover_letter": "Dear Hiring Manager,\\n\\n[2-3 paragraph cover letter for {job.title} at {job.company}]\\n\\nSincerely,\\n[Candidate Name]"
}}"""

                raw = ollama_service.generate(prompt=prompt, temperature=0.3, max_tokens=800)
                cleaned = re.sub(r'```(?:json)?\s*', '', raw).strip().rstrip('`').strip()
                match_obj = re.search(r'\{.*\}', cleaned, re.DOTALL)
                result_data = json.loads(match_obj.group()) if match_obj else {}

                results.append({
                    'job_id': str(job.id),
                    'job_title': job.title,
                    'company': job.company,
                    'status': 'success',
                    'data': {
                        'tailored_summary': result_data.get('tailored_summary', ''),
                        'key_skills': result_data.get('key_skills', []),
                        'changes_made': result_data.get('changes_made', []),
                        'cover_letter': result_data.get('cover_letter', ''),
                    }
                })

            except Exception as e:
                logger.error(f"bulk_tailor_cvs error for job {job.id}: {e}")
                results.append({
                    'job_id': str(job.id),
                    'job_title': job.title,
                    'company': job.company,
                    'status': 'failed',
                    'error': str(e)
                })

        return Response({
            'batch_id': str(job_ids[0]),  # Simple batch ID for now
            'status': 'completed',
            'total_jobs': len(job_ids),
            'successful_jobs': len([r for r in results if r['status'] == 'success']),
            'failed_jobs': len([r for r in results if r['status'] == 'failed']),
            'results': results
        })

    # ------------------------------------------------------------------
    # Apply to a job (creates a JobApplication record)
    # ------------------------------------------------------------------

    @action(detail=True, methods=['post'])
    def apply(self, request, pk=None):
        """
        Apply to a job.
        Body: {cv_version_id (optional), cover_letter (optional)}
        Creates a JobApplication and returns it.
        """
        from cv_builder.models import CVVersion

        job = self.get_object()

        if JobApplication.objects.filter(user=request.user, job=job).exists():
            return Response(
                {'detail': 'You have already applied to this job.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        cv_version_id = request.data.get('cv_version_id')
        cover_letter = request.data.get('cover_letter', '')
        cv_version = None

        if cv_version_id:
            try:
                cv_version = CVVersion.objects.get(id=cv_version_id, cv__user=request.user)
            except CVVersion.DoesNotExist:
                pass

        if not cv_version:
            cv_version = CVVersion.objects.filter(
                cv__user=request.user,
                is_current=True
            ).first()

        application = JobApplication.objects.create(
            user=request.user,
            job=job,
            cv_version=cv_version,
            mode='manual',
            status='applied',
            cover_letter=cover_letter,
            application_date=timezone.now().date(),
            application_url=job.job_url,
        )

        job.application_count += 1
        job.save(update_fields=['application_count'])

        return Response({
            'id': str(application.id),
            'status': 'applied',
            'job_url': job.job_url,
            'message': 'Application submitted successfully!',
        }, status=status.HTTP_201_CREATED)


class SavedJobViewSet(viewsets.ModelViewSet):
    """ViewSet for SavedJob model"""
    
    serializer_class = SavedJobSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return SavedJob.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class JobApplicationViewSet(viewsets.ModelViewSet):
    """ViewSet for JobApplication model"""
    
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return JobApplication.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'update_status':
            return JobApplicationStatusSerializer
        return JobApplicationSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get application statistics"""
        user_apps = JobApplication.objects.filter(user=request.user)
        
        stats = {
            'total': user_apps.count(),
            'by_status': {}
        }
        
        for status_choice in JobApplication.STATUS_CHOICES:
            status_key = status_choice[0]
            status_count = user_apps.filter(status=status_key).count()
            if status_count > 0:
                stats['by_status'][status_key] = {
                    'count': status_count,
                    'label': status_choice[1]
                }
        
        return Response(stats)
    
    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        """Update application status"""
        application = self.get_object()
        serializer = JobApplicationStatusSerializer(
            application,
            data=request.data,
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            
            # Update application date if status is 'applied'
            if serializer.validated_data.get('status') == 'applied' and not application.application_date:
                application.application_date = timezone.now().date()
                application.save()
            
            return Response(JobApplicationSerializer(application).data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class JobMatchViewSet(viewsets.ModelViewSet):
    """ViewSet for JobMatch model"""
    
    serializer_class = JobMatchSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return JobMatch.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def recommendations(self, request):
        """Get job recommendations for user"""
        # Get user's latest CV
        from cv_builder.models import CV
        cv = CV.objects.filter(user=request.user).order_by('-created_at').first()
        
        if not cv:
            return Response(
                {'detail': 'No CV found. Please upload a CV first.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get current version
        current_version = cv.versions.filter(is_current=True).first()
        
        if not current_version:
            return Response(
                {'detail': 'No CV version found.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get matches for this CV version
        matches = JobMatch.objects.filter(
            user=request.user,
            cv_version=current_version
        ).order_by('-overall_match')[:20]
        
        serializer = JobMatchSerializer(matches, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def match_cv(self, request):
        """Match user's CV to all jobs (batch matching)"""
        from cv_builder.models import CV
        cv = CV.objects.filter(user=request.user).order_by('-created_at').first()
        
        if not cv:
            return Response(
                {'detail': 'No CV found. Please upload a CV first.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        current_version = cv.versions.filter(is_current=True).first()
        
        if not current_version:
            return Response(
                {'detail': 'No CV version found.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get jobs to match (active jobs, not already matched)
        existing_match_job_ids = JobMatch.objects.filter(
            user=request.user,
            cv_version=current_version
        ).values_list('job_id', flat=True)
        
        jobs_to_match = Job.objects.filter(
            is_active=True
        ).exclude(id__in=existing_match_job_ids)[:50]  # Limit to 50 jobs
        
        # Calculate matches (placeholder - will be replaced with AI matching)
        matches_created = []
        for job in jobs_to_match:
            # Simple matching logic (will be enhanced with AI)
            skill_match = 0.0
            if job.skills_required and current_version.data.skills:
                job_skills = set(job.skills_required)
                cv_skills = set(current_version.data.skills)
                matched = job_skills & cv_skills
                if len(job_skills) > 0:
                    skill_match = (len(matched) / len(job_skills)) * 100
            
            overall_match = skill_match * 0.7  # 70% weight to skills
            
            job_match = JobMatch.objects.create(
                user=request.user,
                job=job,
                cv_version=current_version,
                overall_match=round(overall_match, 2),
                skill_match=round(skill_match, 2),
                experience_match=50.0,  # Placeholder
                matched_skills=list(set(job.skills_required or []) & set(current_version.data.skills or [])),
                missing_skills=[],
                suggestions=[]
            )
            matches_created.append(job_match)
        
        return Response({
            'message': f'Created {len(matches_created)} matches',
            'matches': JobMatchSerializer(matches_created, many=True).data
        })


class JobSearchViewSet(viewsets.ModelViewSet):
    """ViewSet for JobSearch model - saved searches"""
    
    serializer_class = JobSearchSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return JobSearch.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['get'])
    def run(self, request, pk=None):
        """Run a saved search"""
        search = self.get_object()
        
        # Build filters from saved search
        filters = {}
        if search.query:
            filters['query'] = search.query
        if search.location:
            filters['location'] = search.location
        if search.job_type:
            filters['job_type'] = search.job_type
        if search.experience_level:
            filters['experience_level'] = search.experience_level
        if search.salary_min:
            filters['salary_min'] = search.salary_min
        if search.salary_max:
            filters['salary_max'] = search.salary_max
        if search.skills:
            filters['skills'] = search.skills
        if search.sources:
            filters['sources'] = search.sources
        
        # Apply filters to Job queryset
        queryset = Job.objects.filter(is_active=True)
        
        if 'query' in filters:
            queryset = queryset.filter(
                Q(title__icontains=filters['query']) |
                Q(company__icontains=filters['query']) |
                Q(description__icontains=filters['query'])
            )
        
        if 'location' in filters:
            queryset = queryset.filter(location__icontains=filters['location'])
        
        if 'job_type' in filters:
            queryset = queryset.filter(job_type=filters['job_type'])
        
        if 'experience_level' in filters:
            queryset = queryset.filter(experience_level=filters['experience_level'])
        
        if 'salary_min' in filters:
            queryset = queryset.filter(salary_max__gte=filters['salary_min'])
        
        if 'salary_max' in filters:
            queryset = queryset.filter(salary_min__lte=filters['salary_max'])
        
        if 'sources' in filters:
            queryset = queryset.filter(source__in=filters['sources'])
        
        # Paginate results
        page = int(request.query_params.get('page', 1))
        page_size = 20
        start = (page - 1) * page_size
        end = start + page_size
        
        total = queryset.count()
        jobs = queryset[start:end]
        
        serializer = JobDetailSerializer(jobs, many=True)
        
        return Response({
            'count': total,
            'page': page,
            'page_size': page_size,
            'results': serializer.data
        })


class JobCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for JobCategory model"""
    
    serializer_class = JobCategorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return JobCategory.objects.filter(is_active=True).order_by('order')


class UserApplicationPreferenceViewSet(viewsets.ModelViewSet):
    """ViewSet for UserApplicationPreference model"""
    
    serializer_class = UserApplicationPreferenceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return UserApplicationPreference.objects.filter(user=self.request.user)
    
    def get_object(self):
        """Get or create preference for user"""
        obj, created = UserApplicationPreference.objects.get_or_create(
            user=self.request.user
        )
        self.check_object_permissions(self.request, obj)
        return obj
    
    @action(detail=False, methods=['get'])
    def analyze(self, request):
        """Analyze user's approval patterns and preferences"""
        strategy_agent = ApplicationStrategyAgent()
        analysis = strategy_agent.analyze_user_preferences(request.user)
        return Response(analysis)


class AutoApplicationBatchViewSet(viewsets.ModelViewSet):
    """ViewSet for AutoApplicationBatch model"""
    
    serializer_class = AutoApplicationBatchSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return AutoApplicationBatch.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def create_batch(self, request):
        """Create a new auto-apply batch with matching jobs"""
        approval_manager = ApprovalManager()
        
        try:
            batch = approval_manager.create_batch(
                user=request.user,
                search_query=request.data.get('search_query'),
                search_location=request.data.get('search_location'),
                search_filters=request.data.get('search_filters'),
                limit=request.data.get('limit', 50)
            )
            serializer = AutoApplicationBatchSerializer(batch)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def review(self, request, pk=None):
        """Get batch with all items for review"""
        approval_manager = ApprovalManager()
        review_data = approval_manager.get_batch_for_review(pk)
        return Response(review_data)
    
    @action(detail=True, methods=['post'])
    def approve_all(self, request, pk=None):
        """Approve all pending items in batch"""
        approval_manager = ApprovalManager()
        batch = approval_manager.approve_all(pk)
        serializer = AutoApplicationBatchSerializer(batch)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def reject_all(self, request, pk=None):
        """Reject all pending items in batch"""
        approval_manager = ApprovalManager()
        batch = approval_manager.reject_all(pk)
        serializer = AutoApplicationBatchSerializer(batch)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """Execute all approved applications in batch"""
        executor = ApplicationExecutor()
        results = executor.execute_batch(pk)
        return Response(results)
    
    @action(detail=True, methods=['get'])
    def progress(self, request, pk=None):
        """Get execution progress of batch"""
        executor = ApplicationExecutor()
        progress = executor.get_batch_progress(pk)
        return Response(progress)
    
    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Pause/cancel batch execution"""
        executor = ApplicationExecutor()
        batch = executor.pause_batch(pk)
        serializer = AutoApplicationBatchSerializer(batch)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def retry_failed(self, request, pk=None):
        """Retry failed applications in batch"""
        executor = ApplicationExecutor()
        results = executor.retry_failed_applications(pk)
        return Response(results)


class AutoApplicationItemViewSet(viewsets.ModelViewSet):
    """ViewSet for AutoApplicationItem model"""
    
    serializer_class = AutoApplicationItemSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return AutoApplicationItem.objects.filter(batch__user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a single application item"""
        approval_manager = ApprovalManager()
        item = approval_manager.approve_item(pk)
        serializer = AutoApplicationItemSerializer(item)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a single application item"""
        approval_manager = ApprovalManager()
        item = approval_manager.reject_item(pk)
        serializer = AutoApplicationItemSerializer(item)
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'])
    def update_cv(self, request, pk=None):
        """Update user-edited CV for an item"""
        approval_manager = ApprovalManager()
        item = approval_manager.update_item_cv(pk, request.data.get('edited_cv'))
        serializer = AutoApplicationItemSerializer(item)
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'])
    def update_cover_letter(self, request, pk=None):
        """Update user-edited cover letter for an item"""
        approval_manager = ApprovalManager()
        item = approval_manager.update_item_cover_letter(
            pk, 
            request.data.get('edited_cover_letter')
        )
        serializer = AutoApplicationItemSerializer(item)
        return Response(serializer.data)


class RealTimeSearchViewSet(viewsets.GenericViewSet):
    """ViewSet for real-time job search with caching"""
    
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Real-time job search with caching"""
        search_engine = JobSearchEngine()
        
        results = search_engine.search(
            query=request.query_params.get('query'),
            location=request.query_params.get('location'),
            job_type=request.query_params.get('job_type'),
            category=request.query_params.get('category'),
            salary_min=request.query_params.get('salary_min'),
            salary_max=request.query_params.get('salary_max'),
            experience_level=request.query_params.get('experience_level'),
            limit=int(request.query_params.get('limit', 50)),
            use_cache=request.query_params.get('use_cache', 'true').lower() == 'true',
            sources=request.query_params.getlist('sources')
        )
        
        return Response(results)
    
    @action(detail=False, methods=['get'])
    def categories(self, request):
        """Get all job categories"""
        search_engine = JobSearchEngine()
        categories = search_engine.get_categories()
        return Response(categories)
    
    @action(detail=False, methods=['post'])
    def clear_cache(self, request):
        """Clear expired cache entries"""
        search_engine = JobSearchEngine()
        count = search_engine.clear_cache()
        return Response({'cleared': count})
