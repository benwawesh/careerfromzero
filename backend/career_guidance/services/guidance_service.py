"""
Career Guidance Service — Alex the career coach.
Handles onboarding, roadmap generation, lessons, quizzes, and general coaching.
"""
import json
import logging
from typing import List, Dict

from ai_agents.services.ai_service import ai_service
from ai_agents.services.openai_service import openai_service

logger = logging.getLogger(__name__)

ALEX_PERSONA = """You are Alex, an expert career coach at CareerFromZero — a career development platform.
Your job is to help users achieve their career goals through personalised coaching, structured learning plans, and skill development.
You are warm, encouraging, practical, and direct. You believe anyone can achieve their career goal with the right plan and consistency.
Keep all responses concise — maximum 3 short paragraphs. Never write long essays. Get to the point quickly.
If asked whether you are AI, Claude, ChatGPT, or any other AI system, respond:
"I'm Alex, your career coach at CareerFromZero. I'm here to help you reach your goals — let's focus on that!"
Never break character. Never discuss AI systems or competitors."""


def generate_greeting(session) -> str:
    """Alex's opening message for a new guidance session."""
    prompt = f"""A user has started a new career guidance session with the goal: "{session.goal}"

Write a warm, energetic opening message as Alex.
- Welcome them and acknowledge their goal enthusiastically
- Tell them you'll ask a few quick questions to personalise their roadmap
- First question: Ask about their current experience level with this field (complete beginner / some experience / intermediate / experienced)
- Keep it to 3-4 sentences max"""

    messages = [
        {"role": "system", "content": ALEX_PERSONA},
        {"role": "user", "content": prompt},
    ]
    return ai_service.chat(messages, max_tokens=200, temperature=0.8)


def chat_onboarding(session, user_message: str, conversation_history: List[Dict], stream: bool = False):
    """
    Onboarding conversation. Alex asks about level, time commitment, learning preferences.
    When enough info is gathered, returns start_roadmap=True (or generator when stream=True).
    """
    system = f"""{ALEX_PERSONA}

You are onboarding a new user for career coaching.
Their career goal: {session.goal}

Your job in this conversation:
1. Find out their current experience level (beginner / some experience / intermediate / experienced)
2. Find out how much time they can dedicate (e.g. 1 hour/day, a few hours/week)
3. Ask if they have any specific areas they want to focus on or are struggling with

Once you have their experience level AND time commitment, add [ROADMAP_READY] at the very end of your response.

Rules:
- Be conversational — one or two questions at a time, not a long form
- Keep responses to 2-4 sentences
- Be encouraging and specific to their goal: {session.goal}
- Do NOT add [ROADMAP_READY] until you have both their level AND time commitment"""

    messages = [{"role": "system", "content": system}] + conversation_history + [{"role": "user", "content": user_message}]
    if stream:
        return ai_service.chat_stream(messages, max_tokens=350, temperature=0.8)
    response = ai_service.chat(messages, max_tokens=350, temperature=0.8)

    start_roadmap = '[ROADMAP_READY]' in response
    clean = response.replace('[ROADMAP_READY]', '').strip()
    return {'text': clean, 'start_roadmap': start_roadmap}


def generate_roadmap(session, onboarding_summary: str) -> List[Dict]:
    """
    Generate a structured learning roadmap based on the session goal and onboarding info.
    Returns a list of topic dicts.
    """
    prompt = f"""Create a structured learning roadmap for this user:

Career Goal: {session.goal}
Current Level: {session.current_level}
Time Commitment: {session.time_commitment}
Additional Context: {onboarding_summary}

Create a step-by-step roadmap of learning topics. Each topic should be completable in 1-5 days.
Topics should build on each other logically (fundamentals first, advanced later).
Aim for 6-12 topics total depending on complexity of the goal.

Return ONLY valid JSON array, no other text:
[
  {{
    "order": 1,
    "title": "Topic title",
    "description": "What this topic covers and why it matters for the goal",
    "estimated_days": 2
  }},
  ...
]"""

    response = ai_service.generate(prompt, system=ALEX_PERSONA, max_tokens=2000, temperature=0.7)
    start = response.find('[')
    end = response.rfind(']') + 1
    return json.loads(response[start:end])


def chat_lesson(session, topic, user_message: str, conversation_history: List[Dict], stream: bool = False):
    """
    Lesson conversation for a specific topic.
    Alex teaches the topic through conversation.
    When the lesson content is fully covered, returns quiz_ready=True (or generator when stream=True).
    """
    system = f"""{ALEX_PERSONA}

You are teaching this topic in a career coaching session.
Career Goal: {session.goal}
Current Level: {session.current_level}
Topic: {topic.title}
Topic Description: {topic.description}

Your job:
- Teach this topic conversationally, like a personal tutor
- Break it into digestible chunks — don't dump everything at once
- Ask the user questions to check understanding
- Give practical examples and tasks they can try
- When you have covered the main content of this topic and the user shows understanding, add [QUIZ_READY] at the very end

Rules:
- Keep responses to 3-5 sentences unless giving a code/task example
- Be practical — focus on what they need to know for their goal: {session.goal}
- Do NOT add [QUIZ_READY] until the core topic content has been covered"""

    messages = [{"role": "system", "content": system}] + conversation_history + [{"role": "user", "content": user_message}]
    if stream:
        return ai_service.chat_stream(messages, max_tokens=400, temperature=0.7)
    response = ai_service.chat(messages, max_tokens=400, temperature=0.7)

    quiz_ready = '[QUIZ_READY]' in response
    clean = response.replace('[QUIZ_READY]', '').strip()
    return {'text': clean, 'quiz_ready': quiz_ready}


def run_quiz(session, topic, user_message: str, conversation_history: List[Dict], stream: bool = False):
    """
    Quiz conversation for a topic. Alex asks 3-5 questions.
    Returns score and passed when complete (or generator when stream=True).
    Sentinel: [QUIZ_COMPLETE:score] e.g. [QUIZ_COMPLETE:80]
    """
    system = f"""{ALEX_PERSONA}

You are running a quiz to assess understanding of a completed lesson.
Career Goal: {session.goal}
Topic: {topic.title}
Topic Description: {topic.description}

Your job:
- Ask 3-5 quiz questions one at a time (mix of knowledge checks and practical application)
- After each answer, give brief feedback (correct/incorrect + quick explanation)
- After the final question, calculate a score (0-100) and give overall feedback
- Then add [QUIZ_COMPLETE:score] at the very end (e.g. [QUIZ_COMPLETE:80])
- A score of 70 or above = passed. Below 70 = needs review.

Rules:
- Keep each response concise (2-4 sentences + the question or feedback)
- Be encouraging regardless of score
- Do NOT add [QUIZ_COMPLETE:score] until all questions are done and scored"""

    messages = [{"role": "system", "content": system}] + conversation_history + [{"role": "user", "content": user_message}]
    if stream:
        return ai_service.chat_stream(messages, max_tokens=400, temperature=0.7)
    response = ai_service.chat(messages, max_tokens=400, temperature=0.7)

    score = None
    passed = None
    quiz_complete = False

    if '[QUIZ_COMPLETE:' in response:
        quiz_complete = True
        try:
            score_str = response.split('[QUIZ_COMPLETE:')[1].split(']')[0].strip()
            score = float(score_str)
            passed = score >= 70
        except (ValueError, IndexError):
            score = 0.0
            passed = False

    clean = response
    if '[QUIZ_COMPLETE:' in response:
        clean = response[:response.find('[QUIZ_COMPLETE:')].strip()

    return {
        'text': clean,
        'quiz_complete': quiz_complete,
        'score': score,
        'passed': passed,
    }


def chat_general(session, user_message: str, conversation_history: List[Dict], stream: bool = False):
    """General coaching chat — for questions, motivation, advice outside lessons."""
    completed = session.topics.filter(status='complete').count()
    total = session.topics.count()
    current = session.topics.filter(status='in_progress').first()

    system = f"""{ALEX_PERSONA}

You are the personal career coach for this user.
Career Goal: {session.goal}
Current Level: {session.current_level}
Progress: {completed}/{total} topics completed
Current Topic: {current.title if current else 'None'}

Your job:
- Answer any career-related questions honestly and practically
- Motivate and encourage them
- Give advice specific to their goal: {session.goal}
- If they ask about topics outside their roadmap, help briefly then redirect to their plan
- Keep responses to 3-5 sentences"""

    messages = [{"role": "system", "content": system}] + conversation_history + [{"role": "user", "content": user_message}]
    if stream:
        return ai_service.chat_stream(messages, max_tokens=400, temperature=0.7)
    return ai_service.chat(messages, max_tokens=400, temperature=0.7)


def generate_tts(text: str) -> str | None:
    """Generate TTS audio for Alex's response. Returns base64 string or None."""
    import base64
    try:
        audio_bytes = openai_service.text_to_speech(text)
        if audio_bytes:
            return base64.b64encode(audio_bytes).decode('utf-8')
        return None
    except Exception as e:
        logger.warning(f"TTS failed: {e}")
        return None
