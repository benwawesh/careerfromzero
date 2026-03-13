import uuid
from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL


class GuidanceSession(models.Model):
    LEVEL_CHOICES = [
        ('beginner', 'Complete Beginner'),
        ('some_experience', 'Some Experience'),
        ('intermediate', 'Intermediate'),
        ('experienced', 'Experienced'),
    ]

    STATUS_CHOICES = [
        ('onboarding', 'Onboarding'),
        ('active', 'Active'),
        ('complete', 'Complete'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='guidance_sessions')
    goal = models.TextField()  # e.g. "Become a software engineer"
    current_level = models.CharField(max_length=20, choices=LEVEL_CHOICES, blank=True)
    time_commitment = models.CharField(max_length=100, blank=True)  # e.g. "2 hours per day"
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='onboarding')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} → {self.goal[:50]} ({self.status})"


class GuidanceTopic(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('complete', 'Complete'),
    ]

    session = models.ForeignKey(GuidanceSession, on_delete=models.CASCADE, related_name='topics')
    order = models.IntegerField()
    title = models.CharField(max_length=200)
    description = models.TextField()
    estimated_days = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    score = models.FloatField(null=True, blank=True)
    passed = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.session} — {self.order}. {self.title}"


class GuidanceMessage(models.Model):
    ROLE_CHOICES = [
        ('alex', 'Alex'),
        ('user', 'User'),
    ]

    session = models.ForeignKey(GuidanceSession, on_delete=models.CASCADE, related_name='messages')
    topic = models.ForeignKey(GuidanceTopic, on_delete=models.SET_NULL, null=True, blank=True, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.role}] {self.content[:60]}"
