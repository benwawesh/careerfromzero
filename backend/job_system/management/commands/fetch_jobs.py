"""
Fetch jobs from all configured sources and save to the database.

Usage examples:
  python manage.py fetch_jobs                        # fetch everything
  python manage.py fetch_jobs --region kenya         # Kenya boards + JobSpy Kenya
  python manage.py fetch_jobs --region international # Free APIs + JobSpy US/UK/CA/EU
  python manage.py fetch_jobs --query "data analyst" # filtered by keyword
  python manage.py fetch_jobs --query "developer" --region kenya
  python manage.py fetch_jobs --limit 50             # 50 jobs per source
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from job_system.services.job_scraper import job_fetcher
from job_system.models import Job


class Command(BaseCommand):
    help = 'Fetch jobs from all sources (LinkedIn, Indeed, Glassdoor, Remotive, Arbeitnow, Jobicy, RemoteOK, Adzuna, BrighterMonday, Fuzu, KenyaJob, MyJobMag)'

    def add_arguments(self, parser):
        parser.add_argument('--query', type=str, default='',
                            help='Search keyword (default: all jobs)')
        parser.add_argument('--location', type=str, default='',
                            help='Location filter')
        parser.add_argument('--region', type=str, default='all',
                            choices=['all', 'kenya', 'international'],
                            help='Region focus: all | kenya | international (default: all)')
        parser.add_argument('--limit', type=int, default=5000,
                            help='Jobs per source (default: 5000 = unlimited for most sources)')

    def handle(self, *args, **options):
        query = options['query']
        location = options['location']
        region = options['region']
        limit = options['limit']

        before = Job.objects.count()

        self.stdout.write(self.style.SUCCESS('\n=== Job Fetch Starting ==='))
        self.stdout.write(f'  Region  : {region}')
        self.stdout.write(f'  Query   : {query or "(all)"}')
        self.stdout.write(f'  Location: {location or "(any)"}')
        self.stdout.write(f'  Limit   : {limit} per source')
        self.stdout.write('')

        if region == 'kenya':
            jobs = job_fetcher.fetch_kenya_jobs(query=query, limit_per_source=limit)
        elif region == 'international':
            jobs = job_fetcher.fetch_international_jobs(query=query, limit_per_source=limit)
        else:
            jobs = job_fetcher.fetch_all_jobs(query=query, location=location, limit_per_source=limit)

        self.stdout.write(f'Fetched {len(jobs)} total jobs from all sources')

        if not jobs:
            self.stdout.write(self.style.WARNING('No jobs returned — check logs for errors'))
            return

        self.stdout.write('Saving to database...')
        result = job_fetcher.save_jobs_to_db(jobs)

        after = Job.objects.count()
        active = Job.objects.filter(is_active=True).count()

        self.stdout.write(self.style.SUCCESS('\n=== Done ==='))
        self.stdout.write(f'  New jobs created  : {result["created"]}')
        self.stdout.write(f'  Existing updated  : {result["updated"]}')
        self.stdout.write(f'  Errors            : {result["errors"]}')
        self.stdout.write(f'  Total in DB       : {after} (was {before})')
        self.stdout.write(f'  Active jobs       : {active}')
        self.stdout.write(f'  Time              : {timezone.now().strftime("%Y-%m-%d %H:%M")}')

        # Source breakdown
        self.stdout.write('\nSource breakdown (new jobs):')
        source_counts = {}
        for job in jobs:
            src = job.get('source', 'unknown')
            source_counts[src] = source_counts.get(src, 0) + 1
        for src, count in sorted(source_counts.items(), key=lambda x: -x[1]):
            self.stdout.write(f'  {src:<20} {count}')

        # Sample
        recent = Job.objects.filter(is_active=True).order_by('-created_at')[:5]
        if recent:
            self.stdout.write('\nMost recent jobs added:')
            for job in recent:
                self.stdout.write(f'  [{job.source}] {job.title} @ {job.company} — {job.location}')
