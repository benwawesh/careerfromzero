"""
CV Customizer AI Agent
Generates customized CVs for specific job postings
"""

from .base_agent import BaseCVAgent
from users.models import User
from cv_builder.models import CVVersion
from job_system.models import Job
import json


class CVCustomizerAgent(BaseCVAgent):
    """AI agent for customizing CVs for specific jobs"""
    
    def __init__(self):
        super().__init__()
        self.model = "claude-haiku-4-5-20251001"  # Claude API
    
    def customize_cv(self, user: User, job: Job, cv_version: CVVersion = None) -> dict:
        """
        Generate a customized CV for a specific job
        
        Args:
            user: User object
            job: Job object
            cv_version: CVVersion object (optional)
        
        Returns:
            dict with customized CV and changes made
        """
        # Get CV content
        if not cv_version:
            cv_version = CVVersion.objects.filter(
                cv__user=user,
                is_current=True
            ).first()

        if not cv_version:
            return {
                'error': 'No active CV found'
            }
        
        # Build customization prompt
        prompt = self._build_customization_prompt(cv_version, job)
        
        # Get AI response using base class method
        response = self.generate_response(prompt)
        
        # Parse response
        try:
            custom_cv = self._parse_custom_cv_response(response)
        except Exception as e:
            print(f"Error parsing custom CV response: {e}")
            custom_cv = self._fallback_customization(cv_version, job)
        
        return custom_cv
    
    def _build_customization_prompt(self, cv_version: CVVersion, job: Job) -> str:
        """Build prompt for CV customization"""
        
        prompt = f"""You are an expert CV writer and career coach. 
Customize this candidate's CV for the specific job posting.

JOB DETAILS:
Title: {job.title}
Company: {job.company}
Description: {job.description}
Requirements: {job.requirements or 'Not specified'}
Qualifications: {job.qualifications or 'Not specified'}
Required Skills: {', '.join(job.skills_required) if job.skills_required else 'Not specified'}
Experience Level: {job.experience_level or 'Not specified'}
Location: {job.location or 'Not specified'}

CANDIDATE ORIGINAL CV:
{cv_version.optimized_text or (cv_version.cv.data.raw_text if hasattr(cv_version.cv, 'data') else '')}

Please customize the CV to match this job by:

1. Reordering sections to highlight most relevant experience
2. Rewriting bullet points to include job-specific keywords
3. Emphasizing skills and experience that match the job requirements
4. De-emphasizing or removing irrelevant experience
5. Using action verbs and quantifiable achievements
6. Optimizing for ATS (Applicant Tracking System)
7. Tailoring the summary to the specific role

IMPORTANT:
- Keep the CV factual and honest
- Don't invent skills or experience
- Maintain professional tone
- Include keywords from job description
- Focus on achievements and results

Return ONLY valid JSON in this exact format:
{{
  "custom_cv": {{
    "name": "{job.title} - {job.company}",
    "summary": "Tailored professional summary...",
    "experience": [
      {{
        "company": "Company Name",
        "title": "Job Title",
        "duration": "Jan 2020 - Present",
        "location": "City, Country",
        "responsibilities": [
          "Developed and maintained RESTful APIs using Django REST Framework",
          "Led a team of 5 developers to deliver projects on time",
          "Implemented CI/CD pipelines reducing deployment time by 50%"
        ]
      }}
    ],
    "education": [
      {{
        "institution": "University Name",
        "degree": "Bachelor of Science in Computer Science",
        "year": "2019"
      }}
    ],
    "skills": [
      "Python",
      "Django",
      "React",
      "PostgreSQL",
      "AWS",
      "Docker"
    ],
    "projects": [
      {{
        "name": "E-commerce Platform",
        "description": "Built full-stack e-commerce platform...",
        "technologies": ["Django", "React", "PostgreSQL"]
      }}
    ]
  }},
  "changes_made": [
    "Reordered experience to highlight Django projects",
    "Added keywords: microservices, REST APIs, CI/CD",
    "Emphasized leadership experience",
    "Removed irrelevant retail experience",
    "Rewrote bullet points to be action-oriented"
  ],
  "sections_order": ["experience", "projects", "skills", "education"]
}}

Keep the CV length appropriate (1-2 pages equivalent).
Focus on achievements and quantifiable results.
"""
        
        return prompt
    
    def _parse_custom_cv_response(self, response: str) -> dict:
        """Parse AI response into structured data"""
        
        # Extract JSON from response
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        
        if json_start == -1 or json_end == 0:
            raise ValueError("No JSON found in response")
        
        json_str = response[json_start:json_end]
        custom_cv = json.loads(json_str)
        
        # Validate required fields
        required_fields = ['custom_cv', 'changes_made']
        for field in required_fields:
            if field not in custom_cv:
                custom_cv[field] = [] if field == 'changes_made' else {}
        
        return custom_cv
    
    def _fallback_customization(self, cv_version: CVVersion, job: Job) -> dict:
        """Fallback customization if AI fails"""
        
        # Try to parse original CV
        cv_text = cv_version.optimized_text or (cv_version.cv.data.raw_text if hasattr(cv_version.cv, 'data') else '')
        try:
            original_cv = json.loads(cv_text)
        except Exception:
            original_cv = {'content': cv_text}
        
        # Simple keyword injection
        changes = []
        
        # Add job title to name
        if 'name' in original_cv:
            changes.append(f"Updated name to: {job.title} - {job.company}")
        
        # Add required skills if not present
        if job.skills_required:
            if 'skills' not in original_cv:
                original_cv['skills'] = job.skills_required
                changes.append(f"Added skills: {', '.join(job.skills_required)}")
            else:
                new_skills = [s for s in job.skills_required if s not in original_cv.get('skills', [])]
                if new_skills:
                    original_cv['skills'].extend(new_skills)
                    changes.append(f"Added missing skills: {', '.join(new_skills)}")
        
        return {
            'custom_cv': original_cv,
            'changes_made': changes,
            'sections_order': ['experience', 'education', 'skills', 'projects']
        }
    
    def batch_customize(self, user: User, jobs: list, 
                     cv_version: CVVersion = None) -> dict:
        """
        Generate customized CVs for multiple jobs
        
        Args:
            user: User object
            jobs: List of Job objects
            cv_version: CVVersion object (optional)
        
        Returns:
            dict mapping job IDs to custom CVs
        """
        results = {}
        
        for job in jobs:
            try:
                custom_cv = self.customize_cv(user, job, cv_version)
                results[str(job.id)] = custom_cv
            except Exception as e:
                print(f"Error customizing CV for job {job.id}: {e}")
                results[str(job.id)] = {'error': str(e)}
        
        return results