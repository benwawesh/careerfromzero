import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

LEVEL_CHOICES = [
    ('junior', 'Junior / Entry Level'),
    ('mid', 'Mid Level'),
    ('senior', 'Senior Level'),
    ('manager', 'Managerial / Team Lead'),
    ('director', 'Director / Executive'),
]

TYPE_CHOICES = [
    ('hr', 'HR / Behavioural'),
    ('technical', 'Technical'),
    ('mixed', 'Mixed'),
]

STATUS_CHOICES = [
    ('intro', 'Introduction'),
    ('phase1_test', 'Phase 1 - Written Test'),
    ('phase1_review', 'Phase 1 - Review'),
    ('phase2_interview', 'Phase 2 - Interview'),
    ('phase2_review', 'Phase 2 - Review'),
    ('phase3_interview', 'Phase 3 - Deep Dive'),
    ('phase3_review', 'Phase 3 - Review'),
    ('complete', 'Complete'),
]

class InterviewSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='interview_sessions')
    career_goal = models.TextField()  # job description OR career path
    experience_level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    interview_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    mode = models.CharField(max_length=10, default='text')  # text or voice
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='intro')
    phase1_score = models.FloatField(null=True, blank=True)
    phase2_score = models.FloatField(null=True, blank=True)
    phase3_score = models.FloatField(null=True, blank=True)
    overall_score = models.FloatField(null=True, blank=True)
    phase1_passed = models.BooleanField(null=True, blank=True)
    phase2_passed = models.BooleanField(null=True, blank=True)
    phase3_passed = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

QUESTION_TYPE_CHOICES = [
    ('multiple_choice', 'Multiple Choice'),
    ('short_answer', 'Short Answer'),
    ('situational', 'Situational'),
    ('behavioural', 'Behavioural'),
    ('technical', 'Technical'),
]

class InterviewQuestion(models.Model):
    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name='questions')
    phase = models.IntegerField()  # 1, 2, or 3
    order = models.IntegerField()
    question_type = models.CharField(max_length=50, choices=QUESTION_TYPE_CHOICES)
    question_text = models.TextField()
    options = models.JSONField(null=True, blank=True)  # list of strings for multiple choice
    correct_answer = models.TextField(null=True, blank=True)
    ideal_answer_guide = models.TextField(null=True, blank=True)
    section = models.CharField(max_length=50, null=True, blank=True)  # e.g. "Written Communication"

    class Meta:
        ordering = ['phase', 'order']

class InterviewAnswer(models.Model):
    question = models.OneToOneField(InterviewQuestion, on_delete=models.CASCADE, related_name='answer')
    answer_text = models.TextField()
    score = models.FloatField(null=True, blank=True)  # 0-10
    feedback = models.TextField(null=True, blank=True)
    is_correct = models.BooleanField(null=True, blank=True)
    needs_review = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)

class ReviewMessage(models.Model):
    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name='review_messages')
    phase = models.IntegerField()
    role = models.CharField(max_length=10)  # 'alex' or 'user'
    content = models.TextField()
    question_ref = models.ForeignKey(InterviewQuestion, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
