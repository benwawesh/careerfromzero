"""
Job Scraper Service
===================
Pulls jobs from free APIs, python-jobspy (LinkedIn/Indeed/Glassdoor/ZipRecruiter),
Adzuna API (multi-country), and African job board scrapers.

Free APIs — no key:
  Remotive    https://remotive.com/api/remote-jobs
  Arbeitnow   https://www.arbeitnow.com/api/job-board-api
  Jobicy      https://jobicy.com/api/v2/remote-jobs
  RemoteOK    https://remoteok.com/api
  The Muse    https://www.themuse.com/api/public/jobs

Scraped via python-jobspy (no key — handles anti-bot):
  LinkedIn · Indeed · Glassdoor · ZipRecruiter
  Supports countries: US, UK, Canada, Kenya, Nigeria, South Africa,
                      Germany, France, Australia, India, UAE …

Adzuna API (free 1000 calls/day — add ADZUNA_APP_ID + ADZUNA_APP_KEY to .env):
  Countries: us, ca, gb, de, fr, au, za, ng, in, sg …

African board scrapers (HTML):
  BrighterMonday Kenya · Fuzu · KenyaJob · MyJobMag Kenya
"""

import os
import re
import logging
from datetime import datetime, date
from typing import List, Dict, Optional

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
    return s

def _parse_date(val) -> Optional[date]:
    if not val:
        return None
    if isinstance(val, date):
        return val
    for fmt in ('%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%SZ',
                '%a, %d %b %Y %H:%M:%S %Z', '%a, %d %b %Y %H:%M:%S GMT'):
        try:
            return datetime.strptime(str(val)[:25], fmt).date()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(str(val).replace('Z', '+00:00')).date()
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════════
# FREE APIS — no registration needed
# ══════════════════════════════════════════════════════════════════════════════

class RemotiveScraper:
    """Remotive free remote-jobs API."""
    API = "https://remotive.com/api/remote-jobs"

    def fetch_jobs(self, query='', location='', limit=500) -> List[Dict]:
        jobs = []
        try:
            params = {'limit': 300}  # API max
            if query:
                params['search'] = query
            r = _http().get(self.API, params=params, timeout=15)
            r.raise_for_status()
            for d in r.json().get('jobs', []):
                j = self._parse(d)
                if j:
                    jobs.append(j)
            logger.info(f"Remotive: {len(jobs)}")
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


class ArbeitnowScraper:
    """Arbeitnow free API — EU & remote tech jobs."""
    API = "https://www.arbeitnow.com/api/job-board-api"

    def fetch_jobs(self, query='', location='', limit=5000) -> List[Dict]:
        jobs, page = [], 1
        try:
            while True:
                r = _http().get(self.API, params={'page': page}, timeout=20)
                r.raise_for_status()
                data = r.json().get('data', [])
                if not data:
                    break
                for d in data:
                    if query:
                        hay = f"{d.get('title','')} {d.get('description','')}".lower()
                        if query.lower() not in hay:
                            continue
                    j = self._parse(d)
                    if j:
                        jobs.append(j)
                page += 1
            logger.info(f"Arbeitnow: {len(jobs)} across {page-1} pages")
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


class JobicyScraper:
    """Jobicy remote jobs API."""
    API = "https://jobicy.com/api/v2/remote-jobs"

    def fetch_jobs(self, query='', location='', limit=500) -> List[Dict]:
        jobs = []
        try:
            params = {'count': 50, 'geo': 'worldwide'}  # 50 is API max per call
            if query:
                params['tag'] = query
            r = _http().get(self.API, params=params, timeout=15)
            r.raise_for_status()
            for d in r.json().get('jobs', []):
                j = self._parse(d)
                if j:
                    jobs.append(j)
            logger.info(f"Jobicy: {len(jobs)}")
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


class RemoteOKScraper:
    """RemoteOK free API."""
    API = "https://remoteok.com/api"

    def fetch_jobs(self, query='', location='', limit=500) -> List[Dict]:
        jobs = []
        try:
            params = {}
            if query:
                params['tag'] = query.lower().replace(' ', '+')
            r = _http().get(self.API, params=params,
                            headers={'Referer': 'https://remoteok.com/'}, timeout=15)
            r.raise_for_status()
            for d in r.json()[1:]:  # take all jobs
                if not isinstance(d, dict) or not d.get('position'):
                    continue
                j = self._parse(d)
                if j:
                    jobs.append(j)
            logger.info(f"RemoteOK: {len(jobs)}")
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


class TheMuseScraper:
    """The Muse free API — no key required. US-heavy but has global listings."""
    API = "https://www.themuse.com/api/public/jobs"

    def fetch_jobs(self, query='', location='', limit=5000) -> List[Dict]:
        jobs = []
        try:
            for page in range(500):  # They have ~500+ pages of jobs
                params = {'page': page, 'api_key': 'public'}
                if location:
                    params['location'] = location
                r = _http().get(self.API, params=params, timeout=15)
                if r.status_code != 200:
                    break
                results = r.json().get('results', [])
                if not results:
                    break
                for d in results:
                    if query and query.lower() not in d.get('name', '').lower():
                        continue
                    j = self._parse(d)
                    if j:
                        jobs.append(j)
                if len(jobs) >= limit:
                    break
            logger.info(f"The Muse: {len(jobs)} across {page+1} pages")
        except Exception as e:
            logger.error(f"The Muse: {e}")
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
                'description': '',  # The Muse doesn't include description in list endpoint
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
            logger.error(f"The Muse parse: {e}")
            return None


# ══════════════════════════════════════════════════════════════════════════════
# INDEED RSS — free, no key, multi-country
# ══════════════════════════════════════════════════════════════════════════════

class IndeedRSSScraper:
    """
    Scrapes Indeed RSS feeds — completely free, no API key.
    Runs multiple job categories × multiple countries for broad coverage.
    """
    # Indeed subdomains per country
    COUNTRY_DOMAINS = {
        'Kenya':        'ke.indeed.com',
        'USA':          'www.indeed.com',
        'UK':           'uk.indeed.com',
        'Canada':       'ca.indeed.com',
        'Australia':    'au.indeed.com',
        'South Africa': 'za.indeed.com',
        'Nigeria':      'ng.indeed.com',
        'Germany':      'de.indeed.com',
        'France':       'fr.indeed.com',
        'India':        'www.indeed.co.in',
        'UAE':          'www.indeed.com',
        'Singapore':    'sg.indeed.com',
    }

    # Job categories to search per country for maximum breadth
    DEFAULT_QUERIES = [
        'software developer', 'data analyst', 'project manager', 'accountant',
        'sales', 'marketing', 'nurse', 'teacher', 'engineer', 'customer service',
        'finance', 'human resources', 'operations', 'business analyst', 'designer',
    ]

    def fetch_jobs(self, query='', location='', limit=5000, **kwargs) -> List[Dict]:
        from xml.etree import ElementTree
        import time as _time

        queries = [query] if query else self.DEFAULT_QUERIES
        countries = list(self.COUNTRY_DOMAINS.keys())

        jobs, seen = [], set()
        for country, domain in self.COUNTRY_DOMAINS.items():
            for q in queries:
                url = f"https://{domain}/rss"
                params = {'q': q, 'sort': 'date', 'limit': 20}
                if location:
                    params['l'] = location
                try:
                    r = _http().get(url, params=params, timeout=10)
                    if not r or r.status_code != 200:
                        continue
                    root = ElementTree.fromstring(r.content)
                    items = root.findall('.//item')
                    for item in items:
                        def tag(name):
                            el = item.find(name)
                            return el.text.strip() if el is not None and el.text else ''
                        title = tag('title')
                        link  = tag('link') or tag('guid')
                        company = tag('source')
                        desc  = BeautifulSoup(tag('description') or '', 'html.parser').get_text(' ')
                        pub   = tag('pubDate')
                        loc   = tag('georss:point') or country
                        ext_id = f"indeedrss_{domain}_{link.rstrip('/').split('/')[-1][:80]}"
                        if ext_id in seen:
                            continue
                        seen.add(ext_id)
                        j = {
                            'title': _clean(title)[:200],
                            'company': _clean(company)[:200],
                            'description': _clean(desc)[:3000],
                            'location': _clean(loc)[:200] or country,
                            'job_url': link,
                            'job_type': 'full_time',
                            'source': 'indeedrss',
                            'external_id': ext_id[:195],
                            'posted_date': _parse_date(pub[:25] if pub else None),
                            'is_active': True,
                        }
                        if title and len(title) > 3:
                            jobs.append(j)
                    _time.sleep(0.3)
                except Exception as e:
                    logger.debug(f"Indeed RSS {country}/{q}: {e}")
                if len(jobs) >= limit:
                    break
            if len(jobs) >= limit:
                break

        logger.info(f"Indeed RSS: {len(jobs)} jobs")
        return jobs


# ══════════════════════════════════════════════════════════════════════════════
# WE WORK REMOTELY — RSS feed (hundreds of remote jobs, no key)
# ══════════════════════════════════════════════════════════════════════════════

class WeWorkRemotelyScraper:
    """
    We Work Remotely publishes full RSS feeds per category — no key needed.
    https://weworkremotely.com/remote-jobs.rss
    """
    FEEDS = [
        ("https://weworkremotely.com/remote-jobs.rss",             "weworkremotely"),
        ("https://weworkremotely.com/categories/remote-programming-jobs.rss", "weworkremotely"),
        ("https://weworkremotely.com/categories/remote-design-jobs.rss",      "weworkremotely"),
        ("https://weworkremotely.com/categories/remote-marketing-jobs.rss",   "weworkremotely"),
    ]

    def fetch_jobs(self, query='', location='', limit=2000, **kwargs) -> List[Dict]:
        from xml.etree import ElementTree
        jobs, seen = [], set()
        for feed_url, source in self.FEEDS:
            try:
                r = _http().get(feed_url, timeout=15)
                if not r or r.status_code != 200:
                    continue
                root = ElementTree.fromstring(r.content)
                for item in root.findall('.//item'):
                    def tag(name):
                        el = item.find(name)
                        return el.text.strip() if el is not None and el.text else ''
                    title_raw = tag('title')
                    # WWR format: "Company: Job Title at Company"
                    title = title_raw.split(': ', 1)[-1] if ': ' in title_raw else title_raw
                    link  = tag('link') or tag('guid')
                    desc  = BeautifulSoup(tag('description') or '', 'html.parser').get_text(' ')
                    pub   = tag('pubDate')
                    company = title_raw.split(': ')[0] if ': ' in title_raw else ''
                    ext_id = f"wwr_{link.rstrip('/').split('/')[-1][:80]}"
                    if ext_id in seen or not title or len(title) < 3:
                        continue
                    seen.add(ext_id)
                    if query and query.lower() not in title.lower() and query.lower() not in desc.lower():
                        continue
                    jobs.append({
                        'title': _clean(title)[:200],
                        'company': _clean(company)[:200],
                        'description': _clean(desc)[:3000],
                        'location': 'Remote',
                        'job_url': link,
                        'job_type': 'remote',
                        'source': 'weworkremotely',
                        'external_id': ext_id[:195],
                        'posted_date': _parse_date(pub[:25] if pub else None),
                        'is_active': True,
                    })
            except Exception as e:
                logger.error(f"WWR {feed_url}: {e}")
        logger.info(f"We Work Remotely: {len(jobs)}")
        return jobs


# ══════════════════════════════════════════════════════════════════════════════
# PYTHON-JOBSPY — LinkedIn, Indeed, Glassdoor, ZipRecruiter
# ══════════════════════════════════════════════════════════════════════════════

# Maps human-readable country names to Indeed country codes
INDEED_COUNTRIES = {
    'USA':          'USA',
    'UK':           'UK',
    'Canada':       'Canada',
    'Australia':    'Australia',
    'Germany':      'Germany',
    'France':       'France',
    'India':        'India',
    'South Africa': 'South Africa',
    'Nigeria':      'Nigeria',
    # Kenya not supported by Indeed via JobSpy — use Kenyan board scrapers instead
    # 'Kenya': 'Kenya',
    'UAE':          'UAE',
    'Singapore':    'Singapore',
    'Netherlands':  'Netherlands',
    'Ireland':      'Ireland',
    'New Zealand':  'New Zealand',
}


class JobSpyScraper:
    """
    Scrapes LinkedIn, Indeed, Glassdoor, ZipRecruiter via python-jobspy.
    No API key needed — uses tls-client to bypass anti-bot.

    Configuration via .env:
      JOBSPY_SITES=linkedin,indeed,glassdoor,zip_recruiter
      JOBSPY_COUNTRIES=USA,UK,Canada,Kenya,South Africa
      JOBSPY_HOURS_OLD=168   (how many hours back to look, default 168 = 1 week)
    """

    DEFAULT_SITES = ['linkedin', 'indeed', 'glassdoor', 'zip_recruiter']
    DEFAULT_COUNTRIES = ['USA', 'UK', 'Canada', 'Kenya', 'South Africa']

    def __init__(self):
        sites_env = os.environ.get('JOBSPY_SITES', '')
        countries_env = os.environ.get('JOBSPY_COUNTRIES', '')
        self.sites = [s.strip() for s in sites_env.split(',') if s.strip()] or self.DEFAULT_SITES
        self.countries = [c.strip() for c in countries_env.split(',') if c.strip()] or self.DEFAULT_COUNTRIES
        self.hours_old = int(os.environ.get('JOBSPY_HOURS_OLD', 168))

    # Default search terms to run when no query given — covers broad job market
    DEFAULT_QUERIES = [
        'software developer', 'data analyst', 'project manager',
        'marketing', 'finance', 'sales', 'customer service',
        'nurse', 'teacher', 'engineer',
    ]

    def fetch_jobs(self, query='', location='', limit=100) -> List[Dict]:
        """
        Runs jobspy for each country (and optionally multiple search terms) to get broad coverage.
        Set JOBSPY_RESULTS env var to override per-country limit.
        """
        try:
            from jobspy import scrape_jobs
        except ImportError:
            logger.error("python-jobspy not installed. Run: pip install python-jobspy")
            return []

        results_per_call = int(os.environ.get('JOBSPY_RESULTS', limit))
        all_jobs = []
        seen_ids = set()

        # Use multiple queries when no specific query given for breadth
        queries = [query] if query else self.DEFAULT_QUERIES

        # Countries where Glassdoor works + best city-level location for it
        GLASSDOOR_LOCATIONS = {
            'USA':          'New York, NY',
            'UK':           'London, United Kingdom',
            'Canada':       'Toronto, Ontario',
            'Germany':      'Berlin, Germany',
            'France':       'Paris, France',
            'Australia':    'Sydney, Australia',
            'India':        'Mumbai, India',
            'Ireland':      'Dublin, Ireland',
            'Netherlands':  'Amsterdam, Netherlands',
            'Singapore':    'Singapore',
        }

        for search_term in queries:
            for country in self.countries:
                indeed_country = INDEED_COUNTRIES.get(country, country)
                loc = location or country

                sites_for_country = self.sites[:]
                # ZipRecruiter is US/CA only
                if country not in ('USA', 'Canada'):
                    sites_for_country = [s for s in sites_for_country if s != 'zip_recruiter']
                # Glassdoor only works well for certain countries with city-level location
                if country not in GLASSDOOR_LOCATIONS:
                    sites_for_country = [s for s in sites_for_country if s != 'glassdoor']

                # Use a proper city location for Glassdoor when no location specified
                glassdoor_loc = location or GLASSDOOR_LOCATIONS.get(country, loc)

                try:
                    logger.info(f"JobSpy: '{search_term}' | {country} | sites={sites_for_country}")
                    df = scrape_jobs(
                        site_name=sites_for_country,
                        search_term=search_term,
                        location=glassdoor_loc,
                        results_wanted=results_per_call,
                        hours_old=self.hours_old,
                        country_indeed=indeed_country,
                        linkedin_fetch_description=False,
                        verbose=0,
                    )
                    if df is None or df.empty:
                        continue

                    for _, row in df.iterrows():
                        uid = f"jobspy_{row.get('site', '')}_{row.get('id', row.get('job_url', ''))}"
                        if uid in seen_ids:
                            continue
                        seen_ids.add(uid)
                        j = self._parse_row(row, country)
                        if j:
                            all_jobs.append(j)

                except Exception as e:
                    logger.error(f"JobSpy {search_term}/{country}: {e}")

        logger.info(f"JobSpy total: {len(all_jobs)}")
        return all_jobs

    def _parse_row(self, row, country: str) -> Optional[Dict]:
        try:
            site = str(row.get('site') or 'scraped')
            source_map = {
                'linkedin': 'linkedin',
                'indeed': 'indeed',
                'glassdoor': 'glassdoor',
                'zip_recruiter': 'ziprecruiter',
            }
            source = source_map.get(site, 'scraped')

            import math
            salary_min = salary_max = None
            try:
                v = float(row['min_amount'])
                if not math.isnan(v):
                    salary_min = v
            except Exception:
                pass
            try:
                v = float(row['max_amount'])
                if not math.isnan(v):
                    salary_max = v
            except Exception:
                pass

            jt_raw = str(row.get('job_type') or '').lower()
            job_type = ('part_time' if 'part' in jt_raw else
                        'contract' if 'contract' in jt_raw else
                        'internship' if 'intern' in jt_raw else
                        'remote' if row.get('is_remote') else
                        'full_time' if 'full' in jt_raw else None)

            title = str(row.get('title') or '')
            company = str(row.get('company') or '')
            location = str(row.get('location') or country)
            job_url = str(row.get('job_url') or row.get('job_url_direct') or '')
            # JobSpy returns pandas NaN as 'nan' string when description missing
            raw_desc = row.get('description')
            description = '' if (raw_desc is None or str(raw_desc).lower() == 'nan') else str(raw_desc)
            posted = _parse_date(row.get('date_posted'))

            ext_id = f"jobspy_{site}_{str(row.get('id') or job_url)}"[:95]

            if not title:
                return None

            return {
                'title': _clean(title),
                'company': _clean(company),
                'description': _clean(description)[:5000],
                'location': _clean(location),
                'job_url': job_url,
                'job_type': job_type,
                'source': source,
                'external_id': ext_id,
                'salary_min': salary_min,
                'salary_max': salary_max,
                'salary_currency': str(row.get('currency') or 'USD'),
                'posted_date': posted,
                'is_active': True,
            }
        except Exception as e:
            logger.error(f"JobSpy row parse: {e}")
            return None


# ══════════════════════════════════════════════════════════════════════════════
# ADZUNA — free 1000 calls/day, multi-country
# ══════════════════════════════════════════════════════════════════════════════

# Add ADZUNA_APP_ID + ADZUNA_APP_KEY to .env to enable
# Supported country codes: us, ca, gb, de, fr, au, nz, in, sg, za, ng, br, it, ru, pl, at, be, nl
ADZUNA_COUNTRIES = ['gb', 'us', 'ca', 'de', 'fr', 'au', 'za', 'ng', 'in']


class AdzunaScraper:
    """
    Adzuna multi-country API.
    Set ADZUNA_COUNTRIES in .env to customise (default: gb,us,ca,de,fr,au,za,ng,in)
    """
    BASE = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"

    def __init__(self, app_id: str, app_key: str):
        self.app_id = app_id
        self.app_key = app_key
        env_countries = os.environ.get('ADZUNA_COUNTRIES', '')
        self.countries = ([c.strip() for c in env_countries.split(',') if c.strip()]
                          or ADZUNA_COUNTRIES)

    def fetch_jobs(self, query='', location='', limit=20) -> List[Dict]:
        all_jobs = []
        for country in self.countries:
            jobs = self._fetch_country(country, query, location, limit)
            all_jobs.extend(jobs)
        logger.info(f"Adzuna total ({len(self.countries)} countries): {len(all_jobs)}")
        return all_jobs

    def _fetch_country(self, country: str, query: str, location: str, limit: int) -> List[Dict]:
        jobs = []
        try:
            url = self.BASE.format(country=country)
            params = {
                'app_id': self.app_id,
                'app_key': self.app_key,
                'results_per_page': min(limit, 50),
                'content-type': 'application/json',
            }
            if query:
                params['what'] = query
            if location:
                params['where'] = location
            r = _http().get(url, params=params, timeout=15)
            r.raise_for_status()
            for d in r.json().get('results', [])[:limit]:
                j = self._parse(d, country)
                if j:
                    jobs.append(j)
            logger.info(f"Adzuna/{country}: {len(jobs)}")
        except Exception as e:
            logger.error(f"Adzuna/{country}: {e}")
        return jobs

    def _parse(self, d, country: str) -> Optional[Dict]:
        try:
            contract = d.get('contract_time', '')
            job_type = {'full_time': 'full_time', 'part_time': 'part_time',
                        'contract': 'contract'}.get(contract)
            return {
                'title': d.get('title', ''),
                'company': d.get('company', {}).get('display_name', ''),
                'description': _clean(d.get('description', '')),
                'location': d.get('location', {}).get('display_name', ''),
                'job_url': d.get('redirect_url', ''),
                'job_type': job_type,
                'source': 'adzuna',
                'external_id': f"adzuna_{country}_{d.get('id')}",
                'salary_min': float(d['salary_min']) if d.get('salary_min') else None,
                'salary_max': float(d['salary_max']) if d.get('salary_max') else None,
                'salary_currency': 'USD',
                'posted_date': _parse_date(d.get('created')),
                'is_active': True,
            }
        except Exception as e:
            logger.error(f"Adzuna parse: {e}")
            return None


# ══════════════════════════════════════════════════════════════════════════════
# AFRICAN JOB BOARDS — HTML scraping
# ══════════════════════════════════════════════════════════════════════════════

def _html_session(url, params=None):
    s = _http()
    s.headers.update({'Accept': 'text/html,application/xhtml+xml'})
    return s.get(url, params=params or {}, timeout=15)


def _find_cards(soup, selectors):
    for sel in selectors:
        cards = soup.select(sel)
        if len(cards) >= 3:
            return cards
    return []


class BrighterMondayScraper:
    """BrighterMonday Kenya — https://www.brightermonday.co.ke/jobs
    
    Uses prerender links in HTML head to find job listings.
    Jobs are at /listings/[slug] URLs.
    Fetches ALL available jobs with pagination.
    """
    BASE = "https://www.brightermonday.co.ke"

    def fetch_jobs(self, query='', location='', limit=None) -> List[Dict]:
        """Fetch ALL jobs from BrighterMonday. Set limit=None for unlimited."""
        jobs = []
        page = 1
        
        try:
            while True:
                params = {'page': page}
                if query:
                    params['q'] = query
                if location:
                    params['l'] = location
                
                # Fetch the jobs page
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
                            if limit is not None and len(jobs) >= limit:
                                break
                
                logger.info(f"BrighterMonday page {page}: {len(page_jobs)} jobs (total: {len(jobs)})")
                
                # Check if there's a next page
                next_link = soup.select_one('a[rel="next"]')
                if not next_link:
                    logger.info(f"BrighterMonday: reached last page")
                    break
                
                page += 1
            
            logger.info(f"BrighterMonday total: {len(jobs)} jobs from {page} pages")
        except Exception as e:
            logger.error(f"BrighterMonday: {e}")
        return jobs

    def _parse_from_url(self, job_url, idx) -> Optional[Dict]:
        """Parse job details from a prerender link URL."""
        try:
            # Extract slug from URL
            slug = job_url.rstrip('/').split('/')[-1] or str(idx)
            
            # Fetch the job page to get details
            r = _http().get(job_url, timeout=10)
            if r.status_code != 200:
                # If we can't fetch details, at least return basic info from URL
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
            
            # Extract title
            title = ''
            title_elem = soup.find('h1') or soup.find(class_=re.compile(r'title', re.I))
            if title_elem:
                title = title_elem.get_text(strip=True)
            
            # Extract company
            company = ''
            company_elem = soup.find(class_=re.compile(r'company|employer|org', re.I))
            if company_elem:
                company = company_elem.get_text(strip=True)
            
            # Extract location
            location = 'Kenya'
            loc_elem = soup.find(class_=re.compile(r'location|place|region', re.I))
            if loc_elem:
                location = loc_elem.get_text(strip=True)
            
            # Extract description — try specific job-body containers first
            # Avoid generic matches that include page header/share buttons
            description = ''
            for sel in [
                '[class*="job-description"]', '[class*="job-details__body"]',
                '[class*="description-body"]', '[class*="listing-description"]',
                '[class*="job-content"]', 'article .content', '[itemprop="description"]',
                '[class*="summary"]',
            ]:
                desc_elem = soup.select_one(sel)
                if desc_elem:
                    text = _strip_html(str(desc_elem))
                    # Reject if it looks like metadata (short, or has social share keywords)
                    if len(text) > 100 and not any(
                        kw in text for kw in ('Share on WhatsApp', 'Share on LinkedIn', 'Share link')
                    ):
                        description = text[:3000]
                        break
            
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


class FuzuScraper:
    """Fuzu — tries JSON API first then HTML scraping."""
    BASE = "https://www.fuzu.com"

    def fetch_jobs(self, query='', location='', limit=20) -> List[Dict]:
        jobs = self._try_api(query, location, limit)
        if not jobs:
            jobs = self._try_scrape(query, limit)
        logger.info(f"Fuzu: {len(jobs)}")
        return jobs

    def _try_api(self, query, location, limit) -> List[Dict]:
        try:
            params = {'per_page': limit, 'country': 'kenya'}
            if query:
                params['q'] = query
            r = _http().get(f"{self.BASE}/api/v1/jobs", params=params, timeout=10)
            if r.status_code != 200:
                return []
            items = r.json().get('jobs') or r.json().get('data') or []
            return [j for j in (self._parse_api(d) for d in items[:limit]) if j]
        except Exception:
            return []

    def _parse_api(self, d) -> Optional[Dict]:
        try:
            return {
                'title': d.get('title') or d.get('name', ''),
                'company': (d.get('company') or
                            (d.get('organization') or {}).get('name', '')),
                'description': _strip_html(d.get('description', '')),
                'location': d.get('location') or d.get('city', '') or 'Kenya',
                'job_url': d.get('url') or f"{self.BASE}/jobs/{d.get('id','')}",
                'job_type': 'full_time', 'source': 'fuzu',
                'external_id': f"fuzu_{d.get('id', '')}",
                'is_active': True,
            }
        except Exception:
            return None

    def _try_scrape(self, query, limit) -> List[Dict]:
        jobs = []
        try:
            params = {'q': query} if query else {}
            r = _html_session(f"{self.BASE}/kenya/jobs", params)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, 'html.parser')
            cards = _find_cards(soup, [
                'a[href*="/jobs/"]', 'div[class*="job-card"]',
                'div[class*="job-list"]', 'article', 'li[class*="job"]',
            ])
            for i, card in enumerate(cards[:limit]):
                j = self._parse_card(card, i)
                if j:
                    jobs.append(j)
        except Exception as e:
            logger.error(f"Fuzu scrape: {e}")
        return jobs

    def _parse_card(self, card, idx) -> Optional[Dict]:
        try:
            title_el = card.select_one('h2,h3,h4,[class*="title"]')
            title = title_el.get_text(strip=True) if title_el else ''
            company_el = card.select_one('[class*="company"],[class*="employer"]')
            company = company_el.get_text(strip=True) if company_el else ''
            href = card.get('href') or (card.select_one('a[href]') or {}).get('href', '')
            job_url = href if href.startswith('http') else self.BASE + href if href else ''
            if not title:
                return None
            return {
                'title': _clean(title), 'company': _clean(company) or 'Unknown',
                'description': '', 'location': 'Kenya', 'job_url': job_url,
                'job_type': 'full_time', 'source': 'fuzu',
                'external_id': f"fuzu_{(job_url.rstrip('/').split('/')[-1]) or idx}",
                'is_active': True,
            }
        except Exception:
            return None


class KenyaJobScraper:
    """KenyaJob — https://www.kenyajob.com"""
    BASE = "https://www.kenyajob.com"

    def fetch_jobs(self, query='', location='', limit=20) -> List[Dict]:
        jobs = []
        try:
            params = {}
            if query:
                params['key'] = query
            # Try multiple URL patterns — site structure changes occasionally
            for path in ['/jobs', '/jobs-in-kenya', '/job-listings', '/jobs-kenya', '']:
                r = _html_session(f"{self.BASE}{path}", params)
                if r.status_code == 200:
                    break
            if r.status_code != 200:
                logger.warning(f"KenyaJob: all URLs returned {r.status_code}")
                return []
            r.raise_for_status()
            soup = BeautifulSoup(r.text, 'html.parser')
            cards = _find_cards(soup, [
                'div[class*="job-wrap"]', 'div[class*="views-row"]',
                'article[class*="job"]', 'div[class*="job-item"]',
                'table.views-table tr', 'li[class*="job"]', 'article',
            ])
            for i, card in enumerate(cards[:limit]):
                j = self._parse(card, i)
                if j:
                    jobs.append(j)
            logger.info(f"KenyaJob: {len(jobs)}")
        except Exception as e:
            logger.error(f"KenyaJob: {e}")
        return jobs

    def _parse(self, card, idx) -> Optional[Dict]:
        try:
            title_el = card.select_one(
                'h2,h3,h4,[class*="title"],[class*="job-title"],span.field-content a'
            )
            title = title_el.get_text(strip=True) if title_el else ''
            company_el = card.select_one('[class*="company"],[class*="employer"],[class*="organisation"]')
            company = company_el.get_text(strip=True) if company_el else ''
            loc_el = card.select_one('[class*="location"],[class*="place"]')
            location = loc_el.get_text(strip=True) if loc_el else 'Kenya'
            link = card.select_one('a[href]')
            href = link['href'] if link else ''
            job_url = href if href.startswith('http') else self.BASE + href if href else ''
            if not title:
                return None
            return {
                'title': _clean(title), 'company': _clean(company) or 'Unknown',
                'description': '', 'location': _clean(location),
                'job_url': job_url, 'job_type': 'full_time', 'source': 'kenyajob',
                'external_id': f"kj_{(job_url.rstrip('/').split('/')[-1]) or idx}",
                'is_active': True,
            }
        except Exception as e:
            logger.error(f"KenyaJob parse: {e}")
            return None


class MyJobMagScraper:
    """MyJobMag Kenya — https://www.myjobmag.co.ke/jobs"""
    BASE = "https://www.myjobmag.co.ke"

    def fetch_jobs(self, query='', location='', limit=20) -> List[Dict]:
        jobs = []
        try:
            params = {}
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
            for i, card in enumerate(cards[:limit]):
                j = self._parse(card, i)
                if j:
                    jobs.append(j)
            logger.info(f"MyJobMag: {len(jobs)}")
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
# MAIN COORDINATOR
# ══════════════════════════════════════════════════════════════════════════════

class JobFetcher:
    """
    Coordinates all sources.
    Usage:
        fetcher = JobFetcher()
        jobs = fetcher.fetch_all_jobs(query='developer', location='Nairobi')
        fetcher.save_jobs_to_db(jobs)
    """

    def __init__(self):
        self._free_apis = [
            ('Remotive',         RemotiveScraper()),
            ('Arbeitnow',        ArbeitnowScraper()),
            ('Jobicy',           JobicyScraper()),
            ('RemoteOK',         RemoteOKScraper()),
            ('TheMuse',          TheMuseScraper()),
            ('IndeedRSS',        IndeedRSSScraper()),
            ('WeWorkRemotely',   WeWorkRemotelyScraper()),
        ]
        self._jobspy = JobSpyScraper()

        # Adzuna — only when keys are set
        app_id = os.environ.get('ADZUNA_APP_ID', '')
        app_key = os.environ.get('ADZUNA_APP_KEY', '')
        self._adzuna = AdzunaScraper(app_id, app_key) if app_id and app_key else None
        if self._adzuna:
            logger.info(f"Adzuna enabled for countries: {self._adzuna.countries}")
        else:
            logger.info("Adzuna disabled — set ADZUNA_APP_ID and ADZUNA_APP_KEY to enable")

        self._african = [
            ('BrighterMonday', BrighterMondayScraper()),
            ('Fuzu', FuzuScraper()),
            ('KenyaJob', KenyaJobScraper()),
            ('MyJobMag', MyJobMagScraper()),
        ]

    def fetch_all_jobs(self, query='', location='', limit_per_source=5000) -> List[Dict]:
        all_jobs = []

        # 1. Free APIs
        for name, scraper in self._free_apis:
            try:
                jobs = scraper.fetch_jobs(query, location, limit_per_source)
                all_jobs.extend(jobs)
                logger.info(f"{name}: {len(jobs)} fetched")
            except Exception as e:
                logger.error(f"{name}: {e}")

        # 2. JobSpy (LinkedIn, Indeed, Glassdoor, ZipRecruiter)
        try:
            jobs = self._jobspy.fetch_jobs(query, location, limit_per_source)
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error(f"JobSpy: {e}")

        # 3. Adzuna
        if self._adzuna:
            try:
                # For unlimited, use larger limit for Adzuna (max 50 per page)
                adzuna_limit = 50 if limit_per_source is None else limit_per_source // 3
                jobs = self._adzuna.fetch_jobs(query, location, adzuna_limit)
                all_jobs.extend(jobs)
            except Exception as e:
                logger.error(f"Adzuna: {e}")

        # 4. African boards
        for name, scraper in self._african:
            try:
                jobs = scraper.fetch_jobs(query, location, limit_per_source)
                all_jobs.extend(jobs)
                logger.info(f"{name}: {len(jobs)} fetched")
            except Exception as e:
                logger.error(f"{name}: {e}")

        logger.info(f"Total fetched: {len(all_jobs)}")
        return all_jobs

    def fetch_kenya_jobs(self, query='', limit_per_source=20) -> List[Dict]:
        """Targeted Kenya-focused fetch."""
        all_jobs = []
        for name, scraper in self._african:
            try:
                jobs = scraper.fetch_jobs(query, 'Kenya', limit_per_source)
                all_jobs.extend(jobs)
            except Exception as e:
                logger.error(f"{name}: {e}")
        # Also run JobSpy for Kenya
        try:
            old_countries = self._jobspy.countries
            self._jobspy.countries = ['Kenya', 'South Africa', 'Nigeria']
            jobs = self._jobspy.fetch_jobs(query, 'Kenya', limit_per_source)
            all_jobs.extend(jobs)
            self._jobspy.countries = old_countries
        except Exception as e:
            logger.error(f"JobSpy Kenya: {e}")
        logger.info(f"Kenya fetch total: {len(all_jobs)}")
        return all_jobs

    def fetch_international_jobs(self, query='', limit_per_source=20) -> List[Dict]:
        """Targeted international (US/UK/CA/EU) fetch."""
        all_jobs = []
        for name, scraper in self._free_apis:
            try:
                jobs = scraper.fetch_jobs(query, '', limit_per_source)
                all_jobs.extend(jobs)
            except Exception as e:
                logger.error(f"{name}: {e}")
        try:
            old_countries = self._jobspy.countries
            self._jobspy.countries = ['USA', 'UK', 'Canada', 'Germany', 'France', 'Australia']
            jobs = self._jobspy.fetch_jobs(query, '', limit_per_source)
            all_jobs.extend(jobs)
            self._jobspy.countries = old_countries
        except Exception as e:
            logger.error(f"JobSpy international: {e}")
        if self._adzuna:
            try:
                jobs = self._adzuna.fetch_jobs(query, '', limit_per_source // 2)
                all_jobs.extend(jobs)
            except Exception as e:
                logger.error(f"Adzuna: {e}")
        logger.info(f"International fetch total: {len(all_jobs)}")
        return all_jobs

    def save_jobs_to_db(self, jobs: List[Dict]) -> Dict:
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


# Singleton
job_fetcher = JobFetcher()
