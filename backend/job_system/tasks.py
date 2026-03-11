import logging
from celery import shared_task
from django.core.cache import cache

logger = logging.getLogger(__name__)

JOBS_LIST_CACHE_KEY = 'jobs:list:unfiltered'
JOBS_FINGERPRINT_KEY = 'jobs:list:fingerprint'
JOBS_CACHE_TIMEOUT = 21600  # 6 hours


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def refresh_jobs_cache(self):
    """
    Runs every 4 hours via Celery Beat.
    Checks if jobs have changed (count + latest updated_at).
    If changed, refreshes Redis cache. If not, skips.
    """
    from .models import Job
    from .serializers import JobSerializer

    try:
        qs = Job.objects.filter(is_active=True).order_by('-created_at')
        total = qs.count()
        latest = qs.values_list('updated_at', flat=True).first()
        fingerprint = f'{total}:{latest.isoformat() if latest else "none"}'

        if cache.get(JOBS_FINGERPRINT_KEY) == fingerprint:
            logger.info('refresh_jobs_cache: no change (%s), skipping.', fingerprint)
            return {'status': 'skipped', 'fingerprint': fingerprint}

        # Clear all cached pages so they get refreshed on next request
        from django_redis import get_redis_connection
        try:
            conn = get_redis_connection('default')
            pattern = f'cai:{JOBS_LIST_CACHE_KEY}:page:*'
            keys = conn.keys(pattern)
            if keys:
                conn.delete(*keys)
                logger.info('refresh_jobs_cache: cleared %d cached pages.', len(keys))
        except Exception as e:
            logger.warning('refresh_jobs_cache: could not clear page keys: %s', e)

        cache.set(JOBS_FINGERPRINT_KEY, fingerprint, timeout=JOBS_CACHE_TIMEOUT)
        logger.info('refresh_jobs_cache: fingerprint updated, pages cleared for refresh.')
        return {'status': 'refreshed', 'count': total}

    except Exception as exc:
        logger.error('refresh_jobs_cache failed: %s', exc, exc_info=True)
        raise self.retry(exc=exc)
