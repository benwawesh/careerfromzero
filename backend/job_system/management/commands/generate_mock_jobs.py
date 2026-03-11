"""
Generate Mock Jobs for Testing Pagination
=======================================
Creates realistic job listings to test the system with large datasets.

Usage:
    # Generate 10,000 jobs
    python manage.py generate_mock_jobs 10000
    
    # Generate 50,000 jobs
    python manage.py generate_mock_jobs 50000
    
    # Clear all mock jobs
    python manage.py generate_mock_jobs --clear
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from job_system.models import Job
import random
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Generate realistic mock job listings for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            'count',
            type=int,
            nargs='?',
            default=10000,
            help='Number of mock jobs to generate (default: 10000)',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all mock jobs before generating new ones',
        )

    def handle(self, *args, **options):
        count = options['count']
        clear = options['clear']
        
        self.stdout.write(self.style.WARNING('='*70))
        self.stdout.write(self.style.WARNING('  MOCK JOB GENERATOR'))
        self.stdout.write(self.style.WARNING('='*70))
        self.stdout.write()
        
        # Clear mock jobs if requested
        if clear:
            deleted = Job.objects.filter(source='mock').delete()[0]
            self.stdout.write(self.style.WARNING(f'Cleared {deleted} mock jobs'))
            self.stdout.write()
        
        # Job titles
        titles = [
            'Senior Software Engineer',
            'Full Stack Developer',
            'Frontend Developer',
            'Backend Developer',
            'DevOps Engineer',
            'Data Scientist',
            'Machine Learning Engineer',
            'Product Manager',
            'UX Designer',
            'UI Designer',
            'Mobile Developer (iOS)',
            'Mobile Developer (Android)',
            'QA Engineer',
            'Technical Writer',
            'Business Analyst',
            'Project Manager',
            'Scrum Master',
            'Cloud Architect',
            'Security Engineer',
        ]
        
        # Companies
        companies = [
            'TechCorp', 'InnovateTech', 'DigitalSolutions', 'CloudFirst',
            'DataDriven', 'SmartSystems', 'FutureTech', 'GlobalTech',
            'NextGen', 'PrimeSoft', 'CyberSystems', 'NetSolutions',
            'WebWorks', 'AppMakers', 'CodeCraft', 'DevHub',
            'SoftServe', 'TechVision', 'DigitalDreams', 'CloudNine',
        ]
        
        # Locations
        locations = [
            'Nairobi, Kenya',
            'Remote',
            'Mombasa, Kenya',
            'Kisumu, Kenya',
            'Nakuru, Kenya',
            'Eldoret, Kenya',
            'Remote (Kenya)',
            'Remote (East Africa)',
        ]
        
        # Job types
        job_types = ['full_time', 'remote', 'contract', 'part_time', 'freelance']
        
        # Experience levels
        exp_levels = ['entry_level', 'mid_level', 'senior_level', 'lead']
        
        # Sources (for variety)
        sources = ['indeed', 'linkedin', 'glassdoor', 'remoteok', 'brightermonday']
        
        # Skills
        all_skills = [
            'Python', 'JavaScript', 'React', 'Node.js', 'Django',
            'Java', 'Spring', 'AWS', 'Azure', 'Docker',
            'Kubernetes', 'Git', 'Agile', 'Scrum', 'SQL',
            'MongoDB', 'PostgreSQL', 'Redis', 'GraphQL', 'REST API',
            'TypeScript', 'Vue.js', 'Angular', 'Next.js', 'Express',
        ]
        
        # Descriptions
        descriptions = [
            'We are looking for a talented developer to join our team.',
            'Join our innovative company and work on cutting-edge projects.',
            'Exciting opportunity for experienced developers.',
            'Great role for someone passionate about technology.',
            'Work with a dynamic team on impactful projects.',
        ]
        
        self.stdout.write(f'Generating {count:,} mock jobs...')
        self.stdout.write()
        
        batch_size = 1000
        created = 0
        
        for i in range(0, count, batch_size):
            batch = []
            batch_end = min(i + batch_size, count)
            
            for j in range(i, batch_end):
                title = random.choice(titles)
                company = random.choice(companies)
                location = random.choice(locations)
                job_type = random.choice(job_types)
                exp_level = random.choice(exp_levels)
                source = random.choice(sources)
                skills = random.sample(all_skills, random.randint(3, 8))
                description = random.choice(descriptions)
                
                # Random salary
                salary_min = random.choice([30000, 50000, 70000, 100000, 150000])
                salary_max = salary_min + random.choice([10000, 20000, 50000, 100000])
                
                # Random posted date (within last 90 days)
                days_ago = random.randint(0, 90)
                posted_date = timezone.now() - timedelta(days=days_ago)
                
                batch.append(Job(
                    title=title,
                    company=company,
                    description=description,
                    location=location,
                    job_type=job_type,
                    experience_level=exp_level,
                    source=source,
                    external_id=f"mock_{j}",
                    skills_required=skills,
                    salary_min=salary_min,
                    salary_max=salary_max,
                    salary_currency='KES',
                    posted_date=posted_date,
                    is_active=True,
                    created_at=timezone.now(),
                ))
            
            # Create batch
            created_batch = Job.objects.bulk_create(batch, ignore_conflicts=True)
            created += len(created_batch)
            
            # Progress
            progress = (batch_end / count) * 100
            self.stdout.write(
                f'Progress: {progress:.1f}% ({batch_end:,}/{count:,} jobs created)',
                ending='\r'
            )
        
        self.stdout.write()
        self.stdout.write()
        
        # Summary
        total_jobs = Job.objects.count()
        mock_jobs = Job.objects.filter(source='mock').count()
        
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write(self.style.SUCCESS('  GENERATION COMPLETE'))
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write()
        self.stdout.write(f'Created: {created:,} mock jobs')
        self.stdout.write(f'Total jobs in database: {total_jobs:,}')
        self.stdout.write(f'Mock jobs: {mock_jobs:,}')
        self.stdout.write(f'Real jobs: {total_jobs - mock_jobs:,}')
        self.stdout.write()
        
        # Show jobs by source
        self.stdout.write(self.style.WARNING('Jobs by Source:'))
        self.stdout.write()
        by_source = Job.objects.values('source').annotate(
            count=models.Count('id')
        ).order_by('-count')
        
        for item in by_source[:10]:
            self.stdout.write(
                f'  {item["source"]:20} {item["count"]:6,}'
            )
        
        self.stdout.write()
        self.stdout.write(self.style.SUCCESS('✓ Mock jobs generated successfully!'))