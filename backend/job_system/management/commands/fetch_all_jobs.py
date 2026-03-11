"""
Fetch ALL jobs from all sources without limits
Handles job expiration and can fetch 100,000+ jobs
"""

from django.core.management.base import BaseCommand
from datetime import datetime, date
from job_system.services.job_scraper import job_fetcher
from job_system.models import Job
from django.utils import timezone
from django.db import models
import time


class Command(BaseCommand):
    help = 'Fetch ALL jobs from all sources (unlimited)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            help='Specific source to fetch (e.g., brightermonday, indeed, all)',
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

        self.stdout.write(self.style.WARNING('=== Unlimited Job Fetch Started ==='))
        self.stdout.write(f'Source: {source}')
        self.stdout.write(f'Query: {query or "all"}')
        self.stdout.write(f'Location: {location or "all"}')
        self.stdout.write()

        # Step 1: Handle expired jobs if requested
        if mark_expired or cleanup_expired:
            self._handle_expired_jobs(cleanup=cleanup_expired)

        # Step 2: Fetch jobs with no limits
        if source == 'all':
            self._fetch_all_sources(query, location)
        elif source == 'kenya':
            self._fetch_kenya_jobs(query)
        elif source == 'international':
            self._fetch_international_jobs(query)
        else:
            self._fetch_single_source(source, query, location)

        self.stdout.write()
        self.stdout.write(self.style.SUCCESS('=== Fetch Complete ==='))
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
        """Fetch from all sources with no limits"""
        self.stdout.write(self.style.WARNING('=== Fetching from ALL Sources ==='))
        
        # Fetch unlimited jobs
        jobs = job_fetcher.fetch_all_jobs(query=query, location=location, limit_per_source=None)
        
        # Save to database
        result = job_fetcher.save_jobs_to_db(jobs)
        
        self.stdout.write(f'Total fetched: {len(jobs)}')
        self.stdout.write(f'Created: {result["created"]}')
        self.stdout.write(f'Updated: {result["updated"]}')
        self.stdout.write(f'Errors: {result["errors"]}')

    def _fetch_kenya_jobs(self, query):
        """Fetch unlimited Kenya jobs"""
        self.stdout.write(self.style.WARNING('=== Fetching Kenya Jobs ==='))
        
        jobs = job_fetcher.fetch_kenya_jobs(query=query, limit_per_source=None)
        result = job_fetcher.save_jobs_to_db(jobs)
        
        self.stdout.write(f'Total fetched: {len(jobs)}')
        self.stdout.write(f'Created: {result["created"]}')
        self.stdout.write(f'Updated: {result["updated"]}')
        self.stdout.write(f'Errors: {result["errors"]}')

    def _fetch_international_jobs(self, query):
        """Fetch unlimited international jobs"""
        self.stdout.write(self.style.WARNING('=== Fetching International Jobs ==='))
        
        jobs = job_fetcher.fetch_international_jobs(query=query, limit_per_source=None)
        result = job_fetcher.save_jobs_to_db(jobs)
        
        self.stdout.write(f'Total fetched: {len(jobs)}')
        self.stdout.write(f'Created: {result["created"]}')
        self.stdout.write(f'Updated: {result["updated"]}')
        self.stdout.write(f'Errors: {result["errors"]}')

    def _fetch_single_source(self, source, query, location):
        """Fetch unlimited jobs from a single source"""
        self.stdout.write(self.style.WARNING(f'=== Fetching from {source.upper()} ==='))
        
        # Map source name to scraper
        scrapers = {
            'remotive': job_fetcher._free_apis[0][1],
            'arbeitnow': job_fetcher._free_apis[1][1],
            'jobicy': job_fetcher._free_apis[2][1],
            'remoteok': job_fetcher._free_apis[3][1],
            'themuse': job_fetcher._free_apis[4][1],
            'brightermonday': job_fetcher._african[0][1],
            'fuzu': job_fetcher._african[1][1],
            'kenyajob': job_fetcher._african[2][1],
            'myjobmag': job_fetcher._african[3][1],
        }
        
        scraper = scrapers.get(source.lower())
        if not scraper:
            self.stdout.write(self.style.ERROR(f'Unknown source: {source}'))
            return
        
        jobs = scraper.fetch_jobs(query=query, location=location, limit=None)
        result = job_fetcher.save_jobs_to_db(jobs)
        
        self.stdout.write(f'Total fetched: {len(jobs)}')
        self.stdout.write(f'Created: {result["created"]}')
        self.stdout.write(f'Updated: {result["updated"]}')
        self.stdout.write(f'Errors: {result["errors"]}')

    def _show_summary(self):
        """Show database summary"""
        self.stdout.write()
        self.stdout.write(self.style.WARNING('=== Database Summary ==='))
        
        total = Job.objects.count()
        active = Job.objects.filter(is_active=True).count()
        expired = total - active
        
        self.stdout.write(f'Total jobs: {total}')
        self.stdout.write(f'Active jobs: {active}')
        self.stdout.write(f'Inactive/expired: {expired}')
        
        self.stdout.write()
        self.stdout.write(self.style.WARNING('=== Jobs by Source ==='))
        
        from django.db.models import Count
        by_source = Job.objects.values('source').annotate(
            count=Count('id'),
            active_count=Count('id', filter=models.Q(is_active=True))
        ).order_by('-count')
        
        for item in by_source:
            source = item['source']
            count = item['count']
            active_count = item['active_count']
            bar = '█' * (count // 10)
            self.stdout.write(f'{source:20} {count:5} (active: {active_count:4}) {bar}')