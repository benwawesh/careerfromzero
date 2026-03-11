"""
Job Search Engine Service
Real-time search across multiple job boards with caching
"""

import hashlib
from django.utils import timezone
from datetime import timedelta
from ..models import Job, JobCache, JobCategory
from .job_scraper import JobFetcher


class JobSearchEngine:
    """Real-time job search engine with caching"""

    def __init__(self):
        self.fetcher = JobFetcher()
        self.cache_duration = timedelta(hours=1)

    def search(self, query: str = None, location: str = None,
               job_type: str = None, category: str = None,
               salary_min: float = None, salary_max: float = None,
               experience_level: str = None, limit: int = 50,
               use_cache: bool = True, sources: list = None) -> dict:
        """Search jobs — checks cache first, then DB, then live scrape."""
        cache_key = self._generate_cache_key(
            query, location, job_type, category,
            salary_min, salary_max, experience_level, limit, sources
        )

        if use_cache:
            cached = self._get_cached_results(cache_key)
            if cached:
                return {
                    'results': cached['results'],
                    'count': cached['result_count'],
                    'from_cache': True,
                    'cache_key': cache_key,
                }

        results = self._real_time_search(
            query, location, job_type, category,
            salary_min, salary_max, experience_level, limit, sources
        )

        if use_cache and results['count'] > 0:
            self._cache_results(cache_key, results)

        return {**results, 'from_cache': False, 'cache_key': cache_key}

    def _generate_cache_key(self, *args) -> str:
        param_str = '|'.join(str(a) for a in args if a is not None)
        return hashlib.md5(param_str.encode()).hexdigest()

    def _get_cached_results(self, cache_key: str):
        try:
            cache = JobCache.objects.get(search_key=cache_key)
            if cache.is_valid():
                return {'results': cache.results, 'result_count': cache.result_count}
        except JobCache.DoesNotExist:
            pass
        return None

    def _cache_results(self, cache_key: str, results: dict):
        try:
            JobCache.objects.update_or_create(
                search_key=cache_key,
                defaults={
                    'results': results['results'],
                    'result_count': results['count'],
                    'expires_at': timezone.now() + self.cache_duration,
                }
            )
        except Exception as e:
            print(f"Error caching results: {e}")

    def _real_time_search(self, query, location, job_type, category,
                          salary_min, salary_max, experience_level,
                          limit, sources) -> dict:
        """Search DB; supplement with live fetch if needed."""
        db_jobs = list(self._search_database(
            query, location, job_type, category,
            salary_min, salary_max, experience_level
        ))

        if len(db_jobs) < limit:
            try:
                live_jobs_raw = self.fetcher.fetch_all_jobs(
                    query=query or '',
                    location=location or '',
                    limit_per_source=max(5, limit - len(db_jobs))
                )
                if live_jobs_raw:
                    self.fetcher.save_jobs_to_db(live_jobs_raw)
                    db_jobs = list(self._search_database(
                        query, location, job_type, category,
                        salary_min, salary_max, experience_level
                    ))
            except Exception as e:
                print(f"Live fetch error (non-critical): {e}")

        serialized = [self._serialize_job(j) for j in db_jobs[:limit]]
        return {'results': serialized, 'count': len(serialized)}

    def _search_database(self, query, location, job_type, category,
                         salary_min, salary_max, experience_level):
        from django.db.models import Q
        jobs = Job.objects.filter(is_active=True)

        if query:
            jobs = jobs.filter(
                Q(title__icontains=query) |
                Q(company__icontains=query) |
                Q(description__icontains=query)
            )
        if location:
            jobs = jobs.filter(location__icontains=location)
        if job_type:
            jobs = jobs.filter(job_type=job_type)
        if experience_level:
            jobs = jobs.filter(experience_level=experience_level)
        if salary_min:
            jobs = jobs.filter(salary_max__gte=salary_min)
        if salary_max:
            jobs = jobs.filter(salary_min__lte=salary_max)

        return jobs.order_by('-created_at')

    def _serialize_job(self, job) -> dict:
        return {
            'id': str(job.id),
            'title': job.title,
            'company': job.company,
            'description': job.description[:500],
            'location': job.location,
            'salary_range': job.salary_range,
            'salary_min': float(job.salary_min) if job.salary_min else None,
            'salary_max': float(job.salary_max) if job.salary_max else None,
            'job_type': job.job_type,
            'experience_level': job.experience_level,
            'source': job.source,
            'job_url': job.job_url,
            'company_logo_url': job.company_logo_url,
            'posted_date': job.posted_date.isoformat() if job.posted_date else None,
            'skills_required': job.skills_required,
            'view_count': job.view_count,
            'application_count': job.application_count,
        }

    def get_categories(self) -> list:
        return [
            {
                'id': str(cat.id),
                'name': cat.name,
                'slug': cat.slug,
                'description': cat.description,
                'icon': cat.icon,
                'order': cat.order,
            }
            for cat in JobCategory.objects.filter(is_active=True).order_by('order')
        ]

    def get_popular_searches(self, limit: int = 10) -> list:
        return [
            {
                'search_key': cache.search_key,
                'result_count': cache.result_count,
                'created_at': cache.created_at.isoformat(),
            }
            for cache in JobCache.objects.all().order_by('-created_at')[:limit]
        ]

    def clear_cache(self):
        expired = JobCache.objects.filter(expires_at__lt=timezone.now())
        count = expired.count()
        expired.delete()
        return count
