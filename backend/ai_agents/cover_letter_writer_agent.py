"""
Cover Letter Writer AI Agent
Generates personalized cover letters for job applications
"""

from .base_agent import BaseCVAgent
from users.models import User
from cv_builder.models import CVVersion
from job_system.models import Job


class CoverLetterWriterAgent(BaseCVAgent):
    """AI agent for writing cover letters"""
    
    def __init__(self):
        super().__init__()
        self.model = "claude-haiku-4-5-20251001"  # Claude API
    
    def write_cover_letter(self, user: User, job: Job, 
                         cv_version: CVVersion = None) -> dict:
        """
        Generate a personalized cover letter for a job
        
        Args:
            user: User object
            job: Job object
            cv_version: CVVersion object (optional)
        
        Returns:
            dict with cover letter and metadata
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
        
        # Build prompt
        prompt = self._build_cover_letter_prompt(user, cv_version, job)
        
        # Get AI response using base class method
        response = self.generate_response(prompt)
        
        # Parse response
        try:
            cover_letter_data = self._parse_cover_letter_response(response)
        except Exception as e:
            print(f"Error parsing cover letter response: {e}")
            cover_letter_data = self._fallback_cover_letter(user, job)
        
        return cover_letter_data
    
    def _build_cover_letter_prompt(self, user: User, 
                                  cv_version: CVVersion, job: Job) -> str:
        """Build prompt for cover letter generation"""
        
        # Extract user info
        user_name = user.get_full_name() or user.username
        
        prompt = f"""You are an expert career counselor and cover letter writer.
Write a compelling, personalized cover letter for this job application.

JOB DETAILS:
Title: {job.title}
Company: {job.company}
Location: {job.location or 'Not specified'}
Description: {job.description}
Requirements: {job.requirements or 'Not specified'}
Required Skills: {', '.join(job.skills_required) if job.skills_required else 'Not specified'}

CANDIDATE:
Name: {user_name}
Email: {user.email}

CANDIDATE CV:
{cv_version.optimized_text or (cv_version.cv.data.raw_text if hasattr(cv_version.cv, 'data') else '')}

Please write a professional cover letter that:

1. Has a compelling opening that hooks the reader
2. Shows enthusiasm for the specific role and company
3. Highlights relevant skills and experience from CV
4. Connects candidate's experience to job requirements
5. Demonstrates understanding of the company and role
6. Includes specific examples and achievements
7. Has a strong closing with call to action
8. Is professional yet conversational in tone
9. Is 300-400 words (single page)
10. Avoids generic phrases and clichés

Return ONLY valid JSON in this exact format:
{{
  "cover_letter": "Dear Hiring Manager,\\n\\nI am excited to apply for the...",
  "personalized_elements": [
    "Mentioned company's recent product launch",
    "Referenced specific tech stack from job posting",
    "Connected candidate's experience to company needs"
  ],
  "key_points": [
    "5+ years of Python/Django experience",
    "Led team of 5 developers",
    "Built scalable web applications"
  ]
}}

IMPORTANT:
- Make it specific to the job and company
- Use the company name (not just "your company")
- Include keywords from job description
- Highlight achievements from CV that match requirements
- Be authentic and professional
"""
        
        return prompt
    
    def _parse_cover_letter_response(self, response: str) -> dict:
        """Parse AI response into structured data"""
        
        # Extract JSON from response
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        
        if json_start == -1 or json_end == 0:
            # No JSON found, return raw text
            return {
                'cover_letter': response.strip(),
                'personalized_elements': [],
                'key_points': []
            }
        
        json_str = response[json_start:json_end]
        cover_letter_data = json.loads(json_str)
        
        # Validate required fields
        if 'cover_letter' not in cover_letter_data:
            raise ValueError("No cover letter in response")
        
        # Ensure optional fields exist
        if 'personalized_elements' not in cover_letter_data:
            cover_letter_data['personalized_elements'] = []
        if 'key_points' not in cover_letter_data:
            cover_letter_data['key_points'] = []
        
        return cover_letter_data
    
    def _fallback_cover_letter(self, user: User, job: Job) -> dict:
        """Fallback cover letter if AI fails"""
        
        user_name = user.get_full_name() or user.username
        
        cover_letter = f"""Dear Hiring Manager,

I am writing to express my strong interest in the {job.title} position at {job.company}. With my background and experience, I am confident in my ability to make a significant contribution to your team.

I am particularly drawn to {job.company} because of its reputation for excellence and innovation in the industry. The opportunity to work with a talented team on impactful projects aligns perfectly with my career goals and professional values.

I would welcome the opportunity to discuss how my skills and experience align with the {job.title} role. Thank you for considering my application. I look forward to hearing from you.

Sincerely,
{user_name}
"""
        
        return {
            'cover_letter': cover_letter,
            'personalized_elements': [
                "Mentioned specific job title and company",
                "Expressed enthusiasm for the company"
            ],
            'key_points': [
                "Relevant experience",
                "Strong interest in the role",
                "Eager to contribute"
            ]
        }
    
    def batch_write_cover_letters(self, user: User, jobs: list,
                                cv_version: CVVersion = None) -> dict:
        """
        Generate cover letters for multiple jobs
        
        Args:
            user: User object
            jobs: List of Job objects
            cv_version: CVVersion object (optional)
        
        Returns:
            dict mapping job IDs to cover letters
        """
        results = {}
        
        for job in jobs:
            try:
                cover_letter = self.write_cover_letter(user, job, cv_version)
                results[str(job.id)] = cover_letter
            except Exception as e:
                print(f"Error writing cover letter for job {job.id}: {e}")
                results[str(job.id)] = {'error': str(e)}
        
        return results