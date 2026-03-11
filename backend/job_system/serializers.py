"""
Job System Serializers
API serializers for job listings, applications, and matching
"""

from rest_framework import serializers
from .models import (
    Job, SavedJob, JobApplication, JobMatch, JobSearch,
    AutoApplicationBatch, AutoApplicationItem, UserApplicationPreference,
    JobCategory, JobCache
)


class JobSerializer(serializers.ModelSerializer):
    """Basic job serializer for listing"""
    
    salary_range = serializers.ReadOnlyField()
    external_url = serializers.CharField(source='job_url', read_only=True)
    
    class Meta:
        model = Job
        fields = [
            'id', 'title', 'company', 'description', 'location',
            'salary_min', 'salary_max', 'salary_range',
            'job_type', 'experience_level',
            'source', 'job_url', 'external_url', 'company_logo_url',
            'skills_required', 'posted_date', 'is_active', 'view_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'view_count', 'created_at', 'updated_at']


class JobDetailSerializer(serializers.ModelSerializer):
    """Detailed job serializer with all fields"""
    
    salary_range = serializers.ReadOnlyField()
    
    class Meta:
        model = Job
        fields = '__all__'
        read_only_fields = ['id', 'view_count', 'application_count', 'created_at', 'updated_at']


# NOTE: Jobs are fetched from external sources, not created by users
# Manual job creation has been removed

class SavedJobSerializer(serializers.ModelSerializer):
    """Serializer for saved/bookmarked jobs"""
    
    job = JobDetailSerializer(read_only=True)
    job_id = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = SavedJob
        fields = ['id', 'user', 'job', 'job_id', 'notes', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']
    
    def create(self, validated_data):
        """Create saved job with user from request"""
        job_id = validated_data.pop('job_id')
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            raise serializers.ValidationError({'job_id': 'Job not found'})
        
        return SavedJob.objects.create(
            user=self.context['request'].user,
            job=job,
            **validated_data
        )


class JobApplicationSerializer(serializers.ModelSerializer):
    """Serializer for job applications"""
    
    job = JobDetailSerializer(read_only=True)
    job_id = serializers.UUIDField(write_only=True)
    cv_version_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    salary_range = serializers.CharField(source='job.salary_range', read_only=True)
    
    class Meta:
        model = JobApplication
        fields = [
            'id', 'user', 'job', 'job_id', 'cv_version', 'cv_version_id',
            'status', 'cover_letter', 'application_date', 'application_url',
            'interview_date', 'interview_type', 'interview_notes',
            'follow_up_date', 'follow_up_completed', 'notes', 'reminders',
            'match_score', 'matched_skills', 'missing_skills',
            'salary_range', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        """Create application with user from request"""
        job_id = validated_data.pop('job_id')
        cv_version_id = validated_data.pop('cv_version_id', None)
        
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            raise serializers.ValidationError({'job_id': 'Job not found'})
        
        cv_version = None
        if cv_version_id:
            from cv_builder.models import CVVersion
            try:
                cv_version = CVVersion.objects.get(id=cv_version_id)
            except CVVersion.DoesNotExist:
                raise serializers.ValidationError({'cv_version_id': 'CV version not found'})
        
        return JobApplication.objects.create(
            user=self.context['request'].user,
            job=job,
            cv_version=cv_version,
            **validated_data
        )


class JobApplicationStatusSerializer(serializers.Serializer):
    """Serializer for updating application status"""
    
    status = serializers.ChoiceField(choices=JobApplication.STATUS_CHOICES)
    interview_date = serializers.DateTimeField(required=False, allow_null=True)
    interview_type = serializers.CharField(max_length=50, required=False, allow_null=True)
    interview_notes = serializers.CharField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_null=True)
    
    def validate(self, data):
        """Validate status-specific fields"""
        status = data.get('status')
        
        # Validate interview fields for interview statuses
        if status in ['interview', 'technical', 'screening']:
            if not data.get('interview_date'):
                raise serializers.ValidationError({
                    'interview_date': 'Interview date is required for interview status'
                })
        
        return data


class JobMatchSerializer(serializers.ModelSerializer):
    """Serializer for job match results"""
    
    job = JobDetailSerializer(read_only=True)
    job_id = serializers.UUIDField(write_only=True)
    cv_version_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    salary_range = serializers.CharField(source='job.salary_range', read_only=True)
    
    class Meta:
        model = JobMatch
        fields = [
            'id', 'user', 'job', 'job_id', 'cv_version', 'cv_version_id',
            'overall_match', 'skill_match', 'experience_match',
            'location_match', 'matched_skills', 'missing_skills',
            'additional_skills', 'suggestions', 'improvement_ideas',
            'salary_range', 'created_at',
        ]
        read_only_fields = ['id', 'user', 'created_at']
    
    def create(self, validated_data):
        """Create match with user from request"""
        job_id = validated_data.pop('job_id')
        cv_version_id = validated_data.pop('cv_version_id', None)
        
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            raise serializers.ValidationError({'job_id': 'Job not found'})
        
        cv_version = None
        if cv_version_id:
            from cv_builder.models import CVVersion
            try:
                cv_version = CVVersion.objects.get(id=cv_version_id)
            except CVVersion.DoesNotExist:
                raise serializers.ValidationError({'cv_version_id': 'CV version not found'})
        
        return JobMatch.objects.create(
            user=self.context['request'].user,
            job=job,
            cv_version=cv_version,
            **validated_data
        )


class JobSearchSerializer(serializers.ModelSerializer):
    """Serializer for saved job searches"""
    
    class Meta:
        model = JobSearch
        fields = [
            'id', 'user', 'query', 'location', 'job_type',
            'experience_level', 'salary_min', 'salary_max',
            'skills', 'sources', 'name', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        """Create search with user from request"""
        return JobSearch.objects.create(
            user=self.context['request'].user,
            **validated_data
        )


class JobSearchQuerySerializer(serializers.Serializer):
    """Serializer for job search query parameters"""
    
    query = serializers.CharField(max_length=200, required=False, allow_blank=True)
    location = serializers.CharField(max_length=200, required=False, allow_blank=True)
    job_type = serializers.ChoiceField(
        choices=Job.JOB_TYPE_CHOICES,
        required=False,
        allow_null=True
    )
    experience_level = serializers.ChoiceField(
        choices=Job.EXPERIENCE_CHOICES,
        required=False,
        allow_null=True
    )
    salary_min = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    salary_max = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    skills = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        allow_empty=True
    )
    sources = serializers.ListField(
        child=serializers.ChoiceField(choices=Job.SOURCE_CHOICES),
        required=False,
        allow_empty=True
    )
    page = serializers.IntegerField(default=1, min_value=1)
    page_size = serializers.IntegerField(default=20, min_value=1, max_value=100)
    order_by = serializers.ChoiceField(
        choices=['created_at', 'salary_max', 'salary_min', 'title', 'company'],
        default='created_at'
    )
    
    def validate(self, data):
        """Validate query parameters"""
        salary_min = data.get('salary_min')
        salary_max = data.get('salary_max')
        
        if salary_min and salary_max and salary_min > salary_max:
            raise serializers.ValidationError({
                'salary_min': 'Minimum salary cannot be greater than maximum salary'
            })
        
        return data


class JobCategorySerializer(serializers.ModelSerializer):
    """Serializer for job categories"""
    
    class Meta:
        model = JobCategory
        fields = [
            'id', 'name', 'slug', 'description', 'icon',
            'is_active', 'order', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserApplicationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for user auto-apply preferences"""
    
    class Meta:
        model = UserApplicationPreference
        fields = [
            'id', 'user', 'approval_mode', 'min_match_score',
            'approvals_required_for_trust', 'preferred_job_types',
            'preferred_locations', 'min_salary', 'blacklisted_companies',
            'apply_immediately', 'apply_rate_limit', 'apply_start_time',
            'apply_end_time', 'total_approvals', 'total_rejections',
            'trust_score', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'total_approvals', 'total_rejections', 
                          'trust_score', 'created_at', 'updated_at']


class AutoApplicationBatchSerializer(serializers.ModelSerializer):
    """Serializer for auto-apply batches"""
    
    cv_version_id = serializers.UUIDField(source='cv_version.id', read_only=True)
    
    class Meta:
        model = AutoApplicationBatch
        fields = [
            'id', 'user', 'cv_version', 'cv_version_id',
            'search_query', 'search_location', 'search_filters',
            'status', 'total_jobs', 'approved_jobs', 'rejected_jobs',
            'successful_applications', 'failed_applications',
            'started_at', 'completed_at', 'progress_percentage',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'cv_version', 'status',
                          'approved_jobs', 'rejected_jobs',
                          'successful_applications', 'failed_applications',
                          'started_at', 'completed_at', 'progress_percentage',
                          'created_at', 'updated_at']


class AutoApplicationItemSerializer(serializers.ModelSerializer):
    """Serializer for auto-apply items"""
    
    job_id = serializers.UUIDField(source='job.id', read_only=True)
    job_title = serializers.CharField(source='job.title', read_only=True)
    job_company = serializers.CharField(source='job.company', read_only=True)
    job_location = serializers.CharField(source='job.location', read_only=True)
    
    class Meta:
        model = AutoApplicationItem
        fields = [
            'id', 'batch', 'job', 'job_id', 'job_title', 'job_company', 'job_location',
            'match_score', 'matched_skills', 'missing_skills',
            'user_approval_status', 'application_status',
            'custom_cv', 'custom_cover_letter',
            'edited_cv', 'edited_cover_letter',
            'final_cv', 'final_cover_letter',
            'application_url', 'applied_at', 'error_message',
            'job_application', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'batch', 'job', 'job_application',
                          'applied_at', 'created_at', 'updated_at']
