"""
Base Agent Class for AI Integration
Provides foundation for all specialized agents in the system
"""

from decouple import config
from .services import ollama_service


class CareerAgent:
    """
    Base class for all Career AI agents.
    Uses Ollama directly via ollama_service for all LLM calls.
    CrewAI integration is available lazily for future multi-agent workflows.
    """

    def __init__(
        self,
        role: str,
        goal: str,
        backstory: str,
        verbose: bool = False
    ):
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.verbose = verbose
        self._crew_agent = None  # lazy-loaded only if needed

    def _get_crew_agent(self):
        """Lazy-load a CrewAI Agent only when explicitly needed."""
        if self._crew_agent is None:
            try:
                from crewai import Agent, LLM
                llm = LLM(
                    model=f"claude/{config('CLAUDE_MODEL', default='claude-haiku-4-5-20251001')}",
                    api_key=config('ANTHROPIC_API_KEY', default=''),
                )
                self._crew_agent = Agent(
                    role=self.role,
                    goal=self.goal,
                    backstory=self.backstory,
                    verbose=self.verbose,
                    allow_delegation=False,
                    llm=llm,
                )
            except Exception as e:
                print(f"CrewAI agent init failed (non-critical): {e}")
        return self._crew_agent

    def generate_response(self, prompt: str, temperature: float = 0.7) -> str:
        """Generate a response using Ollama directly."""
        system_prompt = f"You are a {self.role}. {self.goal} {self.backstory}"

        try:
            response = ollama_service.generate(
                prompt=prompt,
                system=system_prompt,
                temperature=temperature
            )
            return response
        except Exception as e:
            print(f"Error generating response: {e}")
            return ""


class BaseCVAgent(CareerAgent):
    """Base class for CV-related agents"""
    
    def __init__(self):
        super().__init__(
            role="Expert CV Writer and Career Consultant",
            goal="Help users create professional, ATS-optimized CVs that stand out",
            backstory="You are an experienced career coach and professional CV writer with 10+ years of experience helping job seekers land their dream jobs. You understand ATS systems, industry trends, and what recruiters look for."
        )


class BaseJobAgent(CareerAgent):
    """Base class for job-related agents"""
    
    def __init__(self):
        super().__init__(
            role="Job Search Specialist",
            goal="Help users find and apply to relevant job opportunities",
            backstory="You are a career specialist who understands the job market, knows how to match candidates with suitable positions, and helps navigate the application process effectively."
        )


class BaseInterviewAgent(CareerAgent):
    """Base class for interview-related agents"""
    
    def __init__(self):
        super().__init__(
            role="Interview Coach and Preparation Expert",
            goal="Help users prepare for and practice interviews",
            backstory="You are an expert interviewer and career coach who has conducted hundreds of interviews across various industries. You know what employers look for and how to help candidates perform their best."
        )