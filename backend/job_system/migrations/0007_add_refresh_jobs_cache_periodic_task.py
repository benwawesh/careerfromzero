from django.db import migrations


def add_periodic_task(apps, schema_editor):
    IntervalSchedule = apps.get_model('django_celery_beat', 'IntervalSchedule')
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')

    schedule, _ = IntervalSchedule.objects.get_or_create(
        every=4,
        period=IntervalSchedule.HOURS,
    )
    PeriodicTask.objects.get_or_create(
        name='Refresh Jobs Redis Cache',
        defaults={
            'interval': schedule,
            'task': 'job_system.tasks.refresh_jobs_cache',
            'enabled': True,
        },
    )


def remove_periodic_task(apps, schema_editor):
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')
    PeriodicTask.objects.filter(name='Refresh Jobs Redis Cache').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('job_system', '0005_add_kenyan_source_choices'),
        ('django_celery_beat', '0018_improve_crontab_helptext'),
    ]

    operations = [
        migrations.RunPython(add_periodic_task, remove_periodic_task),
    ]
