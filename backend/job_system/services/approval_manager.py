"""
Approval Manager Service
Handles auto-apply approval workflow
"""

from django.utils import timezone
from django.db import transaction
from ..models import (
    AutoApplicationBatch, AutoApplicationItem, UserApplicationPreference
)
from ai_agents.job_matcher_agent import JobMatcherAgent
from ai_agents.cv_customizer_agent import CVCustomizerAgent
from ai_agents.cover_letter_writer_agent import CoverLetterWriterAgent
from cv_builder.models import CVVersion


class ApprovalManager:
    """Manages auto-apply approval workflow"""
    
    def __init__(self):
        self.job_matcher = JobMatcherAgent()
        self.cv_customizer = CVCustomizerAgent()
        self.cover_letter_writer = CoverLetterWriterAgent()
        self._strategy_agent = None
    
    @property
    def strategy_agent(self):
        """Lazy load strategy agent to avoid circular import"""
        if self._strategy_agent is None:
            from ai_agents.application_strategy_agent import ApplicationStrategyAgent
            self._strategy_agent = ApplicationStrategyAgent()
        return self._strategy_agent
    
    def create_batch(self, user, search_query: str = None, 
                    search_location: str = None, 
                    search_filters: dict = None,
                    limit: int = 50) -> AutoApplicationBatch:
        """
        Create a new auto-apply batch with matching jobs
        
        Args:
            user: User object
            search_query: Search query used
            search_location: Location searched
            search_filters: Filters applied
            limit: Maximum jobs to include
        
        Returns:
            AutoApplicationBatch object
        """
        # Get active CV
        cv_version = CVVersion.objects.filter(
            cv__user=user,
            is_current=True
        ).first()
        
        if not cv_version:
            raise ValueError("No active CV found")
        
        # Create batch
        batch = AutoApplicationBatch.objects.create(
            user=user,
            cv_version=cv_version,
            search_query=search_query,
            search_location=search_location,
            search_filters=search_filters or {},
            status='draft',
            total_jobs=0
        )
        
        # Find matching jobs
        matched_jobs = self.job_matcher.find_matching_jobs(
            user, 
            limit=limit,
            min_score=70.0
        )
        
        if not matched_jobs:
            batch.status = 'completed'
            batch.save()
            return batch
        
        # Create items for each job
        for match_data in matched_jobs:
            job = match_data['job']
            
            # Check if should auto-approve
            should_approve = self.strategy_agent.should_auto_approve(
                user, job, match_data['overall_match']
            )
            
            # Create item
            item = AutoApplicationItem.objects.create(
                batch=batch,
                job=job,
                match_score=match_data['overall_match'],
                matched_skills=match_data['matched_skills'],
                missing_skills=match_data['missing_skills'],
                user_approval_status='approved' if should_approve else 'pending'
            )
            
            # Generate custom CV
            custom_cv = self.cv_customizer.customize_cv(user, job, cv_version)
            item.custom_cv = custom_cv.get('custom_cv')
            item.save()
            
            # Generate cover letter
            cover_letter = self.cover_letter_writer.write_cover_letter(
                user, job, cv_version
            )
            item.custom_cover_letter = cover_letter.get('cover_letter')
            item.save()
        
        # Update batch statistics
        batch.total_jobs = batch.items.count()
        batch.approved_jobs = batch.items.filter(
            user_approval_status='approved'
        ).count()
        batch.status = 'pending_approval'
        batch.save()
        
        return batch
    
    def approve_item(self, item_id: str) -> AutoApplicationItem:
        """Approve a single application item"""
        item = AutoApplicationItem.objects.get(id=item_id)
        item.user_approval_status = 'approved'
        item.save()
        
        # Update batch
        self._update_batch_stats(item.batch)
        
        return item
    
    def reject_item(self, item_id: str) -> AutoApplicationItem:
        """Reject a single application item"""
        item = AutoApplicationItem.objects.get(id=item_id)
        item.user_approval_status = 'rejected'
        item.save()
        
        # Update batch
        self._update_batch_stats(item.batch)
        
        return item
    
    def approve_all(self, batch_id: str) -> AutoApplicationBatch:
        """Approve all pending items in a batch"""
        batch = AutoApplicationBatch.objects.get(id=batch_id)
        
        # Approve all pending items
        batch.items.filter(user_approval_status='pending').update(
            user_approval_status='approved'
        )
        
        # Update batch stats
        self._update_batch_stats(batch)
        
        return batch
    
    def reject_all(self, batch_id: str) -> AutoApplicationBatch:
        """Reject all pending items in a batch"""
        batch = AutoApplicationBatch.objects.get(id=batch_id)
        
        # Reject all pending items
        batch.items.filter(user_approval_status='pending').update(
            user_approval_status='rejected'
        )
        
        # Update batch stats
        self._update_batch_stats(batch)
        
        return batch
    
    def update_item_cv(self, item_id: str, edited_cv: dict) -> AutoApplicationItem:
        """Update user-edited CV for an item"""
        item = AutoApplicationItem.objects.get(id=item_id)
        item.edited_cv = edited_cv
        item.save()
        
        return item
    
    def update_item_cover_letter(self, item_id: str, 
                               edited_cover_letter: str) -> AutoApplicationItem:
        """Update user-edited cover letter for an item"""
        item = AutoApplicationItem.objects.get(id=item_id)
        item.edited_cover_letter = edited_cover_letter
        item.save()
        
        return item
    
    def get_batch_for_review(self, batch_id: str) -> dict:
        """Get batch with all items for review"""
        batch = AutoApplicationBatch.objects.get(id=batch_id)
        
        items = batch.items.all().order_by('-match_score')
        
        return {
            'batch': {
                'id': str(batch.id),
                'status': batch.status,
                'total_jobs': batch.total_jobs,
                'approved_jobs': batch.approved_jobs,
                'rejected_jobs': batch.rejected_jobs,
                'search_query': batch.search_query,
                'search_location': batch.search_location,
                'created_at': batch.created_at.isoformat()
            },
            'items': [
                {
                    'id': str(item.id),
                    'job': {
                        'id': str(item.job.id),
                        'title': item.job.title,
                        'company': item.job.company,
                        'location': item.job.location,
                        'salary_range': item.job.salary_range,
                        'job_url': item.job.job_url
                    },
                    'match_score': float(item.match_score),
                    'matched_skills': item.matched_skills,
                    'missing_skills': item.missing_skills,
                    'user_approval_status': item.user_approval_status,
                    'custom_cv': item.custom_cv,
                    'custom_cover_letter': item.custom_cover_letter,
                    'final_cv': item.final_cv,
                    'final_cover_letter': item.final_cover_letter
                }
                for item in items
            ]
        }
    
    def get_user_batches(self, user, status: str = None) -> list:
        """Get all batches for a user"""
        batches = AutoApplicationBatch.objects.filter(user=user)
        
        if status:
            batches = batches.filter(status=status)
        
        return batches.order_by('-created_at')
    
    def _update_batch_stats(self, batch: AutoApplicationBatch):
        """Update batch statistics"""
        batch.total_jobs = batch.items.count()
        batch.approved_jobs = batch.items.filter(
            user_approval_status='approved'
        ).count()
        batch.rejected_jobs = batch.items.filter(
            user_approval_status='rejected'
        ).count()
        batch.save()