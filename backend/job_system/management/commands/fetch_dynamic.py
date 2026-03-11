"""
Dynamic Job Fetch Command - Automatic & Unlimited
================================================
Fetches ALL available jobs automatically without hardcoded limits.
Detects pagination and stops when no more jobs exist.

Usage:
    # Fetch ALL jobs from ALL sources (unlimited)
    python manage.py fetch_dynamic
    
    # Fetch from specific source
    python manage.py fetch_dynamic --source brightermonday
    
    # With filters
    python manage.py fetch_dynamic --query developer --location nairobi
    
    # Mark expired jobs as inactive
    python manage.py fetch_dynamic --mark-expired
    
    # Delete expired jobs
    python manage.py fetch_dynamic --cleanup-expired
"""

from django.core.management.base import BaseCommand
from datetime import datetime, date
from job_system.services.job_scraper_dynamic import dynamic_job_fetcher
from job_system.models import Job
from django.utils import timezone
from django.db.models import Count
import time


class Command(BaseCommand):
    help = 'Fetch ALL jobs dynamically (no limits) with automatic pagination detection'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            help='Specific source to fetch (e.g., brightermonday, remoteok, all)',
            default='all'
        )
        parser.add_argument(
            '--query',
            type=str,
            help='Search query (optional)',
            default=''
        )
        parser.add_argument(
            '--location',
            type=str,
            help='Location filter (optional)',
            default=''
        )
        parser.add_argument(
            '--mark-expired',
            action='store_true',
            help='Mark expired jobs as inactive',
        )
        parser.add_argument(
            '--cleanup-expired',
            action='store_true',
            help='Delete expired jobs from database',
        )

    def handle(self, *args, **options):
        source = options['source']
        query = options['query']
        location = options['location']
        mark_expired = options['mark_expired']
        cleanup_expired = options['cleanup_expired']

        self.stdout.write(self.style.WARNING('='*70))
        self.stdout.write(self.style.WARNING('  DYNAMIC JOB FETCH - AUTOMATIC & UNLIMITED'))
        self.stdout.write(self.style.WARNING('='*70))
        self.stdout.write()
        self.stdout.write(f'Source: {source.upper()}')
        self.stdout.write(f'Query: {query or "ALL"}')
        self.stdout.write(f'Location: {location or "ALL"}')
        self.stdout.write()

        # Step 1: Handle expired jobs if requested
        if mark_expired or cleanup_expired:
            self._handle_expired_jobs(cleanup=cleanup_expired)

        # Step 2: Fetch jobs dynamically
        if source == 'all':
            self._fetch_all_sources(query, location)
        else:
            self._fetch_single_source(source, query, location)

        self.stdout.write()
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write(self.style.SUCCESS('  FETCH COMPLETE!'))
        self.stdout.write(self.style.SUCCESS('='*70))
        self._show_summary()

    def _handle_expired_jobs(self, cleanup=False):
        """Mark or delete expired jobs"""
        self.stdout.write(self.style.WARNING('=== Handling Expired Jobs ==='))
        
        today = date.today()
        expired_jobs = Job.objects.filter(expiry_date__lt=today, is_active=True)
        
        if cleanup:
            count = expired_jobs.count()
            expired_jobs.delete()
            self.stdout.write(f'Deleted {count} expired jobs')
        else:
            count = expired_jobs.update(is_active=False)
            self.stdout.write(f'Marked {count} expired jobs as inactive')
        
        # Also mark old jobs as expired if no expiry_date (older than 90 days)
        ninety_days_ago = timezone.now() - timezone.timedelta(days=90)
        very_old = Job.objects.filter(
            expiry_date__isnull=True,
            posted_date__lt=ninety_days_ago,
            is_active=True
        )
        
        if cleanup:
            count = very_old.count()
            very_old.delete()
            self.stdout.write(f'Deleted {count} jobs older than 90 days')
        else:
            count = very_old.update(is_active=False)
            self.stdout.write(f'Marked {count} jobs older than 90 days as inactive')
        
        self.stdout.write()

    def _fetch_all_sources(self, query, location):
        """Fetch from all sources dynamically"""
        self.stdout.write(self.style.WARNING('=== Fetching from ALL Sources ==='))
        self.stdout.write('This will fetch ALL available jobs from all sources...')
        self.stdout.write('No limits - will stop when no more jobs exist!')
        self.stdout.write()
        
        start_time = time.time()
        
        # Fetch unlimited jobs using dynamic scraper
        jobs = dynamic_job_fetcher.fetch_all_jobs(query=query, location=location)
        
        # Save to database
        self.stdout.write()
        self.stdout.write(self.style.WARNING('=== Saving to Database ==='))
        result = dynamic_job_fetcher.save_jobs_to_db(jobs)
        
        elapsed = time.time() - start_time
        
        self.stdout.write()
        self.stdout.write(self.style.SUCCESS(f'=== Fetch Results ==='))
        self.stdout.write(f'Total fetched: {len(jobs)}')
        self.stdout.write(f'Created: {result["created"]}')
        self.stdout.write(f'Updated: {result["updated"]}')
        self.stdout.write(f'Errors: {result["errors"]}')
        self.stdout.write(f'Time taken: {elapsed:.1f} seconds')

    def _fetch_single_source(self, source, query, location):
        """Fetch unlimited jobs from a single source"""
        self.stdout.write(self.style.WARNING(f'=== Fetching from {source.upper()} ==='))
        self.stdout.write(f'This will fetch ALL jobs from {source}...')
        self.stdout.write('No limits - will stop when no more jobs exist!')
        self.stdout.write()
        
        start_time = time.time()
        
        # Fetch unlimited jobs from specific source
        jobs = dynamic_job_fetcher.fetch_from_source(source, query, location)
        
        if not jobs:
            self.stdout.write(self.style.ERROR(f'No jobs fetched from {source}'))
            self.stdout.write(self.style.WARNING('Possible reasons:'))
            self.stdout.write('  - Source name is incorrect')
            self.stdout.write('  - Source is down or blocking requests')
            self.stdout.write('  - No jobs match your query')
            return
        
        # Save to database
        self.stdout.write()
        self.stdout.write(self.style.WARNING('=== Saving to Database ==='))
        result = dynamic_job_fetcher.save_jobs_to_db(jobs)
        
        elapsed = time.time() - start_time
        
        self.stdout.write()
        self.stdout.write(self.style.SUCCESS(f'=== Fetch Results ==='))
        self.stdout.write(f'Source: {source.upper()}')
        self.stdout.write(f'Total fetched: {len(jobs)}')
        self.stdout.write(f'Created: {result["created"]}')
        self.stdout.write(f'Updated: {result["updated"]}')
        self.stdout.write(f'Errors: {result["errors"]}')
        self.stdout.write(f'Time taken: {elapsed:.1f} seconds')

    def _show_summary(self):
        """Show database summary"""
        self.stdout.write()
        self.stdout.write(self.style.WARNING('=== Database Summary ==='))
        
        total = Job.objects.count()
        active = Job.objects.filter(is_active=True).count()
        expired = total - active
        
        self.stdout.write(f'Total jobs: {total:,}')
        self.stdout.write(f'Active jobs: {active:,}')
        self.stdout.write(f'Inactive/expired: {expired:,}')
        
        self.stdout.write()
        self.stdout.write(self.style.WARNING('=== Jobs by Source ==='))
        self.stdout.write()
        
        by_source = Job.objects.values('source').annotate(
            count=Count('id'),
            active_count=Count('id', filter=models.Q(is_active=True))
        ).order_by('-count')
        
        max_count = by_source.first()['count'] if by_source.exists() else 1
        
        for item in by_source:
            source = item['source']
            count = item['count']
            active_count = item['active_count']
            bar_length = int((count / max_count) * 50) if max_count > 0 else 0
            bar = '█' * bar_length
            self.stdout.write(f'{source:20} {count:5} (active: {active_count:4}) {bar}')
        
        self.stdout.write()
        self.stdout.write(self.style.SUCCESS('✓ Done! All available jobs fetched successfully.'))


# Import models.Q at module level
from django.db import models