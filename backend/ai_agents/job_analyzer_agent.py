"""
Job Analyzer AI Agent
Analyzes job postings for better matching and categorization
"""

from .base_agent import BaseJobAgent
from job_system.models import Job
import json


class JobAnalyzerAgent(BaseJobAgent):
    """AI agent for analyzing job postings"""
    
    def __init__(self):
        super().__init__()
        self.model = "claude-haiku-4-5-20251001"  # Claude API
    
    def analyze_job(self, job: Job) -> dict:
        """
        Analyze a job posting in detail
        
        Args:
            job: Job object
        
        Returns:
            dict with job analysis
        """
        # Build prompt
        prompt = self._build_analysis_prompt(job)
        
        # Get AI response using base class method
        response = self.generate_response(prompt)
        
        # Parse response
        try:
            analysis = self._parse_analysis_response(response)
        except Exception as e:
            print(f"Error parsing job analysis: {e}")
            analysis = self._fallback_analysis(job)
        
        return analysis
    
    def _build_analysis_prompt(self, job: Job) -> str:
        """Build prompt for job analysis"""
        
        prompt = f"""You are an expert HR analyst and job market researcher.
Analyze this job posting in detail.

JOB DETAILS:
Title: {job.title}
Company: {job.company}
Description: {job.description}
Requirements: {job.requirements or 'Not specified'}
Qualifications: {job.qualifications or 'Not specified'}
Location: {job.location or 'Not specified'}
Type: {job.job_type or 'Not specified'}
Experience Level: {job.experience_level or 'Not specified'}
Salary: {job.salary_range}

Please analyze and provide:

1. Must-Have Skills: Essential skills for this role
2. Nice-to-Have Skills: Optional but valuable skills
3. Job Level: Entry, Mid, Senior, Lead, Executive
4. Estimated Salary: Estimated salary range (USD)
5. Difficulty: Easy, Medium, Hard, Very Hard
6. Category: Software, Marketing, Design, Sales, HR, Finance, etc.
7. Experience Required: Years of experience needed
8. Education Required: Minimum education level
9. Company Culture Indicators: List of cultural clues (e.g., fast-paced, innovative, traditional)
10. Required Years of Experience: Number (e.g., 3, 5, 10)

Return ONLY valid JSON in this exact format:
{{
  "must_have_skills": ["Python", "Django", "PostgreSQL"],
  "nice_to_have_skills": ["AWS", "Docker", "Kubernetes"],
  "job_level": "Senior",
  "estimated_salary": {{
    "min": 120000,
    "max": 150000,
    "currency": "USD"
  }},
  "difficulty": "Hard",
  "category": "Software Engineering",
  "experience_required": "5+ years",
  "education_required": "Bachelor's Degree",
  "years_of_experience": 5,
  "culture_indicators": [
    "Fast-paced",
    "Innovative",
    "Results-oriented",
    "Collaborative"
  ]
}}

Be realistic with salary estimates based on market rates.
Consider job location for salary (remote typically pays market rate).
"""
        
        return prompt
    
    def _parse_analysis_response(self, response: str) -> dict:
        """Parse AI response into structured data"""
        
        # Extract JSON from response
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        
        if json_start == -1 or json_end == 0:
            raise ValueError("No JSON found in response")
        
        json_str = response[json_start:json_end]
        analysis = json.loads(json_str)
        
        # Validate required fields
        required_fields = ['must_have_skills', 'nice_to_have_skills', 
                        'job_level', 'difficulty', 'category']
        for field in required_fields:
            if field not in analysis:
                analysis[field] = [] if 'skills' in field else 'Medium'
        
        # Ensure optional fields exist
        if 'culture_indicators' not in analysis:
            analysis['culture_indicators'] = []
        if 'estimated_salary' not in analysis:
            analysis['estimated_salary'] = {}
        if 'years_of_experience' not in analysis:
            analysis['years_of_experience'] = 0
        if 'education_required' not in analysis:
            analysis['education_required'] = 'Not specified'
        
        return analysis
    
    def _fallback_analysis(self, job: Job) -> dict:
        """Fallback analysis if AI fails"""
        
        # Extract skills from description
        description_text = f"{job.description} {job.requirements or ''}".lower()
        
        # Common tech keywords
        tech_keywords = ['python', 'javascript', 'react', 'angular', 'django', 
                      'node', 'java', 'c++', 'aws', 'docker', 'kubernetes',
                      'postgresql', 'mysql', 'mongodb', 'redis', 'graphql',
                      'machine learning', 'ai', 'data science']
        
        must_have = []
        nice_to_have = []
        
        for keyword in tech_keywords:
            if keyword in description_text:
                must_have.append(keyword.capitalize())
        
        # Determine level from title
        title_lower = job.title.lower()
        if 'senior' in title_lower or 'lead' in title_lower:
            level = 'Senior'
            years = 5
        elif 'mid' in title_lower or 'experienced' in title_lower:
            level = 'Mid'
            years = 3
        elif 'junior' in title_lower or 'entry' in title_lower:
            level = 'Entry'
            years = 1
        else:
            level = 'Mid'
            years = 3
        
        # Determine category
        if any(kw in title_lower for kw in ['developer', 'engineer', 'software']):
            category = 'Software Engineering'
        elif any(kw in title_lower for kw in ['designer', 'ui', 'ux']):
            category = 'Design'
        elif any(kw in title_lower for kw in ['manager', 'lead']):
            category = 'Management'
        elif any(kw in title_lower for kw in ['data', 'analyst', 'scientist']):
            category = 'Data Science'
        else:
            category = 'General'
        
        return {
            'must_have_skills': must_have[:10],
            'nice_to_have_skills': nice_to_have,
            'job_level': level,
            'estimated_salary': {},
            'difficulty': 'Medium',
            'category': category,
            'experience_required': f'{years}+ years',
            'education_required': 'Not specified',
            'years_of_experience': years,
            'culture_indicators': []
        }
    
    def batch_analyze(self, jobs: list) -> dict:
        """
        Analyze multiple jobs
        
        Args:
            jobs: List of Job objects
        
        Returns:
            dict mapping job IDs to analyses
        """
        results = {}
        
        for job in jobs:
            try:
                analysis = self.analyze_job(job)
                results[str(job.id)] = analysis
            except Exception as e:
                print(f"Error analyzing job {job.id}: {e}")
                results[str(job.id)] = {'error': str(e)}
        
        return results