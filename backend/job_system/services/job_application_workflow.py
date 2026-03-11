"""
Job Application Workflow Service
Orchestrates the complete job application workflow:
1. Analyze CV
2. Match jobs
3. Customize CVs for selected jobs
4. Write cover letters (optional)
5. Create application drafts
"""

from django.core.cache import cache
from django.utils import timezone
from typing import List, Dict, Optional
import logging
import uuid

from cv_builder.models import CV, CVData, CVVersion, CVAnalysis
from job_system.models import Job, JobMatch, JobApplication, AutoApplicationBatch, AutoApplicationItem
from ai_agents.job_matcher_agent import JobMatcherAgent
from ai_agents.cv_customizer_agent import CVCustomizerAgent
from ai_agents.cover_letter_writer_agent import CoverLetterWriterAgent
from cv_builder.services.pdf_generator import CVPDFGenerator

logger = logging.getLogger(__name__)


class JobApplicationWorkflow:
    """
    Orchestrates the complete job application workflow
    Connects CV analysis, job matching, and application creation
    """
    
    def __init__(self):
        self.job_matcher = JobMatcherAgent()
        self.cv_customizer = CVCustomizerAgent()
        self.cover_letter_writer = CoverLetterWriterAgent()
    
    def analyze_cv(self, user, cv_id: str) -> Dict:
        """
        Step 1: Parse and analyze user's CV
        
        Args:
            user: User object
            cv_id: CV UUID
        
        Returns:
            dict with analysis results
        """
        logger.info(f"Analyzing CV {cv_id} for user {user.id}")
        
        try:
            # Get CV
            cv = CV.objects.get(id=cv_id, user=user, is_active=True)
            
            # Check if already analyzed
            if hasattr(cv, 'data') and hasattr(cv.data, 'analysis'):
                return {
                    'status': 'completed',
                    'cv_id': str(cv.id),
                    'title': cv.title,
                    'parsed': hasattr(cv, 'data'),
                    'analyzed': True,
                    'analysis': self._format_analysis(cv.data.analysis)
                }
            
            # Parse CV if not already done
            if not hasattr(cv, 'data'):
                return {
                    'status': 'needs_parsing',
                    'cv_id': str(cv.id),
                    'title': cv.title,
                    'message': 'CV needs to be parsed first',
                    'next_step': 'parse_cv'
                }
            
            # Analyze CV (if parsed but not analyzed)
            # This would trigger an AI agent
            # For now, return basic info
            return {
                'status': 'ready_for_analysis',
                'cv_id': str(cv.id),
                'title': cv.title,
                'parsed': True,
                'analyzed': False,
                'message': 'CV parsed, ready for AI analysis'
            }
        
        except CV.DoesNotExist:
            return {
                'status': 'error',
                'error': 'CV not found'
            }
        except Exception as e:
            logger.error(f"Error analyzing CV: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def match_jobs(self, user, cv_id: str, filters: Optional[Dict] = None, 
                 limit: int = 50, min_score: float = 70.0) -> Dict:
        """
        Step 2: Find jobs matching user's CV
        
        Args:
            user: User object
            cv_id: CV UUID
            filters: Dict of search filters (location, job_type, etc.)
            limit: Maximum jobs to return
            min_score: Minimum match score (0-100)
        
        Returns:
            dict with matched jobs
        """
        logger.info(f"Matching jobs for user {user.id}, CV {cv_id}")
        
        try:
            # Get active CV version
            cv = CV.objects.get(id=cv_id, user=user, is_active=True)
            cv_version = CVVersion.objects.filter(
                cv=cv,
                is_current=True
            ).first()
            
            if not cv_version:
                return {
                    'status': 'error',
                    'error': 'No active CV version found',
                    'message': 'Please create a CV version first'
                }
            
            # Apply filters to job query
            jobs = Job.objects.filter(is_active=True)
            
            if filters:
                if filters.get('location'):
                    jobs = jobs.filter(location__icontains=filters['location'])
                if filters.get('job_type'):
                    jobs = jobs.filter(job_type=filters['job_type'])
                if filters.get('experience_level'):
                    jobs = jobs.filter(experience_level=filters['experience_level'])
                if filters.get('min_salary'):
                    jobs = jobs.filter(salary_min__gte=filters['min_salary'])
            
            jobs = jobs[:limit]
            
            # Match jobs using AI agent
            matched_jobs = []
            
            for job in jobs:
                # Check if already matched (cache)
                existing_match = JobMatch.objects.filter(
                    user=user,
                    job=job,
                    cv_version=cv_version
                ).first()
                
                if existing_match:
                    match_data = {
                        'job_id': str(job.id),
                        'title': job.title,
                        'company': job.company,
                        'location': job.location,
                        'job_type': job.job_type,
                        'experience_level': job.experience_level,
                        'salary_range': job.salary_range,
                        'job_url': job.job_url,
                        'overall_match': float(existing_match.overall_match),
                        'skill_match': float(existing_match.skill_match),
                        'experience_match': float(existing_match.experience_match),
                        'location_match': float(existing_match.location_match or 0),
                        'matched_skills': existing_match.matched_skills,
                        'missing_skills': existing_match.missing_skills,
                        'suggestions': existing_match.suggestions
                    }
                else:
                    # Calculate new match
                    match_result = self.job_matcher.calculate_match(
                        user, job, cv_version
                    )
                    
                    match_data = {
                        'job_id': str(job.id),
                        'title': job.title,
                        'company': job.company,
                        'location': job.location,
                        'job_type': job.job_type,
                        'experience_level': job.experience_level,
                        'salary_range': job.salary_range,
                        'job_url': job.job_url,
                        **match_result
                    }
                
                # Filter by minimum score
                if match_data['overall_match'] >= min_score:
                    matched_jobs.append(match_data)
            
            # Sort by match score
            matched_jobs.sort(key=lambda x: x['overall_match'], reverse=True)
            
            return {
                'status': 'success',
                'cv_id': str(cv_id),
                'total_matched': len(matched_jobs),
                'jobs': matched_jobs
            }
        
        except CV.DoesNotExist:
            return {
                'status': 'error',
                'error': 'CV not found'
            }
        except Exception as e:
            logger.error(f"Error matching jobs: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def batch_customize(self, user, cv_id: str, job_ids: List[str],
                     options: Optional[Dict] = None) -> Dict:
        """
        Step 3 & 4: Generate customizations for selected jobs
        
        Args:
            user: User object
            cv_id: CV UUID
            job_ids: List of Job UUIDs to customize for
            options: Dict with customization options:
                - generate_cv: bool (default: True)
                - generate_cover_letter: bool (default: False)
                - save_as_drafts: bool (default: True)
        
        Returns:
            dict with customization results
        """
        logger.info(f"Batch customizing for {len(job_ids)} jobs, CV {cv_id}")
        
        if not options:
            options = {
                'generate_cv': True,
                'generate_cover_letter': False,
                'save_as_drafts': True
            }
        
        try:
            # Get CV
            cv = CV.objects.get(id=cv_id, user=user, is_active=True)
            cv_version = CVVersion.objects.filter(
                cv=cv,
                is_current=True
            ).first()
            
            if not cv_version:
                return {
                    'status': 'error',
                    'error': 'No active CV version found'
                }
            
            # Get jobs
            jobs = Job.objects.filter(id__in=job_ids, is_active=True)
            
            if len(jobs) != len(job_ids):
                found_ids = [str(j.id) for j in jobs]
                missing = set(job_ids) - set(found_ids)
                logger.warning(f"Some jobs not found: {missing}")
            
            results = {
                'status': 'in_progress',
                'cv_id': str(cv_id),
                'total_jobs': len(jobs),
                'completed': 0,
                'failed': 0,
                'customizations': []
            }
            
            # Process each job
            for i, job in enumerate(jobs, 1):
                logger.info(f"Customizing for job {i}/{len(jobs)}: {job.title}")
                
                try:
                    # Customize CV
                    custom_cv = None
                    if options.get('generate_cv'):
                        cv_result = self.cv_customizer.customize_cv(
                            cv_version, job
                        )
                        custom_cv = cv_result.get('customized_cv')
                    
                    # Write cover letter
                    cover_letter = None
                    if options.get('generate_cover_letter'):
                        letter_result = self.cover_letter_writer.generate_cover_letter(
                            cv_version, job
                        )
                        cover_letter = letter_result.get('cover_letter')
                    
                    # Generate PDF
                    pdf_data = None
                    if custom_cv:
                        pdf_generator = CVPDFGenerator(cv_version)
                        pdf_data = pdf_generator.generate_pdf()
                    
                    customization = {
                        'job_id': str(job.id),
                        'job_title': job.title,
                        'company': job.company,
                        'custom_cv': custom_cv,
                        'cover_letter': cover_letter,
                        'pdf_data': pdf_data,
                        'status': 'completed'
                    }
                    
                    # Save as draft if requested
                    if options.get('save_as_drafts'):
                        app = JobApplication.objects.create(
                            user=user,
                            job=job,
                            cv_version=cv_version,
                            mode='auto',
                            status='draft',
                            match_score=job.match_score if hasattr(job, 'match_score') else 70.0,
                            cover_letter=cover_letter
                        )
                        customization['application_id'] = str(app.id)
                    
                    results['customizations'].append(customization)
                    results['completed'] += 1
                    
                    # Update progress (cache for real-time updates)
                    self._update_progress(user.id, {
                        'total': len(jobs),
                        'current': i,
                        'job_title': job.title,
                        'percentage': int((i / len(jobs)) * 100)
                    })
                
                except Exception as e:
                    logger.error(f"Error customizing for job {job.title}: {e}")
                    results['failed'] += 1
                    results['customizations'].append({
                        'job_id': str(job.id),
                        'job_title': job.title,
                        'status': 'failed',
                        'error': str(e)
                    })
            
            results['status'] = 'completed' if results['failed'] == 0 else 'partial'
            
            return results
        
        except CV.DoesNotExist:
            return {
                'status': 'error',
                'error': 'CV not found'
            }
        except Exception as e:
            logger.error(f"Error in batch customization: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def create_application_batch(self, user, cv_id: str, job_ids: List[str],
                             customizations: List[Dict]) -> Dict:
        """
        Step 5: Create application batch for approval
        
        Args:
            user: User object
            cv_id: CV UUID
            job_ids: List of Job UUIDs
            customizations: List of customization results
        
        Returns:
            dict with batch info
        """
        try:
            # Get CV
            cv = CV.objects.get(id=cv_id, user=user, is_active=True)
            cv_version = CVVersion.objects.filter(
                cv=cv,
                is_current=True
            ).first()
            
            # Create batch
            batch = AutoApplicationBatch.objects.create(
                user=user,
                cv_version=cv_version,
                status='pending_approval',
                total_jobs=len(job_ids)
            )
            
            # Create batch items
            for customization in customizations:
                if customization.get('status') != 'completed':
                    continue
                
                try:
                    job = Job.objects.get(id=customization['job_id'])
                    
                    AutoApplicationItem.objects.create(
                        batch=batch,
                        job=job,
                        user_approval_status='pending',
                        application_status='pending',
                        match_score=customization.get('match_score', 70.0),
                        custom_cv=customization.get('custom_cv'),
                        custom_cover_letter=customization.get('cover_letter')
                    )
                except Job.DoesNotExist:
                    logger.warning(f"Job {customization['job_id']} not found")
            
            batch.refresh_from_db()
            
            return {
                'status': 'success',
                'batch_id': str(batch.id),
                'total_items': batch.total_jobs,
                'approved_items': batch.approved_jobs,
                'rejected_items': batch.rejected_jobs
            }
        
        except CV.DoesNotExist:
            return {
                'status': 'error',
                'error': 'CV not found'
            }
        except Exception as e:
            logger.error(f"Error creating application batch: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _format_analysis(self, analysis: CVAnalysis) -> Dict:
        """Format CV analysis for API response"""
        return {
            'ats_score': analysis.ats_score,
            'overall_score': analysis.overall_score,
            'content_quality_score': analysis.content_quality_score,
            'formatting_score': analysis.formatting_score,
            'strengths': analysis.strengths,
            'weaknesses': analysis.weaknesses,
            'suggestions': analysis.suggestions,
            'formatting_issues': analysis.formatting_issues,
            'missing_keywords': analysis.missing_keywords,
            'missing_sections': analysis.missing_sections
        }
    
    def _update_progress(self, user_id: int, progress_data: Dict):
        """Update progress in cache for real-time updates"""
        cache_key = f"workflow_progress:{user_id}"
        cache.set(cache_key, progress_data, timeout=300)  # 5 minutes
    
    def get_progress(self, user_id: int) -> Optional[Dict]:
        """Get current workflow progress"""
        cache_key = f"workflow_progress:{user_id}"
        return cache.get(cache_key)
    
    def clear_progress(self, user_id: int):
        """Clear workflow progress"""
        cache_key = f"workflow_progress:{user_id}"
        cache.delete(cache_key)