"""
Job Matcher AI Agent
Matches user's CV to job postings and calculates match scores
"""

from .base_agent import BaseJobAgent
from users.models import User
from cv_builder.models import CVVersion
from job_system.models import Job, JobMatch
import json


class JobMatcherAgent(BaseJobAgent):
    """AI agent for matching CVs to job postings"""
    
    def __init__(self):
        super().__init__()
        self.model = "claude-haiku-4-5-20251001"  # Claude API
    
    def calculate_match(self, user: User, job: Job, cv_version: CVVersion = None) -> dict:
        """
        Calculate match score between user's CV and job
        
        Args:
            user: User object
            job: Job object
            cv_version: CVVersion object (optional)
        
        Returns:
            dict with match scores and analysis
        """
        # Get CV content
        if not cv_version:
            cv_version = CVVersion.objects.filter(
                cv__user=user,
                is_current=True
            ).first()

        if not cv_version:
            return {
                'error': 'No active CV found',
                'overall_match': 0
            }
        
        # Build analysis prompt
        prompt = self._build_match_prompt(cv_version, job)
        
        # Get AI response using base class method
        response = self.generate_response(prompt)
        
        # Parse response
        try:
            match_data = self._parse_match_response(response)
        except Exception as e:
            print(f"Error parsing match response: {e}")
            match_data = self._fallback_match_calculation(cv_version, job)
        
        return match_data
    
    def _build_match_prompt(self, cv_version: CVVersion, job: Job) -> str:
        """Build prompt for job matching"""
        
        prompt = f"""You are an expert HR recruiter and career advisor. 
Analyze the match between this candidate's CV and the job posting.

JOB DETAILS:
Title: {job.title}
Company: {job.company}
Description: {job.description}
Requirements: {job.requirements or 'Not specified'}
Qualifications: {job.qualifications or 'Not specified'}
Required Skills: {', '.join(job.skills_required) if job.skills_required else 'Not specified'}
Experience Level: {job.experience_level or 'Not specified'}
Location: {job.location or 'Not specified'}

CANDIDATE CV:
{cv_version.optimized_text or (cv_version.cv.data.raw_text if hasattr(cv_version.cv, 'data') else '')}

Please analyze the match and provide:

1. Overall Match Score (0-100): Based on overall fit
2. Skill Match Score (0-100): How well skills match
3. Experience Match Score (0-100): How well experience matches
4. Matched Skills: List of skills the candidate has that match the job
5. Missing Skills: List of required skills the candidate is missing
6. Additional Skills: List of extra skills candidate has
7. Suggestions: List of 3-5 specific suggestions to improve match
8. Improvement Ideas: Brief paragraph on how to improve chances

Return ONLY valid JSON in this exact format:
{{
  "overall_match": 85,
  "skill_match": 90,
  "experience_match": 80,
  "location_match": 100,
  "matched_skills": ["Python", "Django", "React", "PostgreSQL"],
  "missing_skills": ["AWS", "Docker"],
  "additional_skills": ["Machine Learning", "Data Analysis"],
  "suggestions": [
    "Get AWS certification",
    "Add Docker projects to portfolio",
    "Emphasize Django REST Framework experience"
  ],
  "improvement_ideas": "To improve your chances..."
}}

Important: 
- Be realistic with scores (85+ is excellent match)
- Only include skills actually mentioned in CV
- Location match is 100 if locations match or job is remote, 0 otherwise
"""
        
        return prompt
    
    def _parse_match_response(self, response: str) -> dict:
        """Parse AI response into structured data"""
        
        # Extract JSON from response
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        
        if json_start == -1 or json_end == 0:
            raise ValueError("No JSON found in response")
        
        json_str = response[json_start:json_end]
        match_data = json.loads(json_str)
        
        # Validate required fields
        required_fields = ['overall_match', 'skill_match', 'experience_match', 
                        'matched_skills', 'missing_skills']
        for field in required_fields:
            if field not in match_data:
                match_data[field] = 0 if 'score' in field.lower() else []
        
        # Ensure scores are in range
        for field in ['overall_match', 'skill_match', 'experience_match', 'location_match']:
            if field in match_data:
                match_data[field] = min(100, max(0, float(match_data[field])))
        
        return match_data
    
    def _fallback_match_calculation(self, cv_version: CVVersion, job: Job) -> dict:
        """Fallback calculation if AI fails"""
        
        cv_text = (cv_version.optimized_text or (cv_version.cv.data.raw_text if hasattr(cv_version.cv, 'data') else '')).lower()
        job_text = f"{job.title} {job.description} {job.requirements or ''}".lower()
        
        # Calculate skill match
        matched_skills = []
        missing_skills = []
        
        for skill in job.skills_required:
            if skill.lower() in cv_text:
                matched_skills.append(skill)
            else:
                missing_skills.append(skill)
        
        skill_score = (len(matched_skills) / len(job.skills_required) * 100) if job.skills_required else 50
        
        # Simple heuristic for overall score
        overall_score = (skill_score * 0.6) + (50 * 0.4)  # 60% skill, 40% baseline
        
        return {
            'overall_match': overall_score,
            'skill_match': skill_score,
            'experience_match': 50,  # Can't determine without AI
            'location_match': 100 if not job.location or 'remote' in job.location.lower() else 50,
            'matched_skills': matched_skills,
            'missing_skills': missing_skills,
            'additional_skills': [],
            'suggestions': [],
            'improvement_ideas': 'Complete profile for better matching'
        }
    
    def find_matching_jobs(self, user: User, limit: int = 50, 
                        min_score: float = 70.0) -> list:
        """
        Find jobs matching user's CV
        
        Args:
            user: User object
            limit: Maximum number of jobs to return
            min_score: Minimum match score (0-100)
        
        Returns:
            List of jobs with match scores
        """
        # Get active CV
        cv_version = CVVersion.objects.filter(
            cv__user=user,
            is_current=True
        ).first()
        
        if not cv_version:
            return []
        
        # Get active jobs
        jobs = Job.objects.filter(is_active=True)[:limit]
        
        matched_jobs = []
        
        for job in jobs:
            # Check if already matched
            existing_match = JobMatch.objects.filter(
                user=user,
                job=job,
                cv_version=cv_version
            ).first()
            
            if existing_match:
                match_data = {
                    'job': job,
                    'overall_match': float(existing_match.overall_match),
                    'skill_match': float(existing_match.skill_match),
                    'experience_match': float(existing_match.experience_match),
                    'matched_skills': existing_match.matched_skills,
                    'missing_skills': existing_match.missing_skills,
                    'suggestions': existing_match.suggestions
                }
            else:
                # Calculate new match
                match_data = self.calculate_match(user, job, cv_version)
                match_data['job'] = job
            
            # Filter by minimum score
            if match_data['overall_match'] >= min_score:
                matched_jobs.append(match_data)
        
        # Sort by match score
        matched_jobs.sort(key=lambda x: x['overall_match'], reverse=True)
        
        return matched_jobs
    
    def save_match_result(self, user: User, job: Job, 
                        cv_version: CVVersion, match_data: dict):
        """Save match result to database"""
        
        # Create or update JobMatch
        JobMatch.objects.update_or_create(
            user=user,
            job=job,
            cv_version=cv_version,
            defaults={
                'overall_match': match_data['overall_match'],
                'skill_match': match_data['skill_match'],
                'experience_match': match_data.get('experience_match', 0),
                'location_match': match_data.get('location_match', 0),
                'matched_skills': match_data['matched_skills'],
                'missing_skills': match_data['missing_skills'],
                'additional_skills': match_data.get('additional_skills', []),
                'suggestions': match_data.get('suggestions', []),
                'improvement_ideas': match_data.get('improvement_ideas', '')
            }
        )