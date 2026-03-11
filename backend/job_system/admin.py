from django.contrib import admin
from .models import Job, SavedJob, JobApplication, JobMatch, JobSearch


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ['title', 'company', 'location', 'job_type', 'source', 'is_active', 'view_count', 'created_at']
    list_filter = ['source', 'job_type', 'experience_level', 'is_active']
    search_fields = ['title', 'company', 'description', 'location']
    readonly_fields = ['id', 'view_count', 'application_count', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'


@admin.register(SavedJob)
class SavedJobAdmin(admin.ModelAdmin):
    list_display = ['user', 'job', 'notes', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'job__title', 'job__company']


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ['user', 'job', 'status', 'application_date', 'interview_date', 'created_at']
    list_filter = ['status', 'application_date', 'created_at']
    search_fields = ['user__username', 'job__title', 'job__company']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(JobMatch)
class JobMatchAdmin(admin.ModelAdmin):
    list_display = ['user', 'job', 'overall_match', 'skill_match', 'experience_match', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'job__title', 'job__company']
    readonly_fields = ['id', 'created_at']


@admin.register(JobSearch)
class JobSearchAdmin(admin.ModelAdmin):
    list_display = ['user', 'name', 'query', 'location', 'job_type', 'is_active', 'created_at']
    list_filter = ['job_type', 'experience_level', 'is_active', 'created_at']
    search_fields = ['user__username', 'name', 'query', 'location']
