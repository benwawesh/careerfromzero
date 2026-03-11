"""
African Job Board Scrapers - Additional Sources
============================================
Scrapers for more African job boards to increase job count.

Sources:
- Jobberman (Nigeria)
- Career24 (South Africa)
- JobwebKenya
- Corporate Staffing
"""

import re
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _clean(text: str) -> str:
    return re.sub(r'\s+', ' ', text or '').strip()

def _http():
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    })
    return s


# ══════════════════════════════════════════════════════════════════════════════
# JOBBERMAN (Nigeria) - RSS Feed
# ══════════════════════════════════════════════════════════════════════════════

class JobbermanScraper:
    """
    Jobberman Nigeria - Fetch jobs via RSS
    URL: https://www.jobberman.com
    """
    
    RSS_URL = "https://www.jobberman.com/feed/"
    
    def fetch_jobs(self, location='') -> List[Dict]:
        jobs = []
        
        logger.info("="*70)
        logger.info("JOBBERMAN NIGERIA - Starting Job Fetch")
        logger.info("="*70)
        
        try:
            logger.info("Fetching RSS feed...")
            r = _http().get(self.RSS_URL, timeout=20)
            
            if r.status_code != 200:
                logger.warning(f"RSS feed returned status {r.status_code}")
                return []
            
            # Parse RSS using BeautifulSoup
            soup = BeautifulSoup(r.content, 'xml')
            items = soup.find_all('item')
            
            logger.info(f"Found {len(items)} items in RSS feed")
            
            for item in items:
                job = self._parse_rss_item(item)
                if job:
                    jobs.append(job)
            
            logger.info(f"Jobberman: {len(jobs)} jobs fetched")
            
        except Exception as e:
            logger.error(f"Jobberman error: {e}")
        
        return jobs
    
    def _parse_rss_item(self, item) -> Optional[Dict]:
        try:
            title = _clean(item.find('title').get_text()) if item.find('title') else ''
            if not title or len(title) < 5:
                return None
            
            description = _clean(item.find('description').get_text()) if item.find('description') else ''
            link = item.find('link').get_text() if item.find('link') else ''
            
            # Try to extract company from title/description
            company = 'Unknown Company'
            company_match = re.search(r'at\s+([A-Z][^\s]+(?:\s+[A-Z][^\s]+)?)', title)
            if company_match:
                company = company_match.group(1)
            
            # Clean up HTML tags from description
            description = re.sub(r'<[^>]+>', ' ', description)
            description = _clean(description)
            
            # Parse pub date
            pub_date = item.find('pubDate')
            posted_date = None
            if pub_date:
                date_str = pub_date.get_text()
                try:
                    posted_date = datetime.strptime(date_str[:25], '%a, %d %b %Y %H:%M:%S')
                except:
                    pass
            
            # Generate external ID
            external_id = f"jobberman_{hash(title)}"
            
            return {
                'title': title,
                'company': company,
                'description': description[:500],
                'location': 'Nigeria',
                'job_url': link,
                'job_type': 'full_time',
                'source': 'jobberman',
                'external_id': external_id,
                'posted_date': posted_date,
                'is_active': True,
            }
        except Exception as e:
            logger.error(f"Error parsing RSS item: {e}")
            return None


# ══════════════════════════════════════════════════════════════════════════════
# CAREER24 (South Africa) - RSS Feed
# ══════════════════════════════════════════════════════════════════════════════

class Career24Scraper:
    """
    Career24 South Africa - Fetch jobs via RSS
    URL: https://www.career24.com
    """
    
    RSS_URL = "https://www.career24.com/rss"
    
    def fetch_jobs(self) -> List[Dict]:
        jobs = []
        
        logger.info("="*70)
        logger.info("CAREER24 SOUTH AFRICA - Starting Job Fetch")
        logger.info("="*70)
        
        try:
            logger.info("Fetching RSS feed...")
            r = _http().get(self.RSS_URL, timeout=20)
            
            if r.status_code != 200:
                logger.warning(f"RSS feed returned status {r.status_code}")
                return []
            
            # Parse RSS using BeautifulSoup
            soup = BeautifulSoup(r.content, 'xml')
            items = soup.find_all('item')
            
            logger.info(f"Found {len(items)} items in RSS feed")
            
            for item in items:
                job = self._parse_rss_item(item)
                if job:
                    jobs.append(job)
            
            logger.info(f"Career24: {len(jobs)} jobs fetched")
            
        except Exception as e:
            logger.error(f"Career24 error: {e}")
        
        return jobs
    
    def _parse_rss_item(self, item) -> Optional[Dict]:
        try:
            title = _clean(item.find('title').get_text()) if item.find('title') else ''
            if not title or len(title) < 5:
                return None
            
            description = _clean(item.find('description').get_text()) if item.find('description') else ''
            link = item.find('link').get_text() if item.find('link') else ''
            
            # Try to extract company from title/description
            company = 'Unknown Company'
            company_match = re.search(r'at\s+([A-Z][^\s]+(?:\s+[A-Z][^\s]+)?)', title)
            if company_match:
                company = company_match.group(1)
            
            # Clean up HTML tags from description
            description = re.sub(r'<[^>]+>', ' ', description)
            description = _clean(description)
            
            # Parse pub date
            pub_date = item.find('pubDate')
            posted_date = None
            if pub_date:
                date_str = pub_date.get_text()
                try:
                    posted_date = datetime.strptime(date_str[:25], '%a, %d %b %Y %H:%M:%S')
                except:
                    pass
            
            # Generate external ID
            external_id = f"career24_{hash(title)}"
            
            return {
                'title': title,
                'company': company,
                'description': description[:500],
                'location': 'South Africa',
                'job_url': link,
                'job_type': 'full_time',
                'source': 'career24',
                'external_id': external_id,
                'posted_date': posted_date,
                'is_active': True,
            }
        except Exception as e:
            logger.error(f"Error parsing RSS item: {e}")
            return None


# ══════════════════════════════════════════════════════════════════════════════
# MAIN COORDINATOR - African Job Fetcher
# ══════════════════════════════════════════════════════════════════════════════

class AfricanJobFetcher:
    """Fetches jobs from additional African sources"""
    
    def __init__(self):
        self.scrapers = [
            ('Jobberman', JobbermanScraper()),
            ('Career24', Career24Scraper()),
        ]
    
    def fetch_all_jobs(self, location='') -> List[Dict]:
        """Fetch jobs from all African sources"""
        all_jobs = []
        
        for name, scraper in self.scrapers:
            try:
                jobs = scraper.fetch_jobs(location)
                all_jobs.extend(jobs)
                logger.info(f"{name}: {len(jobs)} jobs fetched")
            except Exception as e:
                logger.error(f"{name}: {e}")
        
        logger.info(f"Total African jobs: {len(all_jobs)}")
        return all_jobs
    
    def fetch_from_source(self, source: str, location='') -> List[Dict]:
        """Fetch from specific African source"""
        source_map = {name.lower(): scraper for name, scraper in self.scrapers}
        
        scraper = source_map.get(source.lower())
        if not scraper:
            logger.error(f"Unknown source: {source}")
            return []
        
        return scraper.fetch_jobs(location)
    
    def save_jobs_to_db(self, jobs: List[Dict]) -> Dict:
        """Save jobs to database"""
        from ..models import Job
        created = updated = errors = 0
        
        for job_data in jobs:
            try:
                ext_id = job_data.get('external_id')
                if ext_id:
                    _, was_created = Job.objects.update_or_create(
                        external_id=ext_id, defaults=job_data
                    )
                    if was_created:
                        created += 1
                    else:
                        updated += 1
                else:
                    Job.objects.create(**job_data)
                    created += 1
            except Exception as e:
                logger.error(f"DB save error: {e}")
                errors += 1
        
        logger.info(f"DB: {created} created, {updated} updated, {errors} errors")
        return {'created': created, 'updated': updated, 'errors': errors}


# Singleton instance
african_job_fetcher = AfricanJobFetcher()