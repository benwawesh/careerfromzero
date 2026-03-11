"""
Management command to fetch and STRUCTURE job details properly
Uses Three-Layer Approach for each job board:
1. Header (Fast Facts) - Title, Company, Location, Date, Experience
2. Job Summary - Single paragraph elevator pitch
3. Job Description - Organized bullet points by section

Each job board has a CUSTOM parser because they're all different.
"""

from django.core.management.base import BaseCommand
from job_system.models import Job
import requests
from bs4 import BeautifulSoup
import logging
import re

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Fetch and STRUCTURE job details into organized sections'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=100, help='Max jobs to update')
        parser.add_argument('--source', type=str, help='Specific source (myjobmag, brightermonday)')
        parser.add_argument('--force', action='store_true', help='Force update')

    def handle(self, *args, **options):
        limit = options.get('limit', 100)
        source = options.get('source')
        force = options.get('force', False)
        
        queryset = Job.objects.filter(is_active=True)
        if source:
            queryset = queryset.filter(source=source)
        
        if force:
            self.stdout.write(f"Force updating {source or 'all sources'}")
        else:
            queryset = queryset.filter(description='')
            self.stdout.write(f"Updating empty descriptions from {source or 'all sources'}")
        
        jobs = list(queryset[:limit])
        total = len(jobs)
        self.stdout.write(f"Found {total} jobs to update")
        
        if total == 0:
            self.stdout.write(self.style.WARNING("No jobs to update!"))
            return
        
        updated = failed = 0
        for i, job in enumerate(jobs, 1):
            self.stdout.write(f"[{i}/{total}] {job.title[:50]}...")
            try:
                if job.source == 'myjobmag':
                    self._update_myjobmag(job)
                elif job.source == 'brightermonday':
                    self._update_brightermonday(job)
                elif job.source == 'jobwebkenya':
                    self._update_jobwebkenya(job)
                elif job.source == 'ngojobs':
                    self._update_ngojobs(job)
                else:
                    self.stdout.write(f"  ⊘ No parser for {job.source}")
                    failed += 1
                    continue
                
                job.save()
                updated += 1
                self.stdout.write(f"  ✓ Structured!")
            except Exception as e:
                logger.error(f"Failed job {job.id}: {e}")
                failed += 1
                self.stdout.write(f"  ✗ {str(e)[:60]}")
        
        self.stdout.write(self.style.SUCCESS(f"\n✓ Structured: {updated}"))
        self.stdout.write(self.style.ERROR(f"✗ Failed: {failed}"))

    # ══════════════════════════════════════════════════════════════════════════════
    # BRIGHTERMONDAY - Custom Parser (React-based, data-cy attributes)
    # ══════════════════════════════════════════════════════════════════════════════

    def _update_brightermonday(self, job):
        """BrighterMonday: Uses React data-cy attributes, very structured"""
        if not job.job_url:
            raise Exception("No URL")
        
        r = requests.get(job.job_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if r.status_code != 200:
            raise Exception(f"HTTP {r.status_code}")
        
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # LAYER 1: HEADER (Fast Facts) - BrighterMonday uses data-cy attributes
        title = soup.find('h1')
        if title:
            job.title = title.get_text(strip=True)[:200]
        
        company = soup.find('a', {'data-cy': 'company-link'})
        if company:
            job.company = company.get_text(strip=True)[:200]
        
        location = soup.find('span', {'data-cy': 'job-location'})
        if location:
            job.location = location.get_text(strip=True)[:200]
        
        job_type = soup.find('span', {'data-cy': 'job-type'})
        if job_type:
            job.job_type = job_type.get_text(strip=True).lower().replace(' ', '_')[:50]
        
        exp_level = soup.find('span', {'data-cy': 'experience-level'})
        if exp_level:
            job.experience_level = exp_level.get_text(strip=True).lower().replace(' ', '_')[:50]
        
        # LAYER 2 & 3: DESCRIPTION - Find main description container
        desc = soup.find('div', {'data-cy': 'job-description'})
        if not desc:
            desc = soup.find('div', class_=re.compile(r'description|details', re.I))
        
        if desc:
            # Remove scripts
            for script in desc.find_all('script'):
                script.decompose()
            
            text = desc.get_text(separator='\n', strip=True)
            self._parse_brightermonday_structure(job, text)

    def _parse_brightermonday_structure(self, job, text):
        """BrighterMonday structure: typically has clear sections"""
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        
        current_section = 'summary'
        summary_lines = []
        responsibilities = []
        requirements = []
        benefits = []
        
        for line in lines:
            line_upper = line.upper()
            
            # BrighterMonday section headers
            if 'ABOUT THE ROLE' in line_upper or 'SUMMARY' in line_upper or 'POSITION SUMMARY' in line_upper:
                current_section = 'summary'
                continue
            elif 'WHAT YOU WILL DO' in line_upper or 'RESPONSIBILITIES' in line_upper or 'DUTIES' in line_upper:
                current_section = 'responsibilities'
                continue
            elif 'WHAT WE ARE LOOKING FOR' in line_upper or 'REQUIREMENTS' in line_upper or 'QUALIFICATIONS' in line_upper:
                current_section = 'requirements'
                continue
            elif 'WHAT WE OFFER' in line_upper or 'BENEFITS' in line_upper:
                current_section = 'benefits'
                continue
            
            # Add to appropriate section
            if current_section == 'summary':
                if len(line) > 20 and not line_upper.startswith('•'):
                    summary_lines.append(line)
            elif current_section == 'responsibilities':
                if self._is_bullet_point(line) or len(line) > 10:
                    responsibilities.append(self._clean_bullet(line))
            elif current_section == 'requirements':
                if self._is_bullet_point(line) or len(line) > 10:
                    requirements.append(self._clean_bullet(line))
            elif current_section == 'benefits':
                if self._is_bullet_point(line) or len(line) > 10:
                    benefits.append(self._clean_bullet(line))
        
        # Save structured data
        if summary_lines:
            job.description = ' '.join(summary_lines[:2])  # First 2 paragraphs as summary
        if responsibilities:
            job.responsibilities = responsibilities[:15]
        if requirements:
            job.requirements = requirements[:15]
        if benefits:
            job.benefits = benefits[:10]
        if requirements:
            job.skills_required = self._extract_skills(requirements)[:10]

    # ══════════════════════════════════════════════════════════════════════════════
    # MYJOBMAG - Custom Parser (Traditional HTML, specific section headers)
    # ══════════════════════════════════════════════════════════════════════════════

    def _update_myjobmag(self, job):
        """MyJobMag: Traditional HTML with very specific section headers"""
        if not job.job_url:
            raise Exception("No URL")
        
        r = requests.get(job.job_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if r.status_code != 200:
            raise Exception(f"HTTP {r.status_code}")
        
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # LAYER 1: HEADER (with length limits)
        title = soup.find('h1')
        if title:
            job.title = title.get_text(strip=True)[:200]
        
        # MyJobMag metadata often in specific divs
        company = soup.find('div', class_=re.compile(r'company|employer', re.I))
        if company:
            job.company = company.get_text(strip=True)[:200]
        
        location = soup.find('span', class_=re.compile(r'location', re.I))
        if location:
            job.location = location.get_text(strip=True)[:200]
        
        # LAYER 2 & 3: DESCRIPTION - MyJobMag has very specific headers
        content_divs = soup.find_all('div', class_=re.compile(r'content|description|details', re.I))
        
        for div in content_divs:
            for script in div.find_all('script'):
                script.decompose()
            
            text = div.get_text(separator='\n', strip=True)
            if len(text) > 300:  # Substantial content
                self._parse_myjobmag_structure(job, text)
                break

    def _parse_myjobmag_structure(self, job, text):
        """MyJobMag structure: VERY specific headers like 'Job Purpose Statement'"""
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        
        summary_lines = []
        responsibilities = []
        requirements = []
        benefits = []
        
        current_section = 'other'
        
        for line in lines:
            line_upper = line.upper()
            
            # MyJobMag SPECIFIC headers - these are exact matches!
            if 'JOB PURPOSE STATEMENT' in line_upper or 'POSITION SUMMARY' in line_upper:
                current_section = 'summary'
                continue
            elif 'JOB DESCRIPTION' in line_upper:
                current_section = 'responsibilities'
                continue
            elif 'WHAT YOU WILL DO' in line_upper or 'DUTIES AND RESPONSIBILITIES' in line_upper:
                current_section = 'responsibilities'
                continue
            elif 'JOB SPECIFICATION' in line_upper:
                current_section = 'requirements'
                continue
            elif 'REQUIREMENTS' in line_upper or 'QUALIFICATIONS' in line_upper:
                current_section = 'requirements'
                continue
            elif 'ACADEMIC' in line_upper:
                current_section = 'requirements'
                continue
            elif 'PROFESSIONAL QUALIFICATIONS' in line_upper or 'EXPERIENCE' in line_upper:
                current_section = 'requirements'
                continue
            elif 'METHOD OF APPLICATION' in line_upper or 'HOW TO APPLY' in line_upper:
                current_section = 'application'
                continue
            elif 'BENEFITS' in line_upper:
                current_section = 'benefits'
                continue
            
            # Add to section (skip obvious headers)
            if line_upper.startswith('JOB') or line_upper.startswith('POSITION'):
                continue
            
            if current_section == 'summary':
                if len(line) > 20 and not line_upper.startswith('•'):
                    summary_lines.append(line)
            elif current_section == 'responsibilities':
                if self._is_bullet_point(line) or len(line) > 10:
                    responsibilities.append(self._clean_bullet(line))
            elif current_section == 'requirements':
                if self._is_bullet_point(line) or len(line) > 10:
                    requirements.append(self._clean_bullet(line))
            elif current_section == 'benefits':
                if self._is_bullet_point(line) or len(line) > 10:
                    benefits.append(self._clean_bullet(line))
            elif current_section == 'application':
                # Add to description
                if not job.description:
                    job.description = line
                else:
                    job.description += ' ' + line
        
        # Save structured data
        if summary_lines:
            if job.description:
                job.description = ' '.join(summary_lines[:2]) + '\n\n' + job.description
            else:
                job.description = ' '.join(summary_lines[:2])
        
        if responsibilities:
            job.responsibilities = responsibilities[:15]
        if requirements:
            job.requirements = requirements[:15]
        if benefits:
            job.benefits = benefits[:10]
        if requirements:
            job.skills_required = self._extract_skills(requirements)[:10]

    # ══════════════════════════════════════════════════════════════════════════════
    # JOBWEBKENYA - Custom Parser (Traditional HTML)
    # ══════════════════════════════════════════════════════════════════════════════

    def _update_jobwebkenya(self, job):
        """JobwebKenya: Traditional HTML structure"""
        if not job.job_url:
            raise Exception("No URL")
        
        r = requests.get(job.job_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if r.status_code != 200:
            raise Exception(f"HTTP {r.status_code}")
        
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # LAYER 1: HEADER
        title = soup.find('h1')
        if title:
            job.title = title.get_text(strip=True)[:200]
        
        company = soup.find('div', class_=re.compile(r'company|employer', re.I))
        if company:
            job.company = company.get_text(strip=True)[:200]
        
        # LAYER 2 & 3: DESCRIPTION
        desc_selectors = ['div.job-description', 'div.description', 'div.job-details', 'div.content']
        for sel in desc_selectors:
            desc = soup.select_one(sel)
            if desc:
                for script in desc.find_all('script'):
                    script.decompose()
                text = desc.get_text(separator='\n', strip=True)
                self._parse_jobwebkenya_structure(job, text)
                break

    def _parse_jobwebkenya_structure(self, job, text):
        """JobwebKenya structure: Simple section headers"""
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        
        summary_lines = []
        responsibilities = []
        requirements = []
        
        current_section = 'summary'
        
        for line in lines:
            line_upper = line.upper()
            
            if 'DESCRIPTION' in line_upper and 'JOB' in line_upper:
                current_section = 'responsibilities'
                continue
            elif 'REQUIREMENTS' in line_upper or 'QUALIFICATIONS' in line_upper:
                current_section = 'requirements'
                continue
            elif 'RESPONSIBILITIES' in line_upper or 'DUTIES' in line_upper:
                current_section = 'responsibilities'
                continue
            
            if line_upper.startswith('JOB'):
                continue
            
            if current_section == 'summary':
                if len(line) > 20:
                    summary_lines.append(line)
            elif current_section == 'responsibilities':
                if self._is_bullet_point(line) or len(line) > 10:
                    responsibilities.append(self._clean_bullet(line))
            elif current_section == 'requirements':
                if self._is_bullet_point(line) or len(line) > 10:
                    requirements.append(self._clean_bullet(line))
        
        if summary_lines:
            job.description = ' '.join(summary_lines[:2])
        if responsibilities:
            job.responsibilities = responsibilities[:15]
        if requirements:
            job.requirements = requirements[:15]
            job.skills_required = self._extract_skills(requirements)[:10]

    # ══════════════════════════════════════════════════════════════════════════════
    # NGO JOBS - Custom Parser (Structured content)
    # ══════════════════════════════════════════════════════════════════════════════

    def _update_ngojobs(self, job):
        """NGO Jobs: Structured with company info at top"""
        if not job.job_url:
            raise Exception("No URL")
        
        r = requests.get(job.job_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if r.status_code != 200:
            raise Exception(f"HTTP {r.status_code}")
        
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # LAYER 1: HEADER
        title = soup.find('h1')
        if title:
            job.title = title.get_text(strip=True)[:200]
        
        # LAYER 2 & 3: DESCRIPTION
        desc_selectors = ['div.job-description', 'div.description', 'article', 'div.entry-content']
        for sel in desc_selectors:
            desc = soup.select_one(sel)
            if desc:
                for script in desc.find_all('script'):
                    script.decompose()
                text = desc.get_text(separator='\n', strip=True)
                self._parse_ngojobs_structure(job, text)
                break

    def _parse_ngojobs_structure(self, job, text):
        """NGO Jobs: Company info often at top, then job details"""
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        
        summary_lines = []
        responsibilities = []
        requirements = []
        
        current_section = 'company'  # NGO jobs often start with company info
        
        for line in lines:
            line_upper = line.upper()
            
            if 'ABOUT' in line_upper and 'ORGANIZATION' in line_upper:
                current_section = 'company'
                continue
            elif 'ABOUT' in line_upper and ('ROLE' in line_upper or 'POSITION' in line_upper):
                current_section = 'summary'
                continue
            elif 'REQUIREMENTS' in line_upper or 'QUALIFICATIONS' in line_upper:
                current_section = 'requirements'
                continue
            elif 'RESPONSIBILITIES' in line_upper or 'DUTIES' in line_upper:
                current_section = 'responsibilities'
                continue
            
            if current_section == 'summary':
                if len(line) > 20:
                    summary_lines.append(line)
            elif current_section == 'responsibilities':
                if self._is_bullet_point(line) or len(line) > 10:
                    responsibilities.append(self._clean_bullet(line))
            elif current_section == 'requirements':
                if self._is_bullet_point(line) or len(line) > 10:
                    requirements.append(self._clean_bullet(line))
        
        if summary_lines:
            job.description = ' '.join(summary_lines[:2])
        if responsibilities:
            job.responsibilities = responsibilities[:15]
        if requirements:
            job.requirements = requirements[:15]
            job.skills_required = self._extract_skills(requirements)[:10]

    # ══════════════════════════════════════════════════════════════════════════════
    # SHARED HELPER FUNCTIONS
    # ══════════════════════════════════════════════════════════════════════════════

    def _is_bullet_point(self, line):
        """Check if line is a bullet point"""
        return bool(re.match(r'^[\-•*○▪▫–]\s', line) or re.match(r'^\d+\.\s', line))

    def _clean_bullet(self, line):
        """Remove bullet marker from line"""
        line = re.sub(r'^[\-•*○▪▫–]\s*', '', line)
        line = re.sub(r'^\d+\.\s*', '', line)
        return line.strip()

    def _extract_skills(self, requirements):
        """Extract skills from requirements list"""
        skills = []
        skill_keywords = ['python', 'java', 'javascript', 'react', 'django', 'sql', 'aws', 
                        'excel', 'powerpoint', 'communication', 'leadership', 'management',
                        'analysis', 'marketing', 'sales', 'finance', 'accounting', 'design']
        
        for req in requirements:
            req_lower = req.lower()
            for skill in skill_keywords:
                if skill in req_lower:
                    skills.append(skill.capitalize())
        
        return list(set(skills))  # Remove duplicates