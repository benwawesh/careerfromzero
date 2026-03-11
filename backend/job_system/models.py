"""
Job System Models
Handles job listings, applications, and matching
"""

from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class JobCategory(models.Model):
    """Job categories for organizing jobs"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=50, blank=True, null=True)  # Emoji or icon name
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'Job Categories'
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.name.lower().replace(' ', '-').replace('/', '-')
        super().save(*args, **kwargs)


class JobCache(models.Model):
    """Cache search results for faster repeated queries"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    search_key = models.CharField(max_length=500, unique=True)  # Hash of search params
    search_params = models.JSONField()  # Store original search parameters
    results = models.JSONField()  # Cached job results
    result_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['search_key']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"Cache: {self.search_key} ({self.result_count} results)"
    
    def is_valid(self):
        """Check if cache is still valid"""
        from django.utils import timezone
        return timezone.now() < self.expires_at


class UserApplicationPreference(models.Model):
    """User preferences for auto-apply"""
    
    APPROVAL_CHOICES = [
        ('always', 'Always Require Approval'),
        ('after_trust', 'After Trust (Require X approvals first)'),
        ('never', 'Never Require Approval'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='auto_apply_preferences')
    
    # Approval Settings
    approval_mode = models.CharField(max_length=20, choices=APPROVAL_CHOICES, default='always')
    approvals_required_for_trust = models.PositiveIntegerField(default=10)  # Number of approvals before auto
    
    # Match Score Threshold
    min_match_score = models.DecimalField(max_digits=5, decimal_places=2, default=70.00)  # Minimum match score to auto-approve
    
    # Job Preferences
    preferred_job_types = models.JSONField(default=list, blank=True)  # List of job types
    preferred_locations = models.JSONField(default=list, blank=True)  # List of locations
    min_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    blacklisted_companies = models.JSONField(default=list, blank=True)  # Companies to avoid
    
    # Apply Settings
    apply_immediately = models.BooleanField(default=True)
    apply_rate_limit = models.PositiveIntegerField(default=10)  # Applications per hour
    apply_start_time = models.TimeField(null=True, blank=True)  # Start applying at
    apply_end_time = models.TimeField(null=True, blank=True)  # Stop applying at
    
    # Learning
    trust_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)  # 0-100
    total_approvals = models.PositiveIntegerField(default=0)
    total_rejections = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User Auto-Apply Preferences'
    
    def __str__(self):
        return f"{self.user.username} - {self.approval_mode}"
    
    @property
    def can_auto_approve(self):
        """Check if user can auto-approve based on trust"""
        if self.approval_mode == 'always':
            return False
        elif self.approval_mode == 'never':
            return True
        elif self.approval_mode == 'after_trust':
            return self.approvals_required_for_trust <= self.total_approvals
        return False


class Job(models.Model):
    """Job listing from various sources"""
    
    SOURCE_CHOICES = [
        ('manual', 'Manual Entry'),
        # International boards (via python-jobspy)
        ('linkedin', 'LinkedIn'),
        ('indeed', 'Indeed'),
        ('glassdoor', 'Glassdoor'),
        ('ziprecruiter', 'ZipRecruiter'),
        # Free remote APIs
        ('adzuna', 'Adzuna'),
        ('remotive', 'Remotive'),
        ('arbeitnow', 'Arbeitnow'),
        ('jobicy', 'Jobicy'),
        ('remoteok', 'RemoteOK'),
        ('themuse', 'The Muse'),
        # Kenyan / African boards
        ('brightermonday', 'BrighterMonday'),
        ('fuzu', 'Fuzu'),
        ('kenyajob', 'KenyaJob'),
        ('myjobmag', 'MyJobMag'),
        ('jobwebkenya', 'Jobwebkenya'),
        ('ngojobs', 'NGO Jobs Africa'),
        ('corporatestaffing', 'Corporate Staffing KE'),
        ('nationkenya', 'Nation Kenya'),
        ('jobberman', 'Jobberman (Nigeria)'),
        ('career24', 'Career24 (South Africa)'),
        # Additional free APIs / RSS
        ('indeedrss', 'Indeed RSS'),
        ('weworkremotely', 'We Work Remotely'),
        ('scraped', 'Web Scraped'),
    ]
    
    JOB_TYPE_CHOICES = [
        ('full_time', 'Full-time'),
        ('part_time', 'Part-time'),
        ('contract', 'Contract'),
        ('internship', 'Internship'),
        ('freelance', 'Freelance'),
        ('remote', 'Remote'),
    ]
    
    EXPERIENCE_CHOICES = [
        ('entry', 'Entry Level'),
        ('entry_level', 'Entry Level'),
        ('mid', 'Mid Level'),
        ('mid_level', 'Mid Level'),
        ('senior', 'Senior Level'),
        ('senior_level', 'Senior Level'),
        ('lead', 'Lead/Manager'),
        ('executive', 'Executive'),
    ]
    
    # Core Job Information
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    description = models.TextField()
    
    # Source Information
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='manual')
    external_id = models.CharField(max_length=200, blank=True, null=True)
    job_url = models.URLField(max_length=500, blank=True, null=True)
    
    # Job Details
    location = models.CharField(max_length=200, blank=True, null=True)
    salary_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    salary_currency = models.CharField(max_length=10, default='USD', blank=True)
    job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES, blank=True, null=True)
    experience_level = models.CharField(max_length=20, choices=EXPERIENCE_CHOICES, blank=True, null=True)
    
    # Requirements
    requirements = models.TextField(blank=True, null=True)
    qualifications = models.TextField(blank=True, null=True)
    benefits = models.TextField(blank=True, null=True)
    
    # AI-Parsed Data
    skills_required = models.JSONField(default=list, blank=True)  # List of required skills
    skills_optional = models.JSONField(default=list, blank=True)  # List of preferred skills
    responsibilities = models.JSONField(default=list, blank=True)  # List of responsibilities
    
    # Embedded vector for semantic search
    embedding = models.JSONField(null=True, blank=True)
    
    # Company Logo
    company_logo_url = models.URLField(max_length=500, blank=True, null=True)
    
    # Metadata
    posted_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Tracking
    view_count = models.PositiveIntegerField(default=0)
    application_count = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)  # Featured jobs displayed prominently
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['company']),
            models.Index(fields=['location']),
            models.Index(fields=['job_type']),
            models.Index(fields=['experience_level']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.title} at {self.company}"
    
    @property
    def salary_range(self):
        """Get formatted salary range"""
        if self.salary_min and self.salary_max:
            return f"{self.salary_currency} {self.salary_min:,.0f} - {self.salary_max:,.0f}"
        elif self.salary_min:
            return f"{self.salary_currency} {self.salary_min:,.0f}+"
        elif self.salary_max:
            return f"Up to {self.salary_currency} {self.salary_max:,.0f}"
        return "Not specified"


class AutoApplicationBatch(models.Model):
    """Batch of auto-applications for approval"""
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('applying', 'Applying'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='auto_application_batches')
    cv_version = models.ForeignKey(
        'cv_builder.CVVersion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='auto_application_batches'
    )
    
    # Batch Information
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='draft')
    name = models.CharField(max_length=200, blank=True, null=True)
    
    # Search Parameters (what jobs were matched)
    search_query = models.CharField(max_length=200, blank=True, null=True)
    search_location = models.CharField(max_length=200, blank=True, null=True)
    search_filters = models.JSONField(default=dict, blank=True)
    
    # Statistics
    total_jobs = models.PositiveIntegerField(default=0)
    approved_jobs = models.PositiveIntegerField(default=0)
    rejected_jobs = models.PositiveIntegerField(default=0)
    successful_applications = models.PositiveIntegerField(default=0)
    failed_applications = models.PositiveIntegerField(default=0)
    
    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Error handling
    error_message = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['created_at']),
        ]
        verbose_name = 'Auto-Application Batch'
    
    def __str__(self):
        return f"{self.user.username} - Batch {self.id} ({self.status})"
    
    @property
    def progress_percentage(self):
        """Get progress percentage"""
        if self.total_jobs == 0:
            return 0
        applied = self.successful_applications + self.failed_applications
        return int((applied / self.total_jobs) * 100)


class AutoApplicationItem(models.Model):
    """Individual application in a batch"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('applying', 'Applying'),
        ('applied', 'Applied'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey('AutoApplicationBatch', on_delete=models.CASCADE, related_name='items')
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='auto_application_items')
    
    # User Approval
    user_approval_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Application Execution
    application_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Match Information
    match_score = models.DecimalField(max_digits=5, decimal_places=2)
    matched_skills = models.JSONField(default=list, blank=True)
    missing_skills = models.JSONField(default=list, blank=True)
    
    # Generated Content
    custom_cv = models.JSONField(null=True, blank=True)  # AI-generated custom CV
    custom_cover_letter = models.TextField(blank=True, null=True)  # AI-generated cover letter
    
    # User Edits
    edited_cv = models.JSONField(null=True, blank=True)  # User-edited CV
    edited_cover_letter = models.TextField(blank=True, null=True)  # User-edited cover letter
    
    # Execution Details
    application_url = models.URLField(max_length=500, blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    
    # JobApplication link (after successful application)
    job_application = models.ForeignKey(
        'JobApplication',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='auto_application_item'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-match_score']
        unique_together = ['batch', 'job']
        indexes = [
            models.Index(fields=['batch', 'user_approval_status']),
            models.Index(fields=['match_score']),
        ]
        verbose_name = 'Auto-Application Item'
    
    def __str__(self):
        return f"{self.job.title} - {self.user_approval_status}"
    
    @property
    def final_cv(self):
        """Get final CV (user edited or AI generated)"""
        return self.edited_cv if self.edited_cv else self.custom_cv
    
    @property
    def final_cover_letter(self):
        """Get final cover letter (user edited or AI generated)"""
        return self.edited_cover_letter if self.edited_cover_letter else self.custom_cover_letter


class SavedJob(models.Model):
    """Jobs saved/bookmarked by users"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_jobs')
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='saved_by')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'job']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.job.title}"


class JobApplication(models.Model):
    """Job applications tracking"""
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('applied', 'Applied'),
        ('under_review', 'Under Review'),
        ('screening', 'Phone Screening'),
        ('interview', 'Interview'),
        ('technical', 'Technical Interview'),
        ('offer', 'Offer Received'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
        ('hired', 'Hired'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    
    # CV used for application
    cv_version = models.ForeignKey(
        'cv_builder.CVVersion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='applications'
    )
    
    # Application Mode (Manual or Auto)
    MODE_CHOICES = [
        ('manual', 'Manual'),
        ('auto', 'Auto-Apply'),
    ]
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default='manual')
    
    # Application Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Application Details
    cover_letter = models.TextField(blank=True, null=True)
    application_date = models.DateField(null=True, blank=True)
    application_url = models.URLField(max_length=500, blank=True, null=True)
    
    # Interview Information
    interview_date = models.DateTimeField(null=True, blank=True)
    interview_type = models.CharField(max_length=50, blank=True, null=True)
    interview_notes = models.TextField(blank=True, null=True)
    
    # Follow-up
    follow_up_date = models.DateField(null=True, blank=True)
    follow_up_completed = models.BooleanField(default=False)
    
    # Notes and Tracking
    notes = models.TextField(blank=True, null=True)
    reminders = models.JSONField(default=list, blank=True)  # List of reminder dates/notes
    
    # Match Score (from CV matching)
    match_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    matched_skills = models.JSONField(default=list, blank=True)
    missing_skills = models.JSONField(default=list, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['application_date']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.job.title} ({self.status})"


class JobMatch(models.Model):
    """AI-powered job matching results"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='job_matches')
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='matches')
    cv_version = models.ForeignKey(
        'cv_builder.CVVersion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='job_matches'
    )
    
    # Match Scores
    overall_match = models.DecimalField(max_digits=5, decimal_places=2)
    skill_match = models.DecimalField(max_digits=5, decimal_places=2)
    experience_match = models.DecimalField(max_digits=5, decimal_places=2)
    location_match = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Detailed Analysis
    matched_skills = models.JSONField(default=list)
    missing_skills = models.JSONField(default=list)
    additional_skills = models.JSONField(default=list, blank=True)
    
    # Recommendations
    suggestions = models.JSONField(default=list)
    improvement_ideas = models.TextField(blank=True, null=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'job', 'cv_version']
        ordering = ['-overall_match']
        indexes = [
            models.Index(fields=['user', 'overall_match']),
            models.Index(fields=['overall_match']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.job.title} ({self.overall_match}%)"


class JobSearch(models.Model):
    """Saved job search queries"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='job_searches')
    
    # Search Parameters
    query = models.CharField(max_length=200, blank=True, null=True)
    location = models.CharField(max_length=200, blank=True, null=True)
    job_type = models.CharField(max_length=20, blank=True, null=True)
    experience_level = models.CharField(max_length=20, blank=True, null=True)
    
    # Advanced Filters
    salary_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    skills = models.JSONField(default=list, blank=True)  # List of required skills
    
    # Source Filters
    sources = models.JSONField(default=list, blank=True)  # List of job sources
    
    # Metadata
    name = models.CharField(max_length=100, blank=True, null=True)  # Custom name for saved search
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.name or self.query or 'Search'}"