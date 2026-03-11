"""
CV Agent - AI-powered CV analysis, ATS optimization, and job tailoring
"""
import json
import logging
import re

from .base_agent import BaseCVAgent

logger = logging.getLogger(__name__)


class CVAgent(BaseCVAgent):
    """
    AI agent for CV operations:
    - ATS scoring and quality analysis
    - CV tailoring to a specific job description
    - Job description keyword extraction
    """

    def analyze_cv(self, cv_text: str) -> dict:
        """
        Analyze a CV for ATS compatibility and overall quality.

        Args:
            cv_text: Plain text content of the CV

        Returns:
            Dict with scores, strengths, weaknesses, suggestions, etc.
        """
        prompt = f"""You are an expert ATS consultant and professional CV reviewer.
Analyze the following CV and return ONLY a valid JSON object with this exact structure:

{{
  "ats_score": <integer 0-100, how ATS-friendly the CV is>,
  "overall_score": <integer 0-100, overall CV quality>,
  "content_quality_score": <integer 0-100, quality of content and achievements>,
  "formatting_score": <integer 0-100, structure and formatting quality>,
  "strengths": ["strength 1", "strength 2", "strength 3"],
  "weaknesses": ["weakness 1", "weakness 2", "weakness 3"],
  "suggestions": ["actionable suggestion 1", "actionable suggestion 2", "actionable suggestion 3"],
  "formatting_issues": ["formatting issue 1", "formatting issue 2"],
  "missing_keywords": ["important keyword 1", "important keyword 2", "important keyword 3"],
  "missing_sections": ["missing section 1"]
}}

CV TEXT:
{cv_text[:4000]}

Return ONLY the JSON object. No explanation, no markdown, no preamble."""

        try:
            raw = self.generate_response(prompt, temperature=0.3)
            return self._parse_json_response(raw, self._default_analysis())
        except Exception as e:
            logger.error(f"CV analysis failed: {e}", exc_info=True)
            return self._default_analysis()

    def tailor_cv(self, cv_text: str, job_description: str) -> dict:
        """
        Rewrite a CV to match a specific job description.

        Args:
            cv_text: Original CV plain text
            job_description: Target job description text

        Returns:
            Dict with optimized CV text, keywords added, changes made, and scores.
        """
        prompt = f"""You are an expert CV writer. Rewrite the CV below to better match the job description.
Emphasize relevant skills, reorder experience bullets to match requirements, and add missing keywords naturally.

Return ONLY a valid JSON object:

{{
  "optimized_text": "<the full rewritten CV as plain text>",
  "keywords_added": ["keyword1", "keyword2", "keyword3"],
  "changes_made": ["Added X to skills section", "Reordered Y bullets", "Highlighted Z experience"],
  "ats_score": <integer 0-100>,
  "overall_score": <integer 0-100>,
  "match_percentage": <integer 0-100, how well the tailored CV matches the job>
}}

JOB DESCRIPTION:
{job_description[:2000]}

ORIGINAL CV:
{cv_text[:3000]}

Return ONLY the JSON object."""

        try:
            raw = self.generate_response(prompt, temperature=0.4)
            return self._parse_json_response(raw, self._default_tailor(cv_text))
        except Exception as e:
            logger.error(f"CV tailoring failed: {e}", exc_info=True)
            return self._default_tailor(cv_text)

    def extract_job_keywords(self, job_description: str) -> dict:
        """
        Extract structured keywords and requirements from a job description.

        Args:
            job_description: Full job description text

        Returns:
            Dict with keywords, required_skills, preferred_skills, etc.
        """
        prompt = f"""Extract structured information from this job description.
Return ONLY a valid JSON object:

{{
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "required_skills": ["must-have skill 1", "must-have skill 2"],
  "preferred_skills": ["nice-to-have skill 1", "nice-to-have skill 2"],
  "experience_years": <integer or null>,
  "education_level": "<Bachelor|Master|PhD|null>",
  "job_type": "<full-time|part-time|contract|remote|null>"
}}

JOB DESCRIPTION:
{job_description[:3000]}

Return ONLY the JSON object."""

        try:
            raw = self.generate_response(prompt, temperature=0.2)
            return self._parse_json_response(raw, {
                "keywords": [],
                "required_skills": [],
                "preferred_skills": [],
                "experience_years": None,
                "education_level": None,
                "job_type": None,
            })
        except Exception as e:
            logger.error(f"Keyword extraction failed: {e}", exc_info=True)
            return {"keywords": [], "required_skills": [], "preferred_skills": []}

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _parse_json_response(self, response: str, fallback: dict) -> dict:
        """
        Parse a JSON object from a raw LLM response string.
        Strips markdown fences if present and finds the first {...} block.
        Falls back to `fallback` if parsing fails.
        """
        if not response:
            return fallback

        # Strip markdown code fences
        cleaned = re.sub(r'```(?:json)?\s*', '', response).strip().rstrip('`').strip()

        # Find the first JSON object in the output
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if not match:
            logger.warning("No JSON object found in LLM response")
            return fallback

        try:
            return json.loads(match.group())
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error from LLM response: {e}")
            return fallback

    def _default_analysis(self) -> dict:
        return {
            "ats_score": 0,
            "overall_score": 0,
            "content_quality_score": 0,
            "formatting_score": 0,
            "strengths": [],
            "weaknesses": ["Analysis could not be completed. Please try again."],
            "suggestions": ["Ensure Ollama is running and the model is available."],
            "formatting_issues": [],
            "missing_keywords": [],
            "missing_sections": [],
        }

    def _default_tailor(self, original_text: str) -> dict:
        return {
            "optimized_text": original_text,
            "keywords_added": [],
            "changes_made": ["Tailoring could not be completed. Please try again."],
            "ats_score": 0,
            "overall_score": 0,
            "match_percentage": 0,
        }
