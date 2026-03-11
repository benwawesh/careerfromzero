"""
Fetch Jobs from Kenyan Job Boards
================================
Fetches ALL jobs from Kenyan job boards with improved scrapers.

Usage:
    # Fetch from all Kenyan sources
    python manage.py fetch_kenyan_jobs
    
    # Fetch from specific source
    python manage.py fetch_kenyan_jobs --source brightermonday
    
    # With filters
    python manage.py fetch_kenyan_jobs --query developer --location nairobi
"""

from django.core.management.base import BaseCommand
from job_system.services.job_scraper_kenya import kenyan_job_fetcher


class Command(BaseCommand):
    help = 'Fetch jobs from Kenyan job boards'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            help='Specific source to fetch (brightermonday, myjobmag, kenyajob)',
        )
        parser.add_argument(
            '--query',
            type=str,
            default='',
            help='Search query',
        )
        parser.add_argument(
            '--location',
            type=str,
            default='',
            help='Location filter',
        )

    def handle(self, *args, **options):
        source = options.get('source', '')
        query = options.get('query', '')
        location = options.get('location', '')
        
        self.stdout.write(self.style.WARNING('='*70))
        self.stdout.write(self.style.WARNING('  KENYAN JOB BOARD FETCH'))
        self.stdout.write(self.style.WARNING('='*70))
        self.stdout.write()
        
        if source:
            self.stdout.write(f'Fetching from: {source.upper()}')
            if query:
                self.stdout.write(f'Query: {query}')
            if location:
                self.stdout.write(f'Location: {location}')
            self.stdout.write()
            
            jobs = kenyan_job_fetcher.fetch_from_source(source, query, location)
        else:
            self.stdout.write('Fetching from ALL Kenyan sources...')
            if query:
                self.stdout.write(f'Query: {query}')
            if location:
                self.stdout.write(f'Location: {location}')
            self.stdout.write()
            
            jobs = kenyan_job_fetcher.fetch_all_jobs(query, location)
        
        self.stdout.write()
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write(self.style.SUCCESS('  FETCH RESULTS'))
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write()
        self.stdout.write(f'Total fetched: {len(jobs):,}')
        self.stdout.write()
        
        # Save to database
        self.stdout.write('Saving to database...')
        result = kenyan_job_fetcher.save_jobs_to_db(jobs)
        self.stdout.write()
        
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write(self.style.SUCCESS('  DATABASE UPDATE'))
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write()
        self.stdout.write(f'Created: {result["created"]:,}')
        self.stdout.write(f'Updated: {result["updated"]:,}')
        self.stdout.write(f'Errors: {result["errors"]}')
        self.stdout.write()
        
        from job_system.models import Job
        from django.db.models import Count

        KENYAN_SOURCES = [
            'brightermonday', 'myjobmag', 'kenyajob', 'jobwebkenya',
            'ngojobs', 'corporatestaffing', 'nationkenya',
        ]

        total_jobs = Job.objects.count()
        kenyan_jobs = Job.objects.filter(source__in=KENYAN_SOURCES).count()

        self.stdout.write(self.style.WARNING('  SUMMARY'))
        self.stdout.write('='*70)
        self.stdout.write(f'Total jobs in database : {total_jobs:,}')
        self.stdout.write(f'Total Kenyan jobs      : {kenyan_jobs:,}')
        self.stdout.write()
        self.stdout.write('Kenyan jobs by source:')
        breakdown = (Job.objects
                     .filter(source__in=KENYAN_SOURCES)
                     .values('source')
                     .annotate(n=Count('id'))
                     .order_by('-n'))
        for row in breakdown:
            self.stdout.write(f'  {row["source"]:<22} {row["n"]:,}')
        self.stdout.write()
        self.stdout.write(self.style.SUCCESS('Done!'))