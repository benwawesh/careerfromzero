"""
CV Builder Serializers
Handles serialization/deserialization of CV-related data
"""

from rest_framework import serializers
from .models import CV, CVData, CVAnalysis, CVVersion, JobDescription
import logging

logger = logging.getLogger(__name__)


class CVSerializer(serializers.ModelSerializer):
    """Serializer for CV model"""
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = CV
        fields = [
            'id', 'title', 'file', 'file_url', 'original_filename',
            'file_type', 'file_size', 'is_temporary', 'is_parsed', 
            'is_analyzed', 'is_active', 'uploaded_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'original_filename', 'file_type', 'file_size', 'is_temporary',
            'is_parsed', 'is_analyzed', 'is_active', 'uploaded_at', 'updated_at'
        ]
    
    def get_file_url(self, obj):
        """Get the URL for the CV file"""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None
    
    def validate_file(self, value):
        """Validate CV file"""
        # Check file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if value.size > max_size:
            raise serializers.ValidationError(
                "File size exceeds maximum limit of 10MB"
            )
        
        # Check file type
        file_name = value.name.lower()
        allowed_extensions = ['pdf', 'docx']
        file_ext = file_name.split('.')[-1]
        
        if file_ext not in allowed_extensions:
            raise serializers.ValidationError(
                f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}"
            )
        
        # Check MIME type — accept multiple valid MIME types per format
        # (browsers vary in what content_type they send, especially for DOCX)
        valid_mimes = {
            'pdf': {
                'application/pdf',
                'application/x-pdf',
                'application/octet-stream',
            },
            'docx': {
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/msword',
                'application/zip',
                'application/octet-stream',
            },
        }
        if value.content_type not in valid_mimes.get(file_ext, set()):
            raise serializers.ValidationError(
                f"Invalid file format for .{file_ext}. Got: {value.content_type}"
            )
        
        logger.info(f"CV file validated: {value.name} ({value.size} bytes)")
        return value
    
    def create(self, validated_data):
        """Create CV with file metadata"""
        file = validated_data['file']
        validated_data['original_filename'] = file.name
        validated_data['file_type'] = file.name.split('.')[-1].upper()
        validated_data['file_size'] = file.size
        
        cv = CV.objects.create(**validated_data)
        logger.info(f"CV created: {cv.id} - {cv.title}")
        return cv


class CVDataSerializer(serializers.ModelSerializer):
    """Serializer for CVData model"""
    
    class Meta:
        model = CVData
        fields = [
            'id', 'cv', 'raw_text', 'email', 'phone', 'location',
            'linkedin_url', 'github_url', 'website_url', 'summary',
            'skills', 'experience', 'education', 'projects',
            'certifications', 'languages', 'interests',
            'parsing_status', 'parsing_error', 'extracted_at', 'updated_at'
        ]
        read_only_fields = ['id', 'cv', 'parsing_status', 'parsing_error', 'extracted_at', 'updated_at']


class CVAnalysisSerializer(serializers.ModelSerializer):
    """Serializer for CVAnalysis model"""
    
    class Meta:
        model = CVAnalysis
        fields = [
            'id', 'cv_data', 'ats_score', 'overall_score',
            'content_quality_score', 'formatting_score',
            'strengths', 'weaknesses', 'suggestions',
            'formatting_issues', 'missing_keywords', 'missing_sections',
            'detailed_checks',
            'analysis_status', 'analysis_error', 'analyzed_at', 'updated_at'
        ]
        read_only_fields = ['id', 'cv_data', 'analysis_status', 'analysis_error', 'analyzed_at', 'updated_at']


class CVVersionSerializer(serializers.ModelSerializer):
    """Serializer for CVVersion model"""
    
    class Meta:
        model = CVVersion
        fields = [
            'id', 'cv', 'version_number', 'title', 'description',
            'version_type', 'optimization_target', 'optimized_text',
            'keywords_added', 'changes_made', 'ats_score',
            'overall_score', 'is_current', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'cv', 'created_at', 'updated_at']


class CVVersionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new CV versions"""
    
    class Meta:
        model = CVVersion
        fields = [
            'version_number', 'title', 'description',
            'version_type', 'optimization_target', 'optimized_text',
            'keywords_added', 'changes_made', 'ats_score',
            'overall_score', 'is_current'
        ]
    
    def validate_version_number(self, value):
        """Validate version number is unique for this CV"""
        cv_id = self.context.get('cv_id')
        if cv_id:
            if CVVersion.objects.filter(cv_id=cv_id, version_number=value).exists():
                raise serializers.ValidationError(
                    f"Version {value} already exists for this CV"
                )
        return value


class JobDescriptionSerializer(serializers.ModelSerializer):
    """Serializer for JobDescription model"""
    
    class Meta:
        model = JobDescription
        fields = [
            'id', 'user', 'title', 'company', 'location', 'job_url',
            'description', 'requirements', 'responsibilities',
            'qualifications', 'benefits', 'keywords',
            'required_skills', 'preferred_skills',
            'is_parsed', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'keywords', 'required_skills',
            'preferred_skills', 'is_parsed', 'created_at', 'updated_at'
        ]


class CVDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for CV including related data"""
    data = CVDataSerializer(read_only=True)
    analysis = CVAnalysisSerializer(source='data.analysis', read_only=True)
    versions = serializers.SerializerMethodField()
    
    class Meta:
        model = CV
        fields = [
            'id', 'title', 'file', 'original_filename',
            'file_type', 'file_size', 'is_parsed', 'is_analyzed',
            'is_active', 'uploaded_at', 'updated_at',
            'data', 'analysis', 'versions'
        ]
        read_only_fields = [
            'id', 'file_type', 'file_size', 'is_parsed',
            'is_analyzed', 'uploaded_at', 'updated_at'
        ]
    
    def get_versions(self, obj):
        """Get CV versions"""
        versions = obj.versions.all()
        return CVVersionSerializer(versions, many=True).data


class CVListSerializer(serializers.ModelSerializer):
    """Serializer for listing CVs (less detailed)"""
    file_url = serializers.SerializerMethodField()
    has_data = serializers.BooleanField(source='is_parsed', read_only=True)
    has_analysis = serializers.BooleanField(source='is_analyzed', read_only=True)
    versions_count = serializers.SerializerMethodField()
    
    class Meta:
        model = CV
        fields = [
            'id', 'title', 'file_url', 'original_filename',
            'file_type', 'file_size', 'has_data', 'has_analysis',
            'versions_count', 'is_active', 'uploaded_at', 'updated_at'
        ]
    
    def get_file_url(self, obj):
        """Get the URL for the CV file"""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None
    
    def get_versions_count(self, obj):
        """Get count of versions"""
        return obj.versions.count()