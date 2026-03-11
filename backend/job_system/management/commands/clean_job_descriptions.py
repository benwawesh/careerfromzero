"""
Strip raw HTML tags from existing job descriptions in the database.
Run once after updating the scraper.

Usage: python manage.py clean_job_descriptions
"""

import re
from django.core.management.base import BaseCommand
from bs4 import BeautifulSoup
from job_system.models import Job


def strip_html(text: str) -> str:
    if not text:
        return ''
    cleaned = BeautifulSoup(text, 'html.parser').get_text(separator=' ')
    return re.sub(r'\s+', ' ', cleaned).strip()


class Command(BaseCommand):
    help = 'Strip HTML tags from job descriptions stored in the database'

    def handle(self, *args, **options):
        jobs = Job.objects.exclude(description='').only('id', 'description')
        total = jobs.count()
        fixed = 0

        self.stdout.write(f'Checking {total} jobs...')

        for job in jobs.iterator():
            if '<' in (job.description or '') and '>' in (job.description or ''):
                cleaned = strip_html(job.description)
                if cleaned != job.description:
                    job.description = cleaned
                    job.save(update_fields=['description'])
                    fixed += 1

        self.stdout.write(self.style.SUCCESS(f'Done. Fixed {fixed} / {total} job descriptions.'))
