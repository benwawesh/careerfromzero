"""
Kenyan Job Board Scrapers
=========================
Fetches ALL jobs from Kenyan job boards with proper pagination.

Strategy per source:
  BrighterMonday  — link-based extraction (/listings/ hrefs) + pagination
  MyJobMag        — link-based extraction + pagination
  Jobwebkenya     — RSS feed (most reliable, no guessing selectors)
  Corporate Staffing Kenya — link-based + pagination
  NGO Jobs Africa — RSS feed
  Career Kenya    — link-based + pagination

All scrapers:
  - Paginate through ALL pages (not just page 1)
  - Use link-based extraction where CSS classes are unreliable
  - Fall back gracefully — log what was found and move on
"""

import re
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _clean(text: str) -> str:
    return re.sub(r'\s+', ' ', text or '').strip()

def _strip_html(html: str) -> str:
    return _clean(BeautifulSoup(html or '', 'html.parser').get_text(separator=' '))

def _http(timeout=20):
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,*/*;q=0.9',
        'Accept-Language': 'en-US,en;q=0.9',
    })
    return s

def _rel_date(text: str) -> Optional[datetime]:
    """Parse 'X days ago', 'X hours ago', ISO dates, etc."""
    if not text:
        return None
    text = text.lower().strip()
    m = re.search(r'(\d+)\s*(hour|day|week|month)', text)
    if m and 'ago' in text:
        n, unit = int(m.group(1)), m.group(2)
        delta = {'hour': timedelta(hours=n), 'day': timedelta(days=n),
                 'week': timedelta(weeks=n), 'month': timedelta(days=n*30)}.get(unit)
        return datetime.now() - delta if delta else None
    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%B %d, %Y', '%b %d, %Y'):
        try:
            return datetime.strptime(text.strip()[:20], fmt)
        except ValueError:
            pass
    return None

def _get(url, params=None, timeout=20) -> Optional[requests.Response]:
    try:
        r = _http().get(url, params=params or {}, timeout=timeout)
        r.raise_for_status()
        return r
    except Exception as e:
        logger.warning(f"GET {url}: {e}")
        return None

def _job_links(soup: BeautifulSoup, base: str, patterns: List[str]) -> List[str]:
    """Extract job URLs by matching href patterns."""
    seen, links = set(), []
    for a in soup.select('a[href]'):
        href = a['href'].strip()
        if not href.startswith('http'):
            href = base.rstrip('/') + ('/' if not href.startswith('/') else '') + href
        if href in seen:
            continue
        if any(p in href for p in patterns):
            seen.add(href)
            links.append(href)
    return links

def _next_page_url(soup: BeautifulSoup, base: str) -> Optional[str]:
    """Find the 'next page' link."""
    for sel in ["a[rel='next']", "a[rel=\"next\"]", '.next a', 'a.next',
                '.pagination a.active + a', 'li.next a', 'a[aria-label="Next"]']:
        el = soup.select_one(sel)
        if el and el.get('href'):
            href = el['href']
            return href if href.startswith('http') else base + href
    return None

def _make_job(title, company, location, job_url, source, external_id,
              description='', job_type='full_time', posted_date=None) -> Optional[Dict]:
    if not title or len(title) < 3:
        return None
    return {
        'title': _clean(title)[:200],
        'company': _clean(company or 'Unknown')[:200],
        'description': _clean(description)[:5000],
        'location': _clean(location or 'Kenya')[:200],
        'job_url': job_url or '',
        'job_type': job_type,
        'source': source,
        'external_id': str(external_id)[:195],
        'posted_date': posted_date.date() if isinstance(posted_date, datetime) else posted_date,
        'is_active': True,
    }


# ─── RSS Helper ───────────────────────────────────────────────────────────────

def _scrape_rss(feed_url: str, source: str, prefix: str, max_items: int = 500) -> List[Dict]:
    """Parse an RSS/Atom feed and return job dicts."""
    jobs = []
    r = _get(feed_url, timeout=15)
    if not r:
        return []
    try:
        root = ElementTree.fromstring(r.content)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        # RSS 2.0
        items = root.findall('.//item')
        # Atom
        if not items:
            items = root.findall('.//atom:entry', ns) or root.findall('.//entry')
        for item in items[:max_items]:
            def tag(name, fallbacks=()):
                for n in (name,) + fallbacks:
                    el = item.find(n)
                    if el is not None and el.text:
                        return el.text.strip()
                return ''
            title = tag('title')
            link  = tag('link') or tag('guid') or tag('atom:link', ('id',))
            desc  = _strip_html(tag('description') or tag('content') or tag('summary'))
            pub   = _rel_date(tag('pubDate') or tag('published') or tag('updated'))
            slug  = link.rstrip('/').split('/')[-1][:80] if link else str(hash(title))
            j = _make_job(title, '', 'Kenya', link, source, f"{prefix}_{slug}",
                          description=desc, posted_date=pub)
            if j:
                jobs.append(j)
    except Exception as e:
        logger.error(f"RSS parse {feed_url}: {e}")
    logger.info(f"RSS {feed_url}: {len(jobs)} items")
    return jobs


# ══════════════════════════════════════════════════════════════════════════════
# BRIGHTERMONDAY KENYA
# Strategy: fetch /jobs page, extract all /listings/ hrefs, paginate
# ══════════════════════════════════════════════════════════════════════════════

class BrighterMondayKenyaScraper:
    BASE = "https://www.brightermonday.co.ke"
    SOURCE = 'brightermonday'

    def fetch_jobs(self, query='', location='', max_pages=30) -> List[Dict]:
        jobs, seen, page = [], set(), 1
        logger.info("BrighterMonday: starting fetch")

        while page <= max_pages:
            params = {'page': page}
            if query:   params['q'] = query
            if location: params['l'] = location

            r = _get(f"{self.BASE}/jobs", params)
            if not r:
                break

            soup = BeautifulSoup(r.text, 'html.parser')

            # Extract job links — BrighterMonday puts each job at /listings/<slug>
            links = _job_links(soup, self.BASE, ['/listings/'])

            if not links:
                # Fallback: try any link that looks like a job URL
                links = _job_links(soup, self.BASE, ['/jobs/', '/vacancy/', '/job/'])

            if not links:
                logger.info(f"BrighterMonday page {page}: no job links found, stopping")
                break

            new = 0
            for url in links:
                if url in seen:
                    continue
                seen.add(url)
                slug = url.rstrip('/').split('/')[-1]
                # Extract card details from the listing page element in the soup
                j = self._extract_from_soup(soup, url, slug)
                if j:
                    jobs.append(j)
                    new += 1

            logger.info(f"BrighterMonday page {page}: {new} new jobs (total: {len(jobs)})")

            nxt = _next_page_url(soup, self.BASE)
            if not nxt:
                break
            page += 1
            time.sleep(0.5)

        logger.info(f"BrighterMonday total: {len(jobs)}")
        return jobs

    def _extract_from_soup(self, soup, url, slug) -> Optional[Dict]:
        """Find the card for this URL in the listing soup."""
        try:
            # Try to find the anchor that links to this job
            a = soup.find('a', href=lambda h: h and slug in h)
            card = a.find_parent() if a else None

            title = company = location = ''
            if card:
                # Walk up to find a container with more info
                for _ in range(4):
                    texts = [t.strip() for t in card.stripped_strings if len(t.strip()) > 3]
                    if len(texts) >= 2:
                        title = texts[0]
                        company = texts[1] if len(texts) > 1 else ''
                        # Look for location among remaining texts
                        for t in texts[2:]:
                            if any(loc in t.lower() for loc in
                                   ('nairobi', 'mombasa', 'kisumu', 'kenya', 'remote', 'nationwide')):
                                location = t
                                break
                        break
                    card = card.parent

            if not title:
                title = slug.replace('-', ' ').title()

            return _make_job(title, company, location or 'Kenya', url,
                             self.SOURCE, f"bm_{slug}")
        except Exception as e:
            logger.debug(f"BM extract error: {e}")
            return _make_job(slug.replace('-', ' ').title(), '', 'Kenya',
                             url, self.SOURCE, f"bm_{slug}")


# ══════════════════════════════════════════════════════════════════════════════
# MYJOBMAG KENYA
# Strategy: paginate /jobs, extract job-link hrefs
# ══════════════════════════════════════════════════════════════════════════════

class MyJobMagKenyaScraper:
    BASE = "https://www.myjobmag.co.ke"
    SOURCE = 'myjobmag'

    def fetch_jobs(self, query='', location='', max_pages=30) -> List[Dict]:
        jobs, seen, page = [], set(), 1
        logger.info("MyJobMag: starting fetch")

        while page <= max_pages:
            params = {'page': page}
            if query:    params['q'] = query
            if location: params['l'] = location

            r = _get(f"{self.BASE}/jobs", params)
            if not r:
                break

            soup = BeautifulSoup(r.text, 'html.parser')

            # Use /job/ (singular) to get individual job pages, not /jobs-at/ company pages
            links = _job_links(soup, self.BASE, ['/job/'])
            # Filter out company pages and navigation
            links = [l for l in links if '/jobs-at/' not in l and '/category/' not in l]

            if not links:
                logger.info(f"MyJobMag page {page}: no job links, stopping")
                break

            new = 0
            for url in links:
                if url in seen:
                    continue
                seen.add(url)
                slug = url.rstrip('/').split('/')[-1]
                a_el = soup.find('a', href=lambda h: h and slug in h)
                card = a_el.find_parent() if a_el else None

                title = company = location = ''
                if card:
                    texts = [t.strip() for t in card.stripped_strings if t.strip()]
                    if texts:
                        title = texts[0]
                        company = texts[1] if len(texts) > 1 else ''

                if not title:
                    title = slug.replace('-', ' ').replace('_', ' ').title()

                j = _make_job(title, company, location or 'Kenya', url,
                              self.SOURCE, f"mjm_{slug}")
                if j:
                    jobs.append(j)
                    new += 1

            logger.info(f"MyJobMag page {page}: {new} new jobs (total: {len(jobs)})")

            nxt = _next_page_url(soup, self.BASE)
            if not nxt:
                break
            page += 1
            time.sleep(0.5)

        logger.info(f"MyJobMag total: {len(jobs)}")
        return jobs


# ══════════════════════════════════════════════════════════════════════════════
# JOBWEBKENYA — RSS FEED (most reliable)
# ══════════════════════════════════════════════════════════════════════════════

class JobwebkenyaScraper:
    """
    Jobwebkenya publishes an RSS feed — no selector guessing needed.
    https://www.jobwebkenya.com/feed/
    """
    SOURCE = 'jobwebkenya'
    FEEDS = [
        "https://www.jobwebkenya.com/feed/",
        "https://www.jobwebkenya.com/rss/",
        "https://www.jobwebkenya.com/?feed=rss2",
    ]

    def fetch_jobs(self, query='', location='', **kwargs) -> List[Dict]:
        for url in self.FEEDS:
            jobs = _scrape_rss(url, self.SOURCE, 'jwk')
            if jobs:
                logger.info(f"Jobwebkenya RSS: {len(jobs)} jobs")
                return jobs
        # Fallback: scrape the listing page
        return self._scrape_html(query)

    def _scrape_html(self, query='') -> List[Dict]:
        jobs, seen, page = [], set(), 1
        base = "https://www.jobwebkenya.com"
        while page <= 20:
            params = {'page': page}
            if query:
                params['s'] = query
            r = _get(f"{base}/jobs", params)
            if not r:
                r = _get(base, params)
            if not r:
                break
            soup = BeautifulSoup(r.text, 'html.parser')
            links = _job_links(soup, base, ['/job/', '/jobs/', '/vacancy/', '/?p='])
            if not links:
                break
            new = 0
            for url in links:
                if url in seen:
                    continue
                seen.add(url)
                slug = url.rstrip('/').split('/')[-1]
                a_el = soup.find('a', href=lambda h: h and slug in h)
                card = a_el.find_parent() if a_el else None
                title = ''
                if card:
                    texts = [t.strip() for t in card.stripped_strings if t.strip()]
                    title = texts[0] if texts else ''
                if not title:
                    title = slug.replace('-', ' ').title()
                j = _make_job(title, '', 'Kenya', url, self.SOURCE, f"jwk_{slug}")
                if j:
                    jobs.append(j)
                    new += 1
            if not new:
                break
            page += 1
            time.sleep(0.5)
        return jobs


# ══════════════════════════════════════════════════════════════════════════════
# NGO JOBS AFRICA — RSS FEED
# ══════════════════════════════════════════════════════════════════════════════

class NgoJobsAfricaScraper:
    """
    NGO / humanitarian jobs — ReliefWeb API (UN-backed, very reliable).
    https://reliefweb.int/jobs?country=kenya
    """
    SOURCE = 'ngojobs'
    API = "https://api.reliefweb.int/v1/jobs"

    def fetch_jobs(self, query='', location='', max_pages=5, **kwargs) -> List[Dict]:
        jobs = []
        try:
            for page in range(max_pages):
                payload = {
                    "filter": {"field": "country.name", "value": "Kenya"},
                    "fields": {"include": ["title", "source", "date", "url", "body"]},
                    "limit": 100,
                    "offset": page * 100,
                    "sort": ["date:desc"],
                }
                if query:
                    payload["query"] = {"value": query, "operator": "AND"}
                r = _http().post(self.API, json=payload, timeout=15)
                r.raise_for_status()
                data = r.json().get('data', [])
                if not data:
                    break
                for item in data:
                    f = item.get('fields', {})
                    title = f.get('title', '')
                    org = (f.get('source') or [{}])[0].get('name', '')
                    url = f.get('url', '')
                    desc = _strip_html(f.get('body', ''))[:2000]
                    pub = f.get('date', {}).get('created', '')
                    slug = url.rstrip('/').split('/')[-1] if url else str(hash(title))
                    j = _make_job(title, org, 'Kenya', url, self.SOURCE,
                                  f"ngo_{slug}", description=desc,
                                  posted_date=_rel_date(pub[:10]) if pub else None)
                    if j:
                        jobs.append(j)
            logger.info(f"NGO Jobs (ReliefWeb): {len(jobs)}")
        except Exception as e:
            logger.error(f"NGO Jobs: {e}")
        return jobs


# ══════════════════════════════════════════════════════════════════════════════
# CORPORATE STAFFING KENYA
# ══════════════════════════════════════════════════════════════════════════════

class CorporateStaffingScraper:
    """
    Corporate Staffing Services Kenya
    https://www.corporatestaffing.co.ke/jobs/
    """
    BASE = "https://www.corporatestaffing.co.ke"
    SOURCE = 'corporatestaffing'

    def fetch_jobs(self, query='', location='', max_pages=20) -> List[Dict]:
        jobs, seen, page = [], set(), 1
        logger.info("Corporate Staffing: starting fetch")

        while page <= max_pages:
            url = f"{self.BASE}/jobs/" if page == 1 else f"{self.BASE}/jobs/page/{page}/"
            r = _get(url)
            if not r:
                break

            soup = BeautifulSoup(r.text, 'html.parser')
            links = _job_links(soup, self.BASE,
                               ['/job/', '/jobs/', '/vacancy/', '/career/'])
            # Filter out navigation links
            links = [l for l in links if not any(
                x in l for x in ['/category/', '/tag/', '/page/', '/author/']
            )]

            if not links:
                logger.info(f"Corporate Staffing page {page}: no job links, stopping")
                break

            new = 0
            for url in links:
                if url in seen:
                    continue
                seen.add(url)
                slug = url.rstrip('/').split('/')[-1]
                a_el = soup.find('a', href=lambda h: h and slug in h)
                card = a_el.find_parent() if a_el else None

                title = company = ''
                if card:
                    texts = [t.strip() for t in card.stripped_strings if t.strip()]
                    title = texts[0] if texts else ''
                    # Company often follows title
                    for t in texts[1:4]:
                        if t != title and len(t) > 2:
                            company = t
                            break

                if not title:
                    title = slug.replace('-', ' ').title()

                j = _make_job(title, company, 'Kenya', url,
                              self.SOURCE, f"cs_{slug}")
                if j:
                    jobs.append(j)
                    new += 1

            logger.info(f"Corporate Staffing page {page}: {new} jobs (total: {len(jobs)})")

            nxt = _next_page_url(soup, self.BASE)
            if not nxt:
                break
            page += 1
            time.sleep(0.5)

        logger.info(f"Corporate Staffing total: {len(jobs)}")
        return jobs


# ══════════════════════════════════════════════════════════════════════════════
# KENYANJOB.COM
# ══════════════════════════════════════════════════════════════════════════════

class KenyaJobScraper:
    """
    Tries multiple Kenyan job sites since URLs change frequently.
    Primary: jobs.co.ke, fallback: kenyajob.com
    """
    SOURCE = 'kenyajob'

    SITES = [
        ("https://jobs.co.ke", ['/jobs', '/vacancies', '']),
        ("https://www.kenyajob.com", ['/jobs', '/job-listings', '']),
        ("https://www.jobskenya.net", ['/jobs', '']),
    ]

    def fetch_jobs(self, query='', location='', max_pages=20) -> List[Dict]:
        # Find a working site
        base = start_path = None
        for site_base, paths in self.SITES:
            for path in paths:
                r = _get(site_base + path)
                if r and r.status_code == 200:
                    base, start_path = site_base, path
                    break
            if base:
                break

        if not base:
            logger.warning("KenyaJob: all sites unreachable")
            return []

        jobs, seen, page = [], set(), 1
        logger.info(f"KenyaJob: using {base}{start_path}")

        while page <= max_pages:
            params = {'page': page}
            if query:
                params['s'] = query
            r = _get(base + start_path, params)
            if not r:
                break

            soup = BeautifulSoup(r.text, 'html.parser')
            links = _job_links(soup, base, ['/job/', '/jobs/', '/vacancy/', '/listing/'])
            links = [l for l in links if not any(x in l for x in ['/category/', '/page/'])]

            if not links:
                break

            new = 0
            for url in links:
                if url in seen:
                    continue
                seen.add(url)
                slug = url.rstrip('/').split('/')[-1]
                a_el = soup.find('a', href=lambda h: h and slug in h)
                card = a_el.find_parent() if a_el else None
                title = ''
                if card:
                    texts = [t.strip() for t in card.stripped_strings if t.strip()]
                    title = texts[0] if texts else ''
                if not title:
                    title = slug.replace('-', ' ').title()
                j = _make_job(title, '', 'Kenya', url, self.SOURCE, f"kj_{slug}")
                if j:
                    jobs.append(j)
                    new += 1

            if not new:
                break
            page += 1
            time.sleep(0.5)

        logger.info(f"KenyaJob total: {len(jobs)}")
        return jobs


# ══════════════════════════════════════════════════════════════════════════════
# STANDARD MEDIA / NATION CAREERS (RSS)
# ══════════════════════════════════════════════════════════════════════════════

class NationCareersScraper:
    """
    Nation Media Group / Standard Digital jobs section — HTML scraping.
    Falls back gracefully if blocked.
    """
    SOURCE = 'nationkenya'
    BASE = "https://nation.africa"

    def fetch_jobs(self, query='', location='', max_pages=5, **kwargs) -> List[Dict]:
        jobs, seen, page = [], set(), 1
        logger.info("Nation Kenya: starting fetch")
        while page <= max_pages:
            params = {'page': page}
            if query:
                params['q'] = query
            for path in ['/kenya/jobs', '/jobs', '/classifieds/jobs']:
                r = _get(self.BASE + path, params)
                if r:
                    break
            if not r:
                break
            soup = BeautifulSoup(r.text, 'html.parser')
            links = _job_links(soup, self.BASE,
                               ['/job/', '/jobs/', '/classifieds/jobs/', '/vacancy/'])
            links = [l for l in links if '/category/' not in l and '/tag/' not in l]
            if not links:
                break
            new = 0
            for url in links:
                if url in seen:
                    continue
                seen.add(url)
                slug = url.rstrip('/').split('/')[-1]
                a_el = soup.find('a', href=lambda h: h and slug in h)
                card = a_el.find_parent() if a_el else None
                title = ''
                if card:
                    texts = [t.strip() for t in card.stripped_strings if t.strip()]
                    title = texts[0] if texts else ''
                if not title:
                    title = slug.replace('-', ' ').title()
                j = _make_job(title, '', 'Kenya', url, self.SOURCE, f"nation_{slug}")
                if j:
                    jobs.append(j)
                    new += 1
            if not new:
                break
            page += 1
            time.sleep(0.5)
        logger.info(f"Nation Kenya: {len(jobs)}")
        return jobs


# ══════════════════════════════════════════════════════════════════════════════
# FUZU — East Africa (Kenya, Uganda, Tanzania, Nigeria, Ghana)
# ══════════════════════════════════════════════════════════════════════════════

class FuzuScraper:
    """
    Fuzu.com — largest East African job platform.
    Covers Kenya, Nigeria, Uganda, Tanzania.
    """
    BASE = "https://www.fuzu.com"
    SOURCE = 'fuzu'

    COUNTRY_PATHS = [
        ('/kenya/jobs',   'Kenya'),
        ('/nigeria/jobs', 'Nigeria'),
        ('/uganda/jobs',  'Uganda'),
    ]

    def fetch_jobs(self, query='', location='', max_pages=30) -> List[Dict]:
        jobs, seen = [], set()
        logger.info("Fuzu: starting fetch")

        paths = self.COUNTRY_PATHS
        if location:
            loc_l = location.lower()
            paths = [(p, c) for p, c in paths if loc_l in c.lower()] or paths

        for path, country in paths:
            page = 1
            while page <= max_pages:
                params = {'page': page}
                if query:
                    params['q'] = query
                r = _get(f"{self.BASE}{path}", params)
                if not r:
                    break

                soup = BeautifulSoup(r.text, 'html.parser')
                links = _job_links(soup, self.BASE,
                                   [f'/{country.lower()}/jobs/', '/jobs/'])
                links = [l for l in links if not any(
                    x in l for x in ['/category/', '/tag/', '/company/']
                )]

                if not links:
                    break

                new = 0
                for url in links:
                    if url in seen:
                        continue
                    seen.add(url)
                    slug = url.rstrip('/').split('/')[-1]
                    a_el = soup.find('a', href=lambda h: h and slug in h)
                    card = a_el.find_parent() if a_el else None
                    title = company = ''
                    if card:
                        texts = [t.strip() for t in card.stripped_strings if t.strip()]
                        title = texts[0] if texts else ''
                        company = texts[1] if len(texts) > 1 else ''
                    if not title:
                        title = slug.replace('-', ' ').title()
                    j = _make_job(title, company, country, url,
                                  self.SOURCE, f"fuzu_{slug}")
                    if j:
                        jobs.append(j)
                        new += 1

                logger.info(f"Fuzu {country} page {page}: {new} jobs (total: {len(jobs)})")
                nxt = _next_page_url(soup, self.BASE)
                if not nxt:
                    break
                page += 1
                time.sleep(0.5)

        logger.info(f"Fuzu total: {len(jobs)}")
        return jobs


# ══════════════════════════════════════════════════════════════════════════════
# JOBBERMAN — Nigeria & Ghana (largest West African job board)
# ══════════════════════════════════════════════════════════════════════════════

class JoobermanScraper:
    """
    Jobberman.com — Nigeria & Ghana's largest job board.
    Provides RSS + HTML scraping with pagination.
    """
    BASE = "https://www.jobberman.com"
    SOURCE = 'jobberman'

    def fetch_jobs(self, query='', location='', max_pages=30) -> List[Dict]:
        # Try RSS first
        jobs = _scrape_rss(f"{self.BASE}/feed", self.SOURCE, 'jbm')
        if jobs:
            logger.info(f"Jobberman RSS: {len(jobs)}")
            return jobs

        # HTML fallback with pagination
        jobs, seen, page = [], set(), 1
        logger.info("Jobberman: starting HTML fetch")

        while page <= max_pages:
            params = {'page': page}
            if query:
                params['q'] = query
            if location:
                params['location'] = location

            r = _get(f"{self.BASE}/jobs", params)
            if not r:
                break

            soup = BeautifulSoup(r.text, 'html.parser')
            links = _job_links(soup, self.BASE,
                               ['/listings/', '/jobs/', '/vacancy/'])
            links = [l for l in links if not any(
                x in l for x in ['/category/', '/tag/', '/page/']
            )]

            if not links:
                break

            new = 0
            for url in links:
                if url in seen:
                    continue
                seen.add(url)
                slug = url.rstrip('/').split('/')[-1]
                a_el = soup.find('a', href=lambda h: h and slug in h)
                card = a_el.find_parent() if a_el else None
                title = company = ''
                if card:
                    texts = [t.strip() for t in card.stripped_strings if t.strip()]
                    title = texts[0] if texts else ''
                    company = texts[1] if len(texts) > 1 else ''
                if not title:
                    title = slug.replace('-', ' ').title()
                j = _make_job(title, company, 'Nigeria', url,
                              self.SOURCE, f"jbm_{slug}")
                if j:
                    jobs.append(j)
                    new += 1

            logger.info(f"Jobberman page {page}: {new} jobs (total: {len(jobs)})")
            nxt = _next_page_url(soup, self.BASE)
            if not nxt:
                break
            page += 1
            time.sleep(0.5)

        logger.info(f"Jobberman total: {len(jobs)}")
        return jobs


# ══════════════════════════════════════════════════════════════════════════════
# CAREER24 / PNET — South Africa
# ══════════════════════════════════════════════════════════════════════════════

class Career24Scraper:
    """
    Career24.com — South Africa's major job board (owned by Media24).
    """
    BASE = "https://www.career24.com"
    SOURCE = 'career24'

    def fetch_jobs(self, query='', location='', max_pages=30) -> List[Dict]:
        jobs, seen, page = [], set(), 1
        logger.info("Career24: starting fetch")

        while page <= max_pages:
            params = {'page': page}
            if query:
                params['keywords'] = query
            if location:
                params['location'] = location

            r = _get(f"{self.BASE}/jobs", params)
            if not r:
                r = _get(self.BASE, params)
            if not r:
                break

            soup = BeautifulSoup(r.text, 'html.parser')
            links = _job_links(soup, self.BASE,
                               ['/jobs/', '/vacancy/', '/job/'])
            links = [l for l in links if not any(
                x in l for x in ['/category/', '/tag/', '/page/']
            )]

            if not links:
                break

            new = 0
            for url in links:
                if url in seen:
                    continue
                seen.add(url)
                slug = url.rstrip('/').split('/')[-1]
                a_el = soup.find('a', href=lambda h: h and slug in h)
                card = a_el.find_parent() if a_el else None
                title = company = ''
                if card:
                    texts = [t.strip() for t in card.stripped_strings if t.strip()]
                    title = texts[0] if texts else ''
                    company = texts[1] if len(texts) > 1 else ''
                if not title:
                    title = slug.replace('-', ' ').title()
                j = _make_job(title, company, 'South Africa', url,
                              self.SOURCE, f"c24_{slug}")
                if j:
                    jobs.append(j)
                    new += 1

            logger.info(f"Career24 page {page}: {new} jobs (total: {len(jobs)})")
            nxt = _next_page_url(soup, self.BASE)
            if not nxt:
                break
            page += 1
            time.sleep(0.5)

        logger.info(f"Career24 total: {len(jobs)}")
        return jobs


# ══════════════════════════════════════════════════════════════════════════════
# COORDINATOR
# ══════════════════════════════════════════════════════════════════════════════

# New sources need to be added to Job model SOURCE_CHOICES
KENYAN_SOURCES = [
    ('BrighterMonday',      BrighterMondayKenyaScraper()),
    ('MyJobMag',            MyJobMagKenyaScraper()),
    ('Jobwebkenya',         JobwebkenyaScraper()),
    ('NGO Jobs Africa',     NgoJobsAfricaScraper()),
    ('Corporate Staffing',  CorporateStaffingScraper()),
    ('KenyaJob',            KenyaJobScraper()),
    ('Nation Careers',      NationCareersScraper()),
    ('Fuzu',                FuzuScraper()),
    ('Jobberman',           JoobermanScraper()),
    ('Career24',            Career24Scraper()),
]


class KenyanJobFetcher:
    """Fetches ALL jobs from Kenyan job boards."""

    def __init__(self):
        self.scrapers = KENYAN_SOURCES

    def fetch_all_jobs(self, query='', location='') -> List[Dict]:
        all_jobs = []
        for name, scraper in self.scrapers:
            try:
                jobs = scraper.fetch_jobs(query=query, location=location)
                all_jobs.extend(jobs)
                logger.info(f"{name}: {len(jobs)} jobs")
            except Exception as e:
                logger.error(f"{name}: {e}")
        logger.info(f"Kenyan total: {len(all_jobs)}")
        return all_jobs

    def fetch_from_source(self, source: str, query='', location='') -> List[Dict]:
        name_map = {n.lower().replace(' ', ''): s for n, s in self.scrapers}
        scraper = name_map.get(source.lower().replace(' ', '').replace('_', ''))
        if not scraper:
            logger.error(f"Unknown source: {source}. Available: {list(name_map)}")
            return []
        return scraper.fetch_jobs(query=query, location=location)

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
        return {'created': created, 'updated': updated, 'errors': errors}


kenyan_job_fetcher = KenyanJobFetcher()
