from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import CustomUserManager


class User(AbstractUser):
    objects = CustomUserManager()
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=200, blank=True, null=True)
    linkedin_url = models.URLField(blank=True, null=True)
    github_url = models.URLField(blank=True, null=True)
    portfolio_url = models.URLField(blank=True, null=True)
    
    # Preferences
    job_search_preferences = models.JSONField(default=dict, blank=True)
    career_goals = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def save(self, *args, **kwargs):
        if not self.username:
            base = self.email.split('@')[0]
            username = base
            counter = 1
            qs = User.objects if self.pk is None else User.objects.exclude(pk=self.pk)
            while qs.filter(username=username).exists():
                username = f"{base}{counter}"
                counter += 1
            self.username = username
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return f"{self.email}"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"