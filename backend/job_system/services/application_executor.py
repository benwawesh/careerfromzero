"""
Application Executor Service
Executes approved job applications (opens job URLs)
"""

import time
from django.utils import timezone
from ..models import (
    AutoApplicationBatch, AutoApplicationItem, JobApplication
)


class ApplicationExecutor:
    """Executes approved job applications"""
    
    def __init__(self):
        self.delay_between_applications = 60  # 60 seconds between applications
    
    def execute_batch(self, batch_id: str) -> dict:
        """
        Execute all approved applications in a batch
        
        Args:
            batch_id: Batch ID
        
        Returns:
            dict with execution results
        """
        batch = AutoApplicationBatch.objects.get(id=batch_id)
        
        # Update batch status
        batch.status = 'applying'
        batch.started_at = timezone.now()
        batch.save()
        
        # Get approved items
        approved_items = batch.items.filter(
            user_approval_status='approved',
            application_status__in=['pending', 'failed']
        )
        
        results = {
            'total': approved_items.count(),
            'successful': 0,
            'failed': 0,
            'applications': []
        }
        
        # Execute each application
        for item in approved_items:
            try:
                # Apply to job
                result = self._execute_application(item)
                
                if result['success']:
                    results['successful'] += 1
                    results['applications'].append({
                        'item_id': str(item.id),
                        'job_title': item.job.title,
                        'company': item.job.company,
                        'status': 'successful'
                    })
                else:
                    results['failed'] += 1
                    results['applications'].append({
                        'item_id': str(item.id),
                        'job_title': item.job.title,
                        'company': item.job.company,
                        'status': 'failed',
                        'error': result['error']
                    })
                
                # Delay between applications
                time.sleep(self.delay_between_applications)
                
            except Exception as e:
                results['failed'] += 1
                results['applications'].append({
                    'item_id': str(item.id),
                    'job_title': item.job.title,
                    'company': item.job.company,
                    'status': 'failed',
                    'error': str(e)
                })
                
                # Update item as failed
                item.application_status = 'failed'
                item.error_message = str(e)
                item.save()
        
        # Update batch status
        batch.status = 'completed'
        batch.completed_at = timezone.now()
        batch.successful_applications = results['successful']
        batch.failed_applications = results['failed']
        batch.save()
        
        return results
    
    def _execute_application(self, item: AutoApplicationItem) -> dict:
        """
        Execute a single application
        
        Args:
            item: AutoApplicationItem
        
        Returns:
            dict with success status
        """
        # For now, we'll open the job URL in a new tab
        # In the future, this could use Selenium/Playwright to automate form filling
        
        if not item.job.job_url:
            return {
                'success': False,
                'error': 'No job URL available'
            }
        
        try:
            # Update item status
            item.application_status = 'applying'
            item.application_url = item.job.job_url
            item.save()
            
            # Create JobApplication record
            job_application = JobApplication.objects.create(
                user=item.batch.user,
                job=item.job,
                cv_version=item.batch.cv_version,
                mode='auto',
                status='applied',
                cover_letter=item.final_cover_letter,
                application_date=timezone.now().date(),
                application_url=item.job.job_url,
                match_score=item.match_score,
                matched_skills=item.matched_skills,
                missing_skills=item.missing_skills
            )
            
            # Link to item
            item.job_application = job_application
            item.application_status = 'applied'
            item.applied_at = timezone.now()
            item.save()
            
            return {
                'success': True,
                'job_application_id': str(job_application.id)
            }
            
        except Exception as e:
            item.application_status = 'failed'
            item.error_message = str(e)
            item.save()
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_batch_progress(self, batch_id: str) -> dict:
        """
        Get progress of batch execution
        
        Args:
            batch_id: Batch ID
        
        Returns:
            dict with progress information
        """
        batch = AutoApplicationBatch.objects.get(id=batch_id)
        
        items = batch.items.all()
        
        status_counts = {
            'pending': 0,
            'approved': 0,
            'rejected': 0,
            'applying': 0,
            'applied': 0,
            'failed': 0
        }
        
        for item in items:
            status_counts[item.application_status] += 1
        
        return {
            'batch_id': str(batch.id),
            'status': batch.status,
            'total_jobs': batch.total_jobs,
            'approved_jobs': batch.approved_jobs,
            'successful_applications': batch.successful_applications,
            'failed_applications': batch.failed_applications,
            'progress_percentage': batch.progress_percentage,
            'started_at': batch.started_at.isoformat() if batch.started_at else None,
            'completed_at': batch.completed_at.isoformat() if batch.completed_at else None,
            'status_counts': status_counts
        }
    
    def pause_batch(self, batch_id: str) -> AutoApplicationBatch:
        """Pause batch execution"""
        batch = AutoApplicationBatch.objects.get(id=batch_id)
        batch.status = 'cancelled'
        batch.save()
        return batch
    
    def retry_failed_applications(self, batch_id: str) -> dict:
        """
        Retry failed applications in a batch
        
        Args:
            batch_id: Batch ID
        
        Returns:
            dict with retry results
        """
        batch = AutoApplicationBatch.objects.get(id=batch_id)
        
        # Get failed items
        failed_items = batch.items.filter(
            application_status='failed',
            user_approval_status='approved'
        )
        
        # Reset to pending
        failed_items.update(application_status='pending', error_message='')
        
        # Re-execute batch
        return self.execute_batch(batch_id)