"""
CrewAI Tools for the CV Agent system.

Each tool is a discrete, reusable capability that any CV-related agent can call.
Agents decide when and how to use these tools based on the task they are given.
"""

import json
import logging
import re

from crewai.tools import tool

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Internal helpers                                                     #
# ------------------------------------------------------------------ #

def _call_ai(prompt: str, temperature: float = 0.3) -> str:
    """Call Claude via ai_service for tool use. Returns raw text."""
    from .services import ai_service
    try:
        response = ai_service.generate(prompt=prompt, temperature=temperature)
        return response or ""
    except Exception as e:
        logger.error(f"AI tool call failed: {e}", exc_info=True)
        return ""


def _extract_json(text: str) -> dict:
    """Pull the first JSON object out of a raw LLM response."""
    cleaned = re.sub(r'```(?:json)?\s*', '', text).strip().rstrip('`').strip()
    match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {}


# ------------------------------------------------------------------ #
# Tool 1 — ATS Score Analyzer                                         #
# ------------------------------------------------------------------ #

@tool("ATS Score Analyzer")
def analyze_ats_score(cv_text: str) -> str:
    """
    Analyzes a CV for ATS (Applicant Tracking System) compatibility.
    Scores the CV across four dimensions and returns detailed feedback.

    Use this when you need to evaluate how well a CV will perform
    against automated screening systems.

    Input: Plain text content of the CV (full text).
    Returns: JSON string with ats_score, overall_score, content_quality_score,
             formatting_score, strengths, weaknesses, suggestions,
             missing_keywords, missing_sections.
    """
    prompt = f"""You are a senior ATS (Applicant Tracking System) consultant.
Evaluate this CV and return ONLY a valid JSON object — no explanation, no markdown.

{{
  "ats_score": <integer 0-100, how ATS-friendly is the CV>,
  "overall_score": <integer 0-100, overall quality>,
  "content_quality_score": <integer 0-100, quality of content and achievements>,
  "formatting_score": <integer 0-100, structure and readability>,
  "strengths": ["concrete strength 1", "concrete strength 2", "concrete strength 3"],
  "weaknesses": ["specific weakness 1", "specific weakness 2"],
  "suggestions": ["actionable fix 1", "actionable fix 2", "actionable fix 3"],
  "missing_keywords": ["keyword 1", "keyword 2", "keyword 3"],
  "missing_sections": ["section name 1"]
}}

CV TEXT:
{cv_text[:3500]}

Return ONLY the JSON object."""

    result = _call_ai(prompt, temperature=0.2)
    logger.info("ATS Score Analyzer tool completed")
    return result or '{}'


# ------------------------------------------------------------------ #
# Tool 2 — Job Requirements Extractor                                  #
# ------------------------------------------------------------------ #

@tool("Job Requirements Extractor")
def extract_job_requirements(job_description: str) -> str:
    """
    Extracts structured requirements from a job description.
    Identifies required skills, preferred skills, keywords, seniority level,
    and key responsibilities that a CV must address.

    Use this at the start of any tailoring workflow to understand
    exactly what the employer is looking for.

    Input: Full text of the job description.
    Returns: JSON string with required_skills, preferred_skills, keywords,
             experience_years, education_level, key_responsibilities.
    """
    prompt = f"""You are a talent acquisition specialist.
Extract all requirements from this job description. Return ONLY valid JSON — no explanation.

{{
  "required_skills": ["must-have skill 1", "must-have skill 2"],
  "preferred_skills": ["nice-to-have skill 1", "nice-to-have skill 2"],
  "keywords": ["important keyword 1", "keyword 2", "keyword 3"],
  "experience_years": <integer or null>,
  "education_level": "<Bachelor|Master|PhD|null>",
  "seniority_level": "<Junior|Mid|Senior|Lead|Manager|null>",
  "key_responsibilities": ["responsibility 1", "responsibility 2"],
  "industry": "<industry name or null>"
}}

JOB DESCRIPTION:
{job_description[:3000]}

Return ONLY the JSON object."""

    result = _call_ai(prompt, temperature=0.2)
    logger.info("Job Requirements Extractor tool completed")
    return result or '{}'


# ------------------------------------------------------------------ #
# Tool 3 — CV Tailor Writer                                           #
# ------------------------------------------------------------------ #

@tool("CV Tailor Writer")
def tailor_cv_to_job(cv_text: str, job_requirements_json: str) -> str:
    """
    Rewrites a CV to match specific job requirements.
    Naturally incorporates missing keywords, restructures bullet points
    to highlight relevant experience, and strengthens the summary.

    Use this as the final step in the tailoring workflow, after job
    requirements and gap analysis are complete.

    Input:
      cv_text: Original plain-text CV content.
      job_requirements_json: JSON string from the Job Requirements Extractor.
    Returns: JSON string with optimized_text, keywords_added, changes_made,
             match_percentage, ats_score, overall_score.
    """
    prompt = f"""You are a Certified Professional Resume Writer (CPRW).
Rewrite the CV below to match the job requirements provided.
Naturally integrate missing keywords, strengthen bullet points with metrics,
and ensure the summary directly addresses the role.

Return ONLY valid JSON — no explanation:

{{
  "optimized_text": "<full rewritten CV as plain text>",
  "keywords_added": ["keyword 1", "keyword 2"],
  "changes_made": ["Rewrote summary to target X role", "Added Y keyword to skills", "Quantified Z achievement"],
  "match_percentage": <integer 0-100>,
  "ats_score": <integer 0-100>,
  "overall_score": <integer 0-100>
}}

JOB REQUIREMENTS:
{job_requirements_json[:1500]}

ORIGINAL CV:
{cv_text[:2500]}

Return ONLY the JSON object."""

    result = _call_ai(prompt, temperature=0.4)
    logger.info("CV Tailor Writer tool completed")
    return result or '{}'


# ------------------------------------------------------------------ #
# Tool 4 — CV Section Enhancer                                        #
# ------------------------------------------------------------------ #

@tool("CV Section Enhancer")
def enhance_cv_section(section_name: str, section_content: str, improvement_notes: str) -> str:
    """
    Rewrites a single CV section to improve impact, add metrics,
    and strengthen action verbs based on specific improvement notes.

    Use this to target individual weak sections identified during ATS analysis.

    Input:
      section_name: Name of the section (e.g. "Work Experience", "Summary").
      section_content: Current text of that section.
      improvement_notes: Specific notes on what to improve (from ATS analysis).
    Returns: Enhanced plain text for that section.
    """
    prompt = f"""You are a professional CV writer.
Rewrite the '{section_name}' section of this CV.
Apply the improvement notes provided: use strong action verbs, add metrics where possible,
and make every bullet point demonstrate clear impact.

Improvement notes: {improvement_notes}

Original {section_name}:
{section_content[:2000]}

Return ONLY the improved section text — no JSON, no explanation, just the rewritten section."""

    result = _call_ai(prompt, temperature=0.5)
    logger.info(f"CV Section Enhancer tool completed for: {section_name}")
    return result or section_content


# ------------------------------------------------------------------ #
# Tool 5 — Skill Gap Mapper                                           #
# ------------------------------------------------------------------ #

@tool("Skill Gap Mapper")
def map_skill_gaps(cv_skills_text: str, job_requirements_json: str) -> str:
    """
    Compares skills found in a CV against job requirements to produce
    a structured gap analysis.

    Use this between job requirement extraction and CV rewriting to give
    the CV Writer agent a clear picture of what to add or emphasize.

    Input:
      cv_skills_text: Skills and experience section from the CV.
      job_requirements_json: JSON string from the Job Requirements Extractor.
    Returns: JSON string with matched_skills, missing_skills,
             transferable_skills, priority_additions.
    """
    prompt = f"""You are a career consultant specializing in skills assessment.
Compare the candidate's skills against the job requirements and return ONLY valid JSON:

{{
  "matched_skills": ["skill the CV already covers well 1", "skill 2"],
  "missing_skills": ["required skill not in CV 1", "missing skill 2"],
  "transferable_skills": ["skill in CV that partially applies 1"],
  "priority_additions": ["most important skill to add 1", "priority 2", "priority 3"],
  "match_score": <integer 0-100>
}}

JOB REQUIREMENTS:
{job_requirements_json[:1500]}

CV SKILLS AND EXPERIENCE:
{cv_skills_text[:2000]}

Return ONLY the JSON object."""

    result = _call_ai(prompt, temperature=0.2)
    logger.info("Skill Gap Mapper tool completed")
    return result or '{}'
