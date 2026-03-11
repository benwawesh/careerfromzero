"""
CV Builder Models
Handles CV upload, storage, parsing, and versioning
"""

from django.db import models
from django.contrib.auth import get_user_model
import uuid
import os

User = get_user_model()


def get_cv_upload_path(instance, filename):
    """Generate unique upload path for CV files"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('cvs', str(instance.user.id), filename)


class CV(models.Model):
    """
    Main CV model for storing uploaded CV files
    """
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='cvs'
    )
    title = models.CharField(
        max_length=200,
        help_text="Title for this CV (e.g., 'Software Engineer CV')"
    )
    file = models.FileField(
        upload_to=get_cv_upload_path,
        null=True,
        blank=True,
        help_text="CV file (PDF or DOCX)"
    )
    original_filename = models.CharField(max_length=255, blank=True)
    is_temporary = models.BooleanField(
        default=False,
        help_text="True if CV was created from manual entry, not file upload"
    )
    file_type = models.CharField(
        max_length=10,
        help_text="File type: PDF or DOCX"
    )
    file_size = models.PositiveIntegerField(
        help_text="File size in bytes"
    )
    
    # Status tracking
    is_parsed = models.BooleanField(default=False, help_text="Has CV been parsed?")
    is_analyzed = models.BooleanField(default=False, help_text="Has CV been analyzed?")
    is_active = models.BooleanField(default=True, help_text="Soft delete flag")
    
    # Metadata
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = "CV"
        verbose_name_plural = "CVs"
    
    def __str__(self):
        return f"{self.title} - {self.user.email}"
    
    def delete(self, *args, **kwargs):
        """Soft delete - mark as inactive instead of actual deletion"""
        self.is_active = False
        self.save()
    
    def hard_delete(self, *args, **kwargs):
        """Actually delete the CV and file"""
        # Delete file from storage
        if self.file and os.path.exists(self.file.path):
            os.remove(self.file.path)
        super().delete(*args, **kwargs)


class CVData(models.Model):
    """
    Parsed and structured data from CV
    """
    cv = models.OneToOneField(
        CV,
        on_delete=models.CASCADE,
        related_name='data'
    )
    
    # Raw extracted text
    raw_text = models.TextField(help_text="Full text extracted from CV")
    
    # Contact information
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    location = models.CharField(max_length=200, null=True, blank=True)
    linkedin_url = models.URLField(null=True, blank=True)
    github_url = models.URLField(null=True, blank=True)
    website_url = models.URLField(null=True, blank=True)
    
    # CV sections
    summary = models.TextField(
        null=True, 
        blank=True,
        help_text="Professional summary/objective"
    )
    
    # JSON fields for complex data
    skills = models.JSONField(
        default=list,
        help_text="List of skills: ['Python', 'Django', 'React']"
    )
    
    experience = models.JSONField(
        default=list,
        help_text="List of experience objects with company, role, dates, etc."
    )
    
    education = models.JSONField(
        default=list,
        help_text="List of education objects with institution, degree, dates, etc."
    )
    
    projects = models.JSONField(
        default=list,
        help_text="List of project objects with name, description, tech stack, etc."
    )
    
    certifications = models.JSONField(
        default=list,
        help_text="List of certifications"
    )
    
    languages = models.JSONField(
        default=list,
        help_text="List of languages spoken"
    )
    
    interests = models.JSONField(
        default=list,
        help_text="List of professional interests/hobbies"
    )
    
    # Parsing metadata
    parsing_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed')
        ],
        default='pending'
    )
    parsing_error = models.TextField(null=True, blank=True)
    
    extracted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "CV Data"
        verbose_name_plural = "CV Data"
    
    def __str__(self):
        return f"Data for {self.cv.title}"


class CVAnalysis(models.Model):
    """
    AI-powered analysis results for a CV
    """
    cv_data = models.OneToOneField(
        CVData,
        on_delete=models.CASCADE,
        related_name='analysis'
    )
    
    # Scores
    ats_score = models.IntegerField(
        help_text="ATS compatibility score (0-100)",
        default=0
    )
    overall_score = models.IntegerField(
        help_text="Overall CV quality score (0-100)",
        default=0
    )
    content_quality_score = models.IntegerField(
        help_text="Content quality score (0-100)",
        default=0
    )
    formatting_score = models.IntegerField(
        help_text="Formatting score (0-100)",
        default=0
    )
    
    # AI-generated feedback
    strengths = models.JSONField(
        default=list,
        help_text="List of CV strengths"
    )
    weaknesses = models.JSONField(
        default=list,
        help_text="List of areas for improvement"
    )
    suggestions = models.JSONField(
        default=list,
        help_text="AI-generated improvement suggestions"
    )
    
    # Detailed analysis
    formatting_issues = models.JSONField(
        default=list,
        help_text="List of formatting issues found"
    )
    missing_keywords = models.JSONField(
        default=list,
        help_text="Common keywords missing from CV"
    )
    missing_sections = models.JSONField(
        default=list,
        help_text="Important sections missing from CV"
    )
    
    # Analysis metadata
    analysis_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed')
        ],
        default='pending'
    )
    analysis_error = models.TextField(null=True, blank=True)
    
    analyzed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "CV Analysis"
        verbose_name_plural = "CV Analyses"
    
    def __str__(self):
        return f"Analysis for {self.cv_data.cv.title} (Score: {self.overall_score})"


class CVVersion(models.Model):
    """
    Track different versions of a CV (original, optimized, tailored, etc.)
    """
    cv = models.ForeignKey(
        CV,
        on_delete=models.CASCADE,
        related_name='versions'
    )
    
    version_number = models.PositiveIntegerField()
    title = models.CharField(
        max_length=200,
        help_text="Version title (e.g., 'Version 2 - Optimized for Google')"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of changes in this version"
    )
    
    # Version type
    version_type = models.CharField(
        max_length=20,
        choices=[
            ('original', 'Original'),
            ('ats_optimized', 'ATS Optimized'),
            ('job_tailored', 'Job Tailored'),
            ('custom', 'Custom')
        ],
        default='original'
    )
    
    # Target (for job-tailored versions)
    optimization_target = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="Target job or company (e.g., 'Google SWE')"
    )
    
    # Optimized content
    optimized_text = models.TextField(
        help_text="Full text of optimized CV"
    )
    
    # Tracking changes
    keywords_added = models.JSONField(
        default=list,
        help_text="Keywords added in this version"
    )
    changes_made = models.JSONField(
        default=list,
        help_text="List of changes made in this version"
    )
    
    # Metrics
    ats_score = models.IntegerField(
        null=True,
        blank=True,
        help_text="ATS score for this version"
    )
    overall_score = models.IntegerField(
        null=True,
        blank=True,
        help_text="Overall score for this version"
    )
    
    # Version management
    is_current = models.BooleanField(
        default=False,
        help_text="Is this the current active version?"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-version_number']
        unique_together = ['cv', 'version_number']
        verbose_name = "CV Version"
        verbose_name_plural = "CV Versions"
    
    def __str__(self):
        return f"{self.cv.title} - v{self.version_number} ({self.title})"
    
    def save(self, *args, **kwargs):
        # Auto-set is_current to False for other versions if this one is True
        if self.is_current:
            CVVersion.objects.filter(
                cv=self.cv
            ).exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)


class JobDescription(models.Model):
    """
    Store job descriptions for CV matching and tailoring
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='job_descriptions'
    )
    
    # Job details
    title = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    location = models.CharField(max_length=200, null=True, blank=True)
    job_url = models.URLField(null=True, blank=True)
    
    # Job content
    description = models.TextField(help_text="Full job description")
    requirements = models.TextField(
        null=True,
        blank=True,
        help_text="Job requirements section"
    )
    responsibilities = models.TextField(
        null=True,
        blank=True,
        help_text="Job responsibilities section"
    )
    qualifications = models.TextField(
        null=True,
        blank=True,
        help_text="Job qualifications section"
    )
    benefits = models.TextField(
        null=True,
        blank=True,
        help_text="Job benefits section"
    )
    
    # Parsed data
    keywords = models.JSONField(
        default=list,
        help_text="Extracted keywords from job description"
    )
    required_skills = models.JSONField(
        default=list,
        help_text="Required skills from job description"
    )
    preferred_skills = models.JSONField(
        default=list,
        help_text="Preferred skills from job description"
    )
    
    # Status
    is_parsed = models.BooleanField(default=False)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Job Description"
        verbose_name_plural = "Job Descriptions"
    
    def __str__(self):
        return f"{self.title} at {self.company}"