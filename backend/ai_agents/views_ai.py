"""
AI Agent Views
4 AI-powered endpoints using Claude API with token deduction.
"""

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .services.ollama_service import ollama_service
from payments.decorators import require_tokens
from payments.token_service import check_balance

logger = logging.getLogger(__name__)


def _call_claude(system: str, user_message: str, max_tokens: int = 2048) -> str:
    """Helper to call Claude API."""
    return ollama_service.chat(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ],
        temperature=0.7,
        max_tokens=max_tokens,
    )


# ─── 1. CV Agent ─────────────────────────────────────────────────────────────

class WriteCVView(APIView):
    """Write a full CV from scratch based on user-provided information."""
    permission_classes = [IsAuthenticated]

    @require_tokens('cv_write')
    def post(self, request):
        data = request.data
        required = ['full_name', 'job_title', 'skills', 'email']
        missing = [f for f in required if not data.get(f)]
        if missing:
            return Response({'error': True, 'message': f'Missing fields: {", ".join(missing)}'}, status=400)

        user_info = f"""
Name: {data.get('full_name')}
Target Job: {data.get('job_title')}
Email: {data.get('email')}
Phone: {data.get('phone', 'Not provided')}
Location: {data.get('location', 'Not provided')}
Years of Experience: {data.get('years_experience', 'Not specified')}
Skills: {data.get('skills')}
Summary: {data.get('summary', 'Not provided')}
Work Experience: {data.get('work_experience', 'Not provided')}
Education: {data.get('education', 'Not provided')}
LinkedIn: {data.get('linkedin_url', '')}
"""

        system = """You are an expert CV writer with 15+ years of experience helping professionals land jobs in Kenya and globally.
Write professional, ATS-optimized CVs that highlight achievements using action verbs and quantified results.
Format the CV clearly with sections: Professional Summary, Work Experience, Education, Skills, and Contact Info.
Use clean formatting with clear headers. Write in a professional tone."""

        prompt = f"""Write a complete, professional CV for this person:

{user_info}

Requirements:
- ATS-optimized with relevant keywords
- Professional summary (3-4 sentences)
- Work experience with bullet points using action verbs
- Education section
- Skills section organized by category
- Clean, professional formatting

Return the complete CV text ready to use."""

        try:
            cv_text = _call_claude(system, prompt, max_tokens=3000)
            return Response({
                'success': True,
                'cv_text': cv_text,
                'feature': 'cv_write',
            })
        except Exception as e:
            logger.error(f"CV write failed: {e}", exc_info=True)
            return Response({'error': True, 'message': 'CV generation failed. Please try again.'}, status=500)


class RevampCVView(APIView):
    """Revamp and improve an existing CV."""
    permission_classes = [IsAuthenticated]

    @require_tokens('cv_revamp')
    def post(self, request):
        cv_text = request.data.get('cv_text', '').strip()
        target_job = request.data.get('target_job', '')

        if not cv_text:
            return Response({'error': True, 'message': 'cv_text is required'}, status=400)

        system = """You are an expert CV writer and career coach specializing in CV optimization for the Kenyan and African job market.
Improve CVs to be more professional, ATS-friendly, and impactful."""

        prompt = f"""Revamp and significantly improve this CV{f' targeting the role of {target_job}' if target_job else ''}:

ORIGINAL CV:
{cv_text}

Improvements to make:
1. Strengthen the professional summary
2. Rewrite bullet points using strong action verbs and quantified achievements
3. Optimize keywords for ATS systems
4. Improve formatting and structure
5. Fix any grammar/spelling issues
6. Make it more concise and impactful

Return the complete improved CV text."""

        try:
            improved_cv = _call_claude(system, prompt, max_tokens=3000)
            return Response({
                'success': True,
                'cv_text': improved_cv,
                'feature': 'cv_revamp',
            })
        except Exception as e:
            logger.error(f"CV revamp failed: {e}", exc_info=True)
            return Response({'error': True, 'message': 'CV revamp failed. Please try again.'}, status=500)


# ─── 2. CV Customization Agent ───────────────────────────────────────────────

class CustomizeCVView(APIView):
    """Tailor a CV to match a specific job description."""
    permission_classes = [IsAuthenticated]

    @require_tokens('cv_customize')
    def post(self, request):
        cv_text = request.data.get('cv_text', '').strip()
        job_description = request.data.get('job_description', '').strip()
        job_title = request.data.get('job_title', '')

        if not cv_text or not job_description:
            return Response({'error': True, 'message': 'cv_text and job_description are required'}, status=400)

        system = """You are an expert CV writer specializing in tailoring CVs to specific job descriptions.
You ensure the CV passes ATS filters and resonates with the hiring manager."""

        prompt = f"""Customize this CV to match the job description below.

JOB TITLE: {job_title}

JOB DESCRIPTION:
{job_description}

CANDIDATE'S CURRENT CV:
{cv_text}

Instructions:
1. Mirror keywords and phrases from the job description
2. Reorder/emphasize skills that match the job requirements
3. Rewrite bullet points to highlight relevant experience
4. Tailor the professional summary for this specific role
5. Keep all facts true — only rephrase, don't fabricate

Return the customized CV text."""

        try:
            customized_cv = _call_claude(system, prompt, max_tokens=3000)
            return Response({
                'success': True,
                'cv_text': customized_cv,
                'feature': 'cv_customize',
            })
        except Exception as e:
            logger.error(f"CV customize failed: {e}", exc_info=True)
            return Response({'error': True, 'message': 'CV customization failed. Please try again.'}, status=500)


class WriteCoverLetterView(APIView):
    """Write a cover letter for a specific job."""
    permission_classes = [IsAuthenticated]

    @require_tokens('cover_letter')
    def post(self, request):
        cv_text = request.data.get('cv_text', '').strip()
        job_description = request.data.get('job_description', '').strip()
        job_title = request.data.get('job_title', '')
        company_name = request.data.get('company_name', 'the company')
        applicant_name = request.data.get('applicant_name', '')

        if not cv_text or not job_description:
            return Response({'error': True, 'message': 'cv_text and job_description are required'}, status=400)

        system = """You are an expert cover letter writer who crafts compelling, personalized cover letters
that get candidates noticed. You write in a professional yet engaging tone."""

        prompt = f"""Write a compelling cover letter for this job application.

APPLICANT NAME: {applicant_name}
JOB TITLE: {job_title}
COMPANY: {company_name}

JOB DESCRIPTION:
{job_description}

APPLICANT'S CV:
{cv_text}

Requirements:
- 3-4 paragraphs, max 400 words
- Opening: Hook that shows enthusiasm and fits the role
- Body: 2 specific achievements from CV that match job requirements
- Closing: Strong call to action
- Professional but personable tone
- Mention the company name naturally

Return the complete cover letter."""

        try:
            cover_letter = _call_claude(system, prompt, max_tokens=1500)
            return Response({
                'success': True,
                'cover_letter': cover_letter,
                'feature': 'cover_letter',
            })
        except Exception as e:
            logger.error(f"Cover letter failed: {e}", exc_info=True)
            return Response({'error': True, 'message': 'Cover letter generation failed. Please try again.'}, status=500)


# ─── 3. Career Guidance Agent ────────────────────────────────────────────────

class CareerGuidanceView(APIView):
    """Chat-based career guidance. Each message costs tokens."""
    permission_classes = [IsAuthenticated]

    @require_tokens('career_guidance')
    def post(self, request):
        message = request.data.get('message', '').strip()
        conversation_history = request.data.get('history', [])  # [{role, content}]
        user_profile = request.data.get('user_profile', '')

        if not message:
            return Response({'error': True, 'message': 'message is required'}, status=400)

        system = f"""You are an expert career counselor and coach with deep knowledge of the Kenyan, African, and global job markets.
You provide practical, actionable career advice tailored to each individual.
You help with: career path planning, skill development, job search strategies, salary negotiation, workplace challenges, and career transitions.
Be encouraging, specific, and practical. Give concrete next steps.
{f'User background: {user_profile}' if user_profile else ''}"""

        # Build conversation messages
        messages = [{"role": "system", "content": system}]
        for msg in conversation_history[-10:]:  # Keep last 10 messages for context
            if msg.get('role') in ('user', 'assistant'):
                messages.append({"role": msg['role'], "content": msg['content']})
        messages.append({"role": "user", "content": message})

        try:
            reply = ollama_service.chat(messages=messages, temperature=0.7, max_tokens=1000)
            return Response({
                'success': True,
                'reply': reply,
                'feature': 'career_guidance',
            })
        except Exception as e:
            logger.error(f"Career guidance failed: {e}", exc_info=True)
            return Response({'error': True, 'message': 'Career guidance failed. Please try again.'}, status=500)


# ─── 4. Job Matching Agent ───────────────────────────────────────────────────

class AIJobMatchView(APIView):
    """Match a CV against available jobs using Claude AI."""
    permission_classes = [IsAuthenticated]

    @require_tokens('job_match')
    def post(self, request):
        cv_text = request.data.get('cv_text', '').strip()
        job_id = request.data.get('job_id')

        if not cv_text or not job_id:
            return Response({'error': True, 'message': 'cv_text and job_id are required'}, status=400)

        from job_system.models import Job
        try:
            job = Job.objects.get(id=job_id, is_active=True)
        except Job.DoesNotExist:
            return Response({'error': True, 'message': 'Job not found'}, status=404)

        job_info = f"""
Title: {job.title}
Company: {job.company}
Location: {job.location}
Description: {job.description or 'Not provided'}
"""

        system = """You are an expert job matching specialist. Analyze how well a candidate's CV matches a job posting.
Return a JSON response with exact keys: match_score (0-100), skill_match (0-100), experience_match (0-100),
matched_skills (list), missing_skills (list), recommendation (string, 1-2 sentences)."""

        prompt = f"""Analyze this CV against the job posting and return a JSON match analysis.

JOB:
{job_info}

CANDIDATE CV:
{cv_text}

Return valid JSON only, no extra text:
{{
  "match_score": <0-100>,
  "skill_match": <0-100>,
  "experience_match": <0-100>,
  "matched_skills": ["skill1", "skill2"],
  "missing_skills": ["skill3", "skill4"],
  "recommendation": "One or two sentence recommendation"
}}"""

        try:
            import json
            response_text = _call_claude(system, prompt, max_tokens=800)

            # Parse JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                match_data = json.loads(json_match.group())
            else:
                match_data = {'match_score': 0, 'error': 'Could not parse response'}

            return Response({
                'success': True,
                'job_id': job_id,
                'job_title': job.title,
                'company': job.company,
                'match_data': match_data,
                'feature': 'job_match',
            })
        except Exception as e:
            logger.error(f"Job match failed: {e}", exc_info=True)
            return Response({'error': True, 'message': 'Job matching failed. Please try again.'}, status=500)


# ─── Token balance check (no deduction) ──────────────────────────────────────

class TokenBalanceCheckView(APIView):
    """Quick check of user's token balance and feature costs."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from payments.token_service import get_or_create_balance, get_feature_cost
        balance = get_or_create_balance(request.user)
        features = ['cv_write', 'cv_revamp', 'cv_customize', 'cover_letter', 'career_guidance', 'job_match']
        return Response({
            'balance': balance.balance,
            'feature_costs': {f: get_feature_cost(f) for f in features},
        })
