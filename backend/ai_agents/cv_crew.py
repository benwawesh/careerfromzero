"""
CV Agent Crews

Two CrewAI crews that orchestrate multiple specialized agents working together:

  CVAnalysisCrew  — 2 agents (Parser → ATS Analyst)
  CVTailoringCrew — 3 agents (Job Analyst → Gap Analyst → CV Writer)

Each agent receives the output of the previous agent as context,
producing a richer result than any single-prompt approach could.
"""

import json
import logging
import re

from crewai import Agent, Task, Crew, Process, LLM
from decouple import config

from .cv_tools import (
    analyze_ats_score,
    extract_job_requirements,
    tailor_cv_to_job,
    enhance_cv_section,
    map_skill_gaps,
)

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Shared helpers                                                       #
# ------------------------------------------------------------------ #

def _get_llm() -> LLM:
    model = config('CLAUDE_MODEL', default='claude-haiku-4-5-20251001')
    api_key = config('ANTHROPIC_API_KEY', default='')
    return LLM(
        model=f"anthropic/{model}",
        api_key=api_key,
        temperature=0.7,
        max_tokens=2048,
    )


def _parse_json(text: str, fallback: dict) -> dict:
    """Extract the first JSON object from raw crew output, merge with fallback."""
    cleaned = re.sub(r'```(?:json)?\s*', '', str(text)).strip().rstrip('`').strip()
    match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group())
            return {**fallback, **parsed}
        except json.JSONDecodeError:
            pass
    return fallback


# ------------------------------------------------------------------ #
# Crew 1 — CV Analysis                                                #
# ------------------------------------------------------------------ #

class CVAnalysisCrew:
    """
    Two agents collaborate to produce a comprehensive CV analysis:

    Agent 1 — CV Parser
      Reads the raw CV text and produces a structured summary: key skills,
      career level, experience timeline, education, achievements, and gaps.
      This gives Agent 2 a clean, organised view rather than raw text.

    Agent 2 — ATS Analyst
      Receives Agent 1's summary + uses the ATS Score Analyzer tool on the
      original text. Combines tool output with its own expertise to produce
      a final scored analysis with strengths, weaknesses, and prioritised
      suggestions.
    """

    def run(self, cv_text: str, user_context: str = "") -> dict:
        llm = _get_llm()

        # ── Agent 1: CV Parser ──────────────────────────────────────
        parser_agent = Agent(
            role="Senior CV Parser and Career Analyst",
            goal=(
                "Extract and structure every piece of information from the CV "
                "into a clear, organised summary that another agent can act on."
            ),
            backstory=(
                "You are a recruitment specialist with 15 years of experience "
                "reading CVs across every industry. You have a sharp eye for "
                "the real story behind a CV — not just what's written, but "
                "what's missing, what's vague, and what genuinely stands out. "
                "You produce structured summaries that give other analysts "
                "an instant, accurate picture of any candidate."
            ),
            llm=llm,
            allow_delegation=False,
            verbose=True,
        )

        # ── Agent 2: ATS Analyst ────────────────────────────────────
        ats_agent = Agent(
            role="ATS Optimization Specialist",
            goal=(
                "Produce a comprehensive, scored ATS analysis with actionable "
                "improvements that will meaningfully raise the CV's performance "
                "against automated screening systems."
            ),
            backstory=(
                "You are an expert in Applicant Tracking Systems — you have "
                "worked with Workday, Greenhouse, Lever, and Taleo. You know "
                "exactly how these systems parse formatting, score keyword "
                "density, and rank candidates. You have helped 1,000+ "
                "candidates improve their ATS pass rate. You always use the "
                "ATS Score Analyzer tool to get an objective baseline score, "
                "then layer in your expert judgment."
            ),
            llm=llm,
            tools=[analyze_ats_score],
            allow_delegation=False,
            verbose=True,
        )

        cv_snippet = cv_text[:1500]  # Keep prompts short for CPU inference

        # ── Task 1: Parse the CV ────────────────────────────────────
        parse_task = Task(
            description=(
                f"Briefly summarise this CV in bullet points:\n\n{cv_snippet}\n\n"
                + (f"Context: {user_context}\n\n" if user_context else "")
                + "Cover: career level, years exp, top 5 skills, education, 1-2 achievements, 1-2 gaps."
            ),
            expected_output="A short bullet-point CV summary (under 200 words).",
            agent=parser_agent,
        )

        # ── Task 2: ATS Analysis ────────────────────────────────────
        ats_task = Task(
            description=(
                "Using the CV summary, call the ATS Score Analyzer tool on this CV text, "
                "then output ONLY a JSON object:\n\n"
                f"CV TEXT FOR TOOL:\n{cv_snippet}\n\n"
                "JSON keys required: ats_score, overall_score, content_quality_score, "
                "formatting_score, strengths (3 items), weaknesses (3 items), "
                "suggestions (3 items), missing_keywords (3 items), missing_sections (list)"
            ),
            expected_output=(
                "A JSON object with ats_score, overall_score, content_quality_score, "
                "formatting_score, strengths, weaknesses, suggestions, "
                "missing_keywords, and missing_sections."
            ),
            agent=ats_agent,
            context=[parse_task],
        )

        crew = Crew(
            agents=[parser_agent, ats_agent],
            tasks=[parse_task, ats_task],
            process=Process.sequential,
            verbose=True,
        )

        try:
            result = crew.kickoff()
            raw = str(result)
            logger.info(f"CVAnalysisCrew completed — output {len(raw)} chars")
            return _parse_json(raw, self._default_analysis())
        except Exception as e:
            logger.error(f"CVAnalysisCrew failed: {e}", exc_info=True)
            return self._default_analysis()

    def _default_analysis(self) -> dict:
        return {
            "ats_score": 0,
            "overall_score": 0,
            "content_quality_score": 0,
            "formatting_score": 0,
            "strengths": [],
            "weaknesses": ["Analysis could not be completed."],
            "suggestions": ["Check ANTHROPIC_API_KEY in .env"],
            "missing_keywords": [],
            "missing_sections": [],
        }


# ------------------------------------------------------------------ #
# Crew 2 — CV Tailoring                                               #
# ------------------------------------------------------------------ #

class CVTailoringCrew:
    """
    Three agents collaborate to tailor a CV to a specific job:

    Agent 1 — Job Analyst
      Uses the Job Requirements Extractor tool to produce a structured
      breakdown of everything the employer needs.

    Agent 2 — Gap Analyst
      Receives Agent 1's job requirements and uses the Skill Gap Mapper
      tool to compare them against the CV. Identifies matched skills,
      missing skills, and transferable experience.

    Agent 3 — CV Writer
      Receives both previous agents' output. Uses the CV Tailor Writer
      tool to produce a rewritten CV, then reviews and refines it.
      The final output is a targeted, ATS-optimised CV version.
    """

    def run(self, cv_text: str, job_description: str, user_context: str = "") -> dict:
        llm = _get_llm()

        # ── Agent 1: Job Analyst ────────────────────────────────────
        job_analyst = Agent(
            role="Job Description Analyst and Requirements Specialist",
            goal=(
                "Extract every explicit and implicit requirement from the job "
                "description so the CV Writer has a complete picture of what "
                "the employer truly needs."
            ),
            backstory=(
                "You are a talent acquisition professional who has reviewed "
                "tens of thousands of job descriptions across tech, finance, "
                "healthcare, and every major industry. You can read between "
                "the lines — identifying what seniority level is really wanted, "
                "which skills are truly non-negotiable, and which buzzwords "
                "will make or break an ATS score. You always use the "
                "Job Requirements Extractor tool to produce a structured output."
            ),
            llm=llm,
            tools=[extract_job_requirements],
            allow_delegation=False,
            verbose=True,
        )

        # ── Agent 2: Gap Analyst ────────────────────────────────────
        gap_analyst = Agent(
            role="CV-to-Job Fit and Gap Analyst",
            goal=(
                "Produce a precise gap analysis showing exactly which job "
                "requirements the CV meets, which it partially meets, and "
                "which are completely absent — giving the CV Writer a clear "
                "action plan."
            ),
            backstory=(
                "You are a career consultant who specialises in candidate-role "
                "matching. After years of coaching job seekers, you can "
                "instantly see which experiences are directly relevant, which "
                "are transferable, and which gaps are dealbreakers. You use "
                "the Skill Gap Mapper tool to ground your analysis in data, "
                "then add strategic insight about what the CV Writer should "
                "prioritise."
            ),
            llm=llm,
            tools=[map_skill_gaps],
            allow_delegation=False,
            verbose=True,
        )

        # ── Agent 3: CV Writer ──────────────────────────────────────
        cv_writer = Agent(
            role="Certified Professional CV Writer and ATS Optimizer",
            goal=(
                "Produce a rewritten CV that maximally matches the job "
                "requirements, passes ATS screening with a high score, and "
                "tells a compelling career story that a human recruiter will "
                "also find impressive."
            ),
            backstory=(
                "You are a CPRW (Certified Professional Resume Writer) with "
                "a track record of getting candidates interviews at Google, "
                "Amazon, McKinsey, and top-tier firms. You understand ATS "
                "deeply — you know how to integrate keywords naturally without "
                "keyword stuffing, how to quantify achievements, and how to "
                "structure a CV that works for both bots and humans. You use "
                "the CV Tailor Writer tool to produce the initial rewrite, "
                "then critically review and refine it."
            ),
            llm=llm,
            tools=[tailor_cv_to_job, enhance_cv_section],
            allow_delegation=False,
            verbose=True,
        )

        # ── Task 1: Analyse the job ─────────────────────────────────
        job_task = Task(
            description=(
                "Analyse this job description thoroughly using the "
                "Job Requirements Extractor tool.\n\n"
                f"JOB DESCRIPTION:\n{job_description[:3000]}\n\n"
                "Your structured output must cover: required skills, preferred "
                "skills, key ATS keywords, experience level, key responsibilities, "
                "and any implicit requirements you can infer from the description."
            ),
            expected_output=(
                "A structured JSON breakdown of all job requirements — required skills, "
                "preferred skills, keywords, seniority level, responsibilities, and "
                "any implicit requirements the CV must address."
            ),
            agent=job_analyst,
        )

        # ── Task 2: Gap analysis ────────────────────────────────────
        gap_task = Task(
            description=(
                "Using the job requirements from the Job Analyst, perform a "
                "detailed gap analysis against the candidate's CV.\n\n"
                "Use the Skill Gap Mapper tool — pass the CV's skills and "
                "experience section as 'cv_skills_text' and the job requirements "
                "JSON as 'job_requirements_json'.\n\n"
                f"CV content for the tool:\n{cv_text[:3000]}\n\n"
                "Your analysis must clearly list:\n"
                "- Skills the CV already covers (matched)\n"
                "- Required skills completely absent from the CV (missing)\n"
                "- Skills the CV has that partially transfer (transferable)\n"
                "- The top 3-5 things the CV Writer must add or emphasise"
            ),
            expected_output=(
                "A clear gap analysis with matched skills, missing skills, "
                "transferable skills, and a prioritised list of additions "
                "for the CV Writer to act on."
            ),
            agent=gap_analyst,
            context=[job_task],
        )

        # ── Task 3: Rewrite the CV ──────────────────────────────────
        write_task = Task(
            description=(
                "Using the job requirements (Task 1) and gap analysis (Task 2), "
                "rewrite the CV to maximally match this role.\n\n"
                "Steps:\n"
                "1. Call the CV Tailor Writer tool:\n"
                f"   - cv_text: the original CV (provided below)\n"
                "   - job_requirements_json: use the Job Analyst's structured output\n"
                "2. Review the rewritten CV against the gap analysis.\n"
                "3. If any priority skills from the gap analysis are still missing, "
                "   call the CV Section Enhancer tool for those sections.\n"
                "4. Produce the final output.\n\n"
                f"Original CV:\n{cv_text[:2500]}\n\n"
                "Output ONLY a JSON object with keys:\n"
                "optimized_text, keywords_added (list), changes_made (list),\n"
                "match_percentage (0-100), ats_score (0-100), overall_score (0-100)"
            ),
            expected_output=(
                "A JSON object with the fully tailored CV text, a list of keywords "
                "added, a list of changes made, and match/ats/overall scores."
            ),
            agent=cv_writer,
            context=[job_task, gap_task],
        )

        crew = Crew(
            agents=[job_analyst, gap_analyst, cv_writer],
            tasks=[job_task, gap_task, write_task],
            process=Process.sequential,
            verbose=True,
        )

        try:
            result = crew.kickoff()
            raw = str(result)
            logger.info(f"CVTailoringCrew completed — output {len(raw)} chars")
            return _parse_json(raw, self._default_tailor(cv_text))
        except Exception as e:
            logger.error(f"CVTailoringCrew failed: {e}", exc_info=True)
            return self._default_tailor(cv_text)

    def _default_tailor(self, original_text: str) -> dict:
        return {
            "optimized_text": original_text,
            "keywords_added": [],
            "changes_made": ["Tailoring could not be completed. Check ANTHROPIC_API_KEY in .env."],
            "match_percentage": 0,
            "ats_score": 0,
            "overall_score": 0,
        }
