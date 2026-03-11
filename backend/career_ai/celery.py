import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'career_ai.settings')

app = Celery('career_ai')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
