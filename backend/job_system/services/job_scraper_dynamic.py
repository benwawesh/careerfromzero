"""
Dynamic Job Scraper - Automatic and Unlimited Fetching
================================================
This module provides dynamic, automatic job fetching that:
- Auto-detects pagination
- Fetches ALL available jobs (no limits)
- Stops when no more jobs exist
- Works with APIs and HTML scrapers

Usage:
    from job_system.services.job_scraper_dynamic import DynamicJobFetcher
    
    fetcher = DynamicJobFetcher()
    
    # Fetch all jobs from all sources
    jobs = fetcher.fetch_all_jobs()
    
    # Fetch from specific source
    jobs = fetcher.fetch_from_source('brightermonday')
    
    # With filters
    jobs = fetcher.fetch_all_jobs(query='developer', location='nairobi')
"""

import os
import re
import logging
from datetime import datetime, date
from typing import List, Dict, Optional, Iterator

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# ─── Shared helpers ───────────────────────────────────────────────────────────

def _clean(text: str) -> str:
    return re.sub(r'\s+', ' ', text or '').strip()

def _strip_html(html: str) -> str:
    return _clean(BeautifulSoup(html or '', 'html.parser').get_text(separator=' '))

def _http():
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/html, */*',
        'Accept-Language': 'en-US,en;q=0.9',
    })
    # Add retry strategy
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[403, 429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s

import time

def _parse_date(val) -> Optional[date]:
    if not val:
        return None
    if isinstance(val, date):
        return val
    for fmt in ('%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%SZ',
                '%a, %d %b %Y %H:%M:%S %Z', '%a, %d %b %Y %H:%M:%S GMT',
                '%Y-%m-%dT%H:%M:%S.%fZ'):
        try:
            return datetime.strptime(str(val)[:30], fmt).date()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(str(val).replace('Z', '+00:00')).date()
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════════
# FREE APIS — Unlimited fetching with pagination
# ══════════════════════════════════════════════════════════════════════════════

class DynamicRemotiveScraper:
    """Remotive - fetches ALL jobs (max 100 per API call)"""
    API = "https://remotive.com/api/remote-jobs"

    def fetch_jobs(self, query='', location='') -> List[Dict]:
        jobs = []
        try:
            params = {'limit': 100}  # Max per request
            if query:
                params['search'] = query
            r = _http().get(self.API, params=params, timeout=15)
            r.raise_for_status()
            for d in r.json().get('jobs', []):
                j = self._parse(d)
                if j:
                    jobs.append(j)
            logger.info(f"Remotive: {len(jobs)} jobs fetched")
        except Exception as e:
            logger.error(f"Remotive: {e}")
        return jobs

    def _parse(self, d) -> Optional[Dict]:
        try:
            tags = [t.lower() for t in (d.get('tags') or [])]
            return {
                'title': d.get('title', ''),
                'company': d.get('company_name', ''),
                'description': _strip_html(d.get('description', '')),
                'location': d.get('candidate_required_location') or 'Remote',
                'job_url': d.get('url', ''),
                'job_type': 'remote',
                'source': 'remotive',
                'external_id': f"remotive_{d.get('id')}",
                'skills_required': tags[:10],
                'company_logo_url': d.get('company_logo', ''),
                'posted_date': _parse_date(d.get('publication_date')),
                'is_active': True,
            }
        except Exception as e:
            logger.error(f"Remotive parse: {e}")
            return None


class DynamicArbeitnowScraper:
    """Arbeitnow - fetches ALL jobs with automatic pagination"""
    API = "https://www.arbeitnow.com/api/job-board-api"

    def fetch_jobs(self, query='', location='') -> List[Dict]:
        jobs = []
        page = 1
        try:
            while True:
                r = _http().get(self.API, params={'page': page}, timeout=15)
                r.raise_for_status()
                data = r.json().get('data', [])
                if not data:
                    logger.info(f"Arbeitnow: no more jobs on page {page}")
                    break
                
                page_jobs = []
                for d in data:
                    if query:
                        hay = f"{d.get('title','')} {d.get('description','')}".lower()
                        if query.lower() not in hay:
                            continue
                    j = self._parse(d)
                    if j:
                        jobs.append(j)
                        page_jobs.append(j)
                
                logger.info(f"Arbeitnow page {page}: {len(page_jobs)} jobs (total: {len(jobs)})")
                page += 1
                
                # Stop if we got less than expected (end of results)
                if len(data) < 20:
                    break
                
                # Safety limit to prevent infinite loops
                if page > 100:
                    logger.warning("Arbeitnow: reached page limit of 100")
                    break
            
            logger.info(f"Arbeitnow: {len(jobs)} total jobs fetched from {page-1} pages")
        except Exception as e:
            logger.error(f"Arbeitnow: {e}")
        return jobs

    def _parse(self, d) -> Optional[Dict]:
        try:
            tags = [t.lower() for t in (d.get('tags') or [])]
            jt_raw = (d.get('job_types') or [''])[0].lower()
            job_type = ('part_time' if 'part' in jt_raw else
                        'contract' if 'contract' in jt_raw else
                        'internship' if 'intern' in jt_raw else
                        'remote' if d.get('remote') else 'full_time')
            return {
                'title': d.get('title', ''),
                'company': d.get('company_name', ''),
                'description': _strip_html(d.get('description', '')),
                'location': d.get('location') or ('Remote' if d.get('remote') else 'Europe'),
                'job_url': d.get('url', ''),
                'job_type': job_type,
                'source': 'arbeitnow',
                'external_id': f"arbeitnow_{d.get('slug', '')}",
                'skills_required': tags[:10],
                'posted_date': (datetime.fromtimestamp(d['created_at']).date()
                                if d.get('created_at') else None),
                'is_active': True,
            }
        except Exception as e:
            logger.error(f"Arbeitnow parse: {e}")
            return None


class DynamicRemoteOKScraper:
    """RemoteOK - fetches ALL jobs"""
    API = "https://remoteok.com/api"

    def fetch_jobs(self, query='', location='') -> List[Dict]:
        jobs = []
        try:
            params = {}
            if query:
                params['tag'] = query.lower().replace(' ', '+')
            r = _http().get(self.API, params=params,
                            headers={'Referer': 'https://remoteok.com/'}, timeout=15)
            r.raise_for_status()
            data = r.json()
            # Skip first item (it's metadata)
            for d in data[1:]:
                if not isinstance(d, dict) or not d.get('position'):
                    continue
                j = self._parse(d)
                if j:
                    jobs.append(j)
            logger.info(f"RemoteOK: {len(jobs)} jobs fetched")
        except Exception as e:
            logger.error(f"RemoteOK: {e}")
        return jobs

    def _parse(self, d) -> Optional[Dict]:
        try:
            tags = [t.lower() for t in (d.get('tags') or [])]
            return {
                'title': d.get('position', ''),
                'company': d.get('company', ''),
                'description': _strip_html(d.get('description', '')),
                'location': d.get('location') or 'Remote',
                'job_url': d.get('url', ''),
                'job_type': 'remote',
                'source': 'remoteok',
                'external_id': f"remoteok_{d.get('id', '')}",
                'skills_required': tags[:10],
                'salary_min': float(d['salary_min']) if d.get('salary_min') else None,
                'salary_max': float(d['salary_max']) if d.get('salary_max') else None,
                'salary_currency': 'USD',
                'company_logo_url': d.get('company_logo', ''),
                'posted_date': _parse_date(d.get('date')),
                'is_active': True,
            }
        except Exception as e:
            logger.error(f"RemoteOK parse: {e}")
            return None


class DynamicJobicyScraper:
    """Jobicy - fetches ALL jobs"""
    API = "https://jobicy.com/api/v2/remote-jobs"

    def fetch_jobs(self, query='', location='') -> List[Dict]:
        jobs = []
        try:
            params = {'count': 100, 'geo': 'worldwide'}  # Max per request
            if query:
                params['tag'] = query
            r = _http().get(self.API, params=params, timeout=15)
            r.raise_for_status()
            for d in r.json().get('jobs', []):
                j = self._parse(d)
                if j:
                    jobs.append(j)
            logger.info(f"Jobicy: {len(jobs)} jobs fetched")
        except Exception as e:
            logger.error(f"Jobicy: {e}")
        return jobs

    def _parse(self, d) -> Optional[Dict]:
        try:
            level = d.get('jobLevel', '').lower()
            exp = ('entry_level' if 'junior' in level else
                   'senior_level' if any(x in level for x in ('senior', 'lead', 'manager')) else
                   'mid_level' if 'mid' in level else None)
            jt = d.get('jobType', '').lower()
            job_type = ('part_time' if 'part' in jt else
                        'contract' if any(x in jt for x in ('contract', 'freelance')) else
                        'full_time')
            tags = [x.strip().lower() for x in (d.get('jobIndustry') or '').split(',') if x.strip()]
            return {
                'title': d.get('jobTitle', ''),
                'company': d.get('companyName', ''),
                'description': _strip_html(d.get('jobDescription') or d.get('jobExcerpt', '')),
                'location': d.get('jobGeo') or 'Remote',
                'job_url': d.get('url', ''),
                'job_type': job_type,
                'source': 'jobicy',
                'external_id': f"jobicy_{d.get('id')}",
                'skills_required': tags[:10],
                'experience_level': exp,
                'posted_date': _parse_date(d.get('pubDate')),
                'is_active': True,
            }
        except Exception as e:
            logger.error(f"Jobicy parse: {e}")
            return None


class DynamicTheMuseScraper:
    """The Muse - fetches ALL jobs with pagination"""
    API = "https://www.themuse.com/api/public/jobs"

    def fetch_jobs(self, query='', location='') -> List[Dict]:
        jobs = []
        page = 0
        try:
            while True:
                params = {'page': page, 'api_key': 'public'}
                if location:
                    params['location'] = location
                r = _http().get(self.API, params=params, timeout=15)
                if r.status_code != 200:
                    logger.info(f"TheMuse: reached end at page {page}")
                    break
                
                data = r.json().get('results', [])
                if not data:
                    logger.info(f"TheMuse: no results on page {page}")
                    break
                
                page_jobs = []
                for d in data:
                    if query:
                        if query.lower() not in d.get('name', '').lower():
                            continue
                    j = self._parse(d)
                    if j:
                        jobs.append(j)
                        page_jobs.append(j)
                
                logger.info(f"TheMuse page {page}: {len(page_jobs)} jobs (total: {len(jobs)})")
                page += 1
                
                # Stop if we got less than expected
                if len(data) < 20:
                    break
                
                # Safety limit
                if page > 100:
                    logger.warning("TheMuse: reached page limit of 100")
                    break
            
            logger.info(f"TheMuse: {len(jobs)} total jobs fetched from {page-1} pages")
        except Exception as e:
            logger.error(f"TheMuse: {e}")
        return jobs

    def _parse(self, d) -> Optional[Dict]:
        try:
            locs = [l['name'] for l in (d.get('locations') or [])]
            levels = [l['name'].lower() for l in (d.get('levels') or [])]
            exp = ('entry_level' if any('entry' in l or 'junior' in l for l in levels) else
                   'senior_level' if any('senior' in l for l in levels) else
                   'mid_level' if any('mid' in l for l in levels) else None)
            url = d.get('refs', {}).get('landing_page', '')
            cats = [c['name'].lower() for c in (d.get('categories') or [])]
            return {
                'title': d.get('name', ''),
                'company': d.get('company', {}).get('name', ''),
                'description': '',
                'location': ', '.join(locs) or 'US',
                'job_url': url,
                'job_type': 'full_time',
                'source': 'themuse',
                'external_id': f"muse_{d.get('id')}",
                'skills_required': cats[:8],
                'experience_level': exp,
                'posted_date': _parse_date(d.get('publication_date')),
                'is_active': True,
            }
        except Exception as e:
            logger.error(f"TheMuse parse: {e}")
            return None


# ══════════════════════════════════════════════════════════════════════════════
# AFRICAN JOB BOARDS — Dynamic scraping with pagination
# ══════════════════════════════════════════════════════════════════════════════

def _html_session(url, params=None):
    s = _http()
    s.headers.update({'Accept': 'text/html,application/xhtml+xml'})
    return s.get(url, params=params or {}, timeout=15)


def _find_cards(soup, selectors):
    for sel in selectors:
        cards = soup.select(sel)
        if len(cards) >= 1:
            return cards
    return []


class DynamicBrighterMondayScraper:
    """BrighterMonday - fetches ALL jobs with automatic pagination"""
    BASE = "https://www.brightermonday.co.ke"

    def fetch_jobs(self, query='', location='') -> List[Dict]:
        jobs = []
        page = 1
        try:
            while True:
                params = {'page': page}
                if query:
                    params['q'] = query
                if location:
                    params['l'] = location
                
                url = f"{self.BASE}/jobs"
                r = _html_session(url, params)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, 'html.parser')
                
                # Extract prerender links from HTML head
                prerender_links = soup.find_all('link', rel='prerender')
                
                if not prerender_links:
                    logger.info(f"BrighterMonday page {page}: no jobs found, stopping")
                    break
                
                page_jobs = []
                for i, link in enumerate(prerender_links):
                    href = link.get('href', '')
                    # Only process /listings/ URLs
                    if '/listings/' in href:
                        j = self._parse_from_url(href, len(jobs) + i)
                        if j:
                            jobs.append(j)
                            page_jobs.append(j)
                
                logger.info(f"BrighterMonday page {page}: {len(page_jobs)} jobs (total: {len(jobs)})")
                
                # Check if there's a next page
                next_link = soup.select_one('a[rel="next"]')
                if not next_link:
                    logger.info(f"BrighterMonday: reached last page ({page})")
                    break
                
                page += 1
            
            logger.info(f"BrighterMonday: {len(jobs)} total jobs fetched from {page-1} pages")
        except Exception as e:
            logger.error(f"BrighterMonday: {e}")
        return jobs

    def _parse_from_url(self, job_url, idx) -> Optional[Dict]:
        """Parse job details from a prerender link URL."""
        try:
            slug = job_url.rstrip('/').split('/')[-1] or str(idx)
            
            # Fetch the job page to get details
            r = _http().get(job_url, timeout=10)
            if r.status_code != 200:
                return {
                    'title': slug.replace('-', ' ').title() if slug else 'Unknown',
                    'company': 'Unknown',
                    'description': '',
                    'location': 'Kenya',
                    'job_url': job_url,
                    'job_type': 'full_time',
                    'source': 'brightermonday',
                    'external_id': f"bm_{slug}",
                    'is_active': True,
                }
            
            soup = BeautifulSoup(r.text, 'html.parser')
            
            title = ''
            title_elem = soup.find('h1') or soup.find(class_=re.compile(r'title', re.I))
            if title_elem:
                title = title_elem.get_text(strip=True)
            
            company = ''
            company_elem = soup.find(class_=re.compile(r'company|employer|org', re.I))
            if company_elem:
                company = company_elem.get_text(strip=True)
            
            location = 'Kenya'
            loc_elem = soup.find(class_=re.compile(r'location|place|region', re.I))
            if loc_elem:
                location = loc_elem.get_text(strip=True)
            
            description = ''
            desc_elem = soup.find(class_=re.compile(r'description|summary|details', re.I))
            if desc_elem:
                description = _strip_html(str(desc_elem))[:2000]
            
            return {
                'title': _clean(title) or slug.replace('-', ' ').title(),
                'company': _clean(company) or 'Unknown',
                'description': _clean(description),
                'location': _clean(location),
                'job_url': job_url,
                'job_type': 'full_time',
                'source': 'brightermonday',
                'external_id': f"bm_{slug}",
                'is_active': True,
            }
        except Exception as e:
            logger.error(f"BrighterMonday parse from URL: {e}")
            return None


class DynamicMyJobMagScraper:
    """MyJobMag - fetches ALL jobs with pagination"""
    BASE = "https://www.myjobmag.co.ke"

    def fetch_jobs(self, query='', location='') -> List[Dict]:
        jobs = []
        page = 1
        try:
            while True:
                params = {'page': page}
                if query:
                    params['q'] = query
                
                r = _html_session(f"{self.BASE}/jobs", params)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, 'html.parser')
                
                cards = _find_cards(soup, [
                    'div[class*="job-list-item"]', 'article[class*="job"]',
                    'li[class*="job"]', 'div[class*="job-item"]',
                    'div[class*="vacancy"]', 'article',
                ])
                
                if not cards:
                    logger.info(f"MyJobMag page {page}: no jobs found, stopping")
                    break
                
                page_jobs = []
                for i, card in enumerate(cards):
                    j = self._parse(card, i)
                    if j:
                        jobs.append(j)
                        page_jobs.append(j)
                
                logger.info(f"MyJobMag page {page}: {len(page_jobs)} jobs (total: {len(jobs)})")
                
                # Check for pagination
                next_link = soup.select_one('a[rel="next"]') or soup.select_one('a.pagination-next')
                if not next_link:
                    logger.info(f"MyJobMag: reached last page ({page})")
                    break
                
                page += 1
                
                # Safety limit
                if page > 100:
                    logger.warning("MyJobMag: reached page limit of 100")
                    break
            
            logger.info(f"MyJobMag: {len(jobs)} total jobs fetched from {page-1} pages")
        except Exception as e:
            logger.error(f"MyJobMag: {e}")
        return jobs

    def _parse(self, card, idx) -> Optional[Dict]:
        try:
            title_el = card.select_one('h2,h3,[class*="title"],[class*="job-title"]')
            title = title_el.get_text(strip=True) if title_el else ''
            company_el = card.select_one('[class*="company"],[class*="employer"],[class*="org"]')
            company = company_el.get_text(strip=True) if company_el else ''
            loc_el = card.select_one('[class*="location"],[class*="city"]')
            location = loc_el.get_text(strip=True) if loc_el else 'Kenya'
            link = card.select_one('a[href]')
            href = link['href'] if link else ''
            job_url = href if href.startswith('http') else self.BASE + href if href else ''
            if not title:
                return None
            return {
                'title': _clean(title), 'company': _clean(company) or 'Unknown',
                'description': '', 'location': _clean(location),
                'job_url': job_url, 'job_type': 'full_time', 'source': 'myjobmag',
                'external_id': f"mjm_{(job_url.rstrip('/').split('/')[-1]) or idx}",
                'is_active': True,
            }
        except Exception as e:
            logger.error(f"MyJobMag parse: {e}")
            return None


# ══════════════════════════════════════════════════════════════════════════════
# MAIN COORDINATOR - Dynamic Job Fetcher
# ══════════════════════════════════════════════════════════════════════════════

class DynamicJobFetcher:
    """
    Dynamic job fetcher that automatically detects pagination
    and fetches ALL available jobs from all sources.
    
    NO HARDCODED LIMITS - Fetches everything until exhausted!
    """
    
    def __init__(self):
        self._free_apis = [
            ('Remotive', DynamicRemotiveScraper()),
            ('Arbeitnow', DynamicArbeitnowScraper()),
            ('Jobicy', DynamicJobicyScraper()),
            ('RemoteOK', DynamicRemoteOKScraper()),
            ('TheMuse', DynamicTheMuseScraper()),
        ]
        
        self._african = [
            ('BrighterMonday', DynamicBrighterMondayScraper()),
            ('MyJobMag', DynamicMyJobMagScraper()),
        ]
    
    def fetch_all_jobs(self, query='', location='') -> List[Dict]:
        """Fetch ALL jobs from all sources (unlimited)"""
        all_jobs = []
        
        # 1. Free APIs
        for name, scraper in self._free_apis:
            try:
                jobs = scraper.fetch_jobs(query, location)
                all_jobs.extend(jobs)
                logger.info(f"{name}: {len(jobs)} fetched")
            except Exception as e:
                logger.error(f"{name}: {e}")
        
        # 2. African boards
        for name, scraper in self._african:
            try:
                jobs = scraper.fetch_jobs(query, location)
                all_jobs.extend(jobs)
                logger.info(f"{name}: {len(jobs)} fetched")
            except Exception as e:
                logger.error(f"{name}: {e}")
        
        logger.info(f"Total fetched: {len(all_jobs)}")
        return all_jobs
    
    def fetch_from_source(self, source: str, query='', location='') -> List[Dict]:
        """Fetch ALL jobs from a specific source"""
        all_scrapers = {**dict(self._free_apis), **dict(self._african)}
        
        # Case-insensitive lookup
        source_lower = source.lower()
        scraper = None
        for name, scraper_obj in all_scrapers.items():
            if name.lower() == source_lower:
                scraper = scraper_obj
                break
        
        if not scraper:
            logger.error(f"Unknown source: {source}")
            available = ', '.join([name for name in all_scrapers.keys()])
            logger.info(f"Available sources: {available}")
            return []
        
        return scraper.fetch_jobs(query, location)
    
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
                logger.error(f"DB save '{job_data.get('title','?')}': {e}")
                errors += 1
        
        logger.info(f"DB: {created} created, {updated} updated, {errors} errors")
        return {'created': created, 'updated': updated, 'errors': errors}


# Singleton instance
dynamic_job_fetcher = DynamicJobFetcher()
