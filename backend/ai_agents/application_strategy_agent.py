"""
Application Strategy AI Agent
Learns user preferences and optimizes applications
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .base_agent import BaseJobAgent
from users.models import User
from job_system.models import (
    AutoApplicationBatch, AutoApplicationItem, UserApplicationPreference
)
from django.db.models import Count, Avg
import json

if TYPE_CHECKING:
    from job_system.models import Job


class ApplicationStrategyAgent(BaseJobAgent):
    """AI agent for learning user preferences and optimizing applications"""
    
    def __init__(self):
        super().__init__()
        self.model = "claude-haiku-4-5-20251001"  # Claude API
    
    def analyze_user_preferences(self, user: User) -> dict:
        """
        Analyze user's approval patterns and preferences
        
        Args:
            user: User object
        
        Returns:
            dict with preferences and predictions
        """
        # Get or create preferences
        prefs, created = UserApplicationPreference.objects.get_or_create(
            user=user,
            defaults={
                'approval_mode': 'always',
                'min_match_score': 70.00,
                'approvals_required_for_trust': 10
            }
        )
        
        # Analyze past batches
        batches = AutoApplicationBatch.objects.filter(user=user)
        
        if batches.count() == 0:
            # No history yet
            return {
                'preferences': self._serialize_preferences(prefs),
                'predictions': {
                    'success_probability': 0.5,
                    'best_apply_time': '9:00 AM - 11:00 AM',
                    'recommended_apply_rate': '5 per day'
                },
                'trust_score': 0.0,
                'suggestions': [
                    "Approve some applications to build trust",
                    "Set your preferred job types",
                    "Set your preferred locations"
                ]
            }
        
        # Calculate statistics
        total_items = AutoApplicationItem.objects.filter(batch__user=user).count()
        approved_items = AutoApplicationItem.objects.filter(
            batch__user=user,
            user_approval_status='approved'
        ).count()
        rejected_items = AutoApplicationItem.objects.filter(
            batch__user=user,
            user_approval_status='rejected'
        ).count()
        
        # Update preferences stats
        prefs.total_approvals = approved_items
        prefs.total_rejections = rejected_items
        
        # Calculate trust score
        if total_items > 0:
            approval_rate = approved_items / total_items
            prefs.trust_score = min(100, approval_rate * 100)
        else:
            prefs.trust_score = 0.0
        
        prefs.save()
        
        # Analyze approved jobs
        approved_jobs = AutoApplicationItem.objects.filter(
            batch__user=user,
            user_approval_status='approved'
        ).select_related('job')
        
        # Extract patterns
        patterns = self._extract_patterns(approved_jobs)
        
        # Generate predictions
        predictions = self._generate_predictions(patterns, prefs)
        
        return {
            'preferences': self._serialize_preferences(prefs),
            'patterns': patterns,
            'predictions': predictions,
            'trust_score': float(prefs.trust_score),
            'suggestions': self._generate_suggestions(patterns, prefs)
        }
    
    def _extract_patterns(self, approved_items) -> dict:
        """Extract patterns from approved applications"""
        
        job_types = {}
        locations = {}
        companies = []
        min_match_scores = []
        
        for item in approved_items:
            job = item.job
            
            # Job types
            if job.job_type:
                job_types[job.job_type] = job_types.get(job.job_type, 0) + 1
            
            # Locations
            if job.location:
                locations[job.location] = locations.get(job.location, 0) + 1
            
            # Companies
            companies.append(job.company)
            
            # Match scores
            if item.match_score:
                min_match_scores.append(float(item.match_score))
        
        # Find most common
        preferred_job_types = sorted(
            job_types.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        preferred_locations = sorted(
            locations.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        avg_min_match = sum(min_match_scores) / len(min_match_scores) if min_match_scores else 70.0
        
        return {
            'preferred_job_types': [jt[0] for jt in preferred_job_types],
            'preferred_locations': [loc[0] for loc in preferred_locations],
            'blacklisted_companies': [],  # User can add manually
            'avg_min_match_score': avg_min_match
        }
    
    def _generate_predictions(self, patterns: dict, prefs: UserApplicationPreference) -> dict:
        """Generate predictions based on patterns"""
        
        success_probability = min(0.9, 0.5 + (prefs.trust_score / 200))
        
        return {
            'success_probability': round(success_probability, 2),
            'best_apply_time': '9:00 AM - 11:00 AM',
            'recommended_apply_rate': '10 per day',
            'likely_success': prefs.trust_score > 70
        }
    
    def _generate_suggestions(self, patterns: dict, prefs: UserApplicationPreference) -> list:
        """Generate suggestions for user"""
        
        suggestions = []
        
        if prefs.trust_score < 50:
            suggestions.append("Approve more applications to build trust for auto-apply")
        
        if len(patterns.get('preferred_job_types', [])) == 0:
            suggestions.append("Set your preferred job types for better matching")
        
        if len(patterns.get('preferred_locations', [])) == 0:
            suggestions.append("Set your preferred locations for better matching")
        
        if patterns.get('avg_min_match_score', 70) < 80:
            suggestions.append("Consider improving your CV to get better match scores")
        
        if len(suggestions) == 0:
            suggestions.append("You're doing great! Your profile is well optimized.")
        
        return suggestions
    
    def _serialize_preferences(self, prefs: UserApplicationPreference) -> dict:
        """Serialize preferences object"""
        return {
            'approval_mode': prefs.approval_mode,
            'min_match_score': float(prefs.min_match_score),
            'preferred_job_types': prefs.preferred_job_types,
            'preferred_locations': prefs.preferred_locations,
            'min_salary': float(prefs.min_salary) if prefs.min_salary else None,
            'blacklisted_companies': prefs.blacklisted_companies,
            'apply_immediately': prefs.apply_immediately,
            'apply_rate_limit': prefs.apply_rate_limit
        }
    
    def should_auto_approve(self, user, job,
                          match_score: float) -> bool:
        """
        Determine if a job should be auto-approved
        
        Args:
            user: User object
            job: Job object
            match_score: Match score (0-100)
        
        Returns:
            bool - True if should auto-approve
        """
        # Import here to avoid circular dependency
        from job_system.models import UserApplicationPreference
        
        # Get preferences
        prefs = UserApplicationPreference.objects.filter(user=user).first()
        
        if not prefs:
            return False
        
        # Check if user can auto-approve
        if not prefs.can_auto_approve:
            return False
        
        # Check match score threshold
        if match_score < prefs.min_match_score:
            return False
        
        # Check blacklisted companies
        if job.company in prefs.blacklisted_companies:
            return False
        
        # Check job type preferences
        if (prefs.preferred_job_types and 
            job.job_type not in prefs.preferred_job_types):
            return False
        
        # Check location preferences
        if (prefs.preferred_locations and 
            job.location not in prefs.preferred_locations and 
            'remote' not in job.location.lower()):
            return False
        
        # Check salary minimum
        if prefs.min_salary and job.salary_min:
            if job.salary_min < prefs.min_salary:
                return False
        
        return True
    
    def update_preferences(self, user: User, preferences: dict) -> UserApplicationPreference:
        """
        Update user's auto-apply preferences
        
        Args:
            user: User object
            preferences: dict of preferences to update
        
        Returns:
            Updated UserApplicationPreference
        """
        prefs, created = UserApplicationPreference.objects.get_or_create(
            user=user
        )
        
        # Update fields
        if 'approval_mode' in preferences:
            prefs.approval_mode = preferences['approval_mode']
        if 'min_match_score' in preferences:
            prefs.min_match_score = preferences['min_match_score']
        if 'approvals_required_for_trust' in preferences:
            prefs.approvals_required_for_trust = preferences['approvals_required_for_trust']
        if 'preferred_job_types' in preferences:
            prefs.preferred_job_types = preferences['preferred_job_types']
        if 'preferred_locations' in preferences:
            prefs.preferred_locations = preferences['preferred_locations']
        if 'min_salary' in preferences:
            prefs.min_salary = preferences['min_salary']
        if 'blacklisted_companies' in preferences:
            prefs.blacklisted_companies = preferences['blacklisted_companies']
        if 'apply_immediately' in preferences:
            prefs.apply_immediately = preferences['apply_immediately']
        if 'apply_rate_limit' in preferences:
            prefs.apply_rate_limit = preferences['apply_rate_limit']
        if 'apply_start_time' in preferences:
            prefs.apply_start_time = preferences['apply_start_time']
        if 'apply_end_time' in preferences:
            prefs.apply_end_time = preferences['apply_end_time']
        
        prefs.save()
        
        return prefs