"""
Interview Service — Claude handles all question generation, evaluation, and review.
OpenAI TTS handles voice output for Alex the interviewer.
"""
import json
import logging
from typing import List, Dict, Optional

from ai_agents.services.ai_service import ai_service
from ai_agents.services.openai_service import openai_service

logger = logging.getLogger(__name__)

VALID_QUESTION_TYPES = {'multiple_choice', 'short_answer', 'situational', 'behavioural', 'technical'}

def sanitize_question_type(qt: str) -> str:
    """Map any Claude-returned question_type to a valid known type."""
    qt = qt.lower().strip()
    if qt in VALID_QUESTION_TYPES:
        return qt
    if 'multiple' in qt or 'choice' in qt:
        return 'multiple_choice'
    if 'short' in qt or 'written' in qt or 'communication' in qt:
        return 'short_answer'
    if 'situation' in qt or 'judgement' in qt or 'judgment' in qt:
        return 'situational'
    if 'behaviour' in qt or 'behavior' in qt or 'star' in qt or 'motivation' in qt or 'culture' in qt or 'hr' in qt:
        return 'behavioural'
    if 'technical' in qt or 'role' in qt or 'knowledge' in qt or 'pressure' in qt or 'scenario' in qt:
        return 'technical'
    return 'short_answer'  # safe default


ALEX_PERSONA = """You are Alex, an expert interview coach at CareerFromZero — a career development platform.
Your job is to coach and guide users to succeed in real job interviews.
You are warm, professional, encouraging, and direct.
If asked whether you are AI, Claude, ChatGPT, or any other AI system, respond:
"I'm Alex, your interview coach at CareerFromZero. I'm here to help you land your dream job — let's focus on that!"
Never break character. Never discuss AI systems or competitors."""


def generate_phase1_questions(career_goal: str, experience_level: str, interview_type: str) -> List[Dict]:
    """
    Generate 10 Phase 1 written screening questions using Claude.
    Returns a list of question dicts.
    """
    prompt = f"""Generate exactly 10 interview screening questions for this candidate:

Career Goal / Job Description: {career_goal}
Experience Level: {experience_level}
Interview Type: {interview_type}

Question breakdown:
- 4 multiple choice questions (role knowledge basics)
- 3 short written answer questions (1-3 sentences, grammar and clarity assessed)
- 3 situational judgement questions (multiple choice, 4 options each)

IMPORTANT: Base questions on REAL interview questions asked at top companies for this exact role and level.

Return ONLY valid JSON array, no other text:
[
  {{
    "order": 1,
    "question_type": "multiple_choice",
    "section": "Role Knowledge",
    "question_text": "...",
    "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
    "correct_answer": "A) ...",
    "ideal_answer_guide": "Explanation of why this is correct..."
  }},
  {{
    "order": 2,
    "question_type": "short_answer",
    "section": "Written Communication",
    "question_text": "...",
    "options": null,
    "correct_answer": null,
    "ideal_answer_guide": "What a good answer should include: key points, tone, structure..."
  }},
  ...
]"""

    response = ai_service.generate(prompt, system=ALEX_PERSONA, max_tokens=3000, temperature=0.7)

    # Extract JSON from response
    start = response.find('[')
    end = response.rfind(']') + 1
    json_str = response[start:end]
    questions = json.loads(json_str)
    for q in questions:
        q['question_type'] = sanitize_question_type(q.get('question_type', 'short_answer'))
    return questions


def generate_phase2_questions(career_goal: str, experience_level: str, interview_type: str) -> List[Dict]:
    """Generate 15 Phase 2 conversational interview questions."""
    prompt = f"""Generate exactly 15 interview questions for a conversational job interview:

Career Goal / Job Description: {career_goal}
Experience Level: {experience_level}
Interview Type: {interview_type}

Structure:
- Round 1 (questions 1-5): Motivation & Background — "Why this role?", background, goals
- Round 2 (questions 6-12): Behavioural STAR format — past experiences, challenges, achievements
- Round 3 (questions 13-15): Culture & Values — feedback style, work preferences, teamwork

IMPORTANT: Use REAL interview questions from top companies. Adjust difficulty for {experience_level} level.
Behavioural questions must require STAR format answers (Situation, Task, Action, Result).

Return ONLY valid JSON array:
[
  {{
    "order": 1,
    "question_type": "behavioural",
    "section": "Motivation & Background",
    "question_text": "...",
    "options": null,
    "correct_answer": null,
    "ideal_answer_guide": "What a strong answer includes: STAR elements, key points..."
  }},
  ...
]"""

    response = ai_service.generate(prompt, system=ALEX_PERSONA, max_tokens=3500, temperature=0.7)
    start = response.find('[')
    end = response.rfind(']') + 1
    questions = json.loads(response[start:end])
    for q in questions:
        q['question_type'] = sanitize_question_type(q.get('question_type', 'short_answer'))
    return questions


def generate_phase3_questions(career_goal: str, experience_level: str, interview_type: str) -> List[Dict]:
    """Generate 10 Phase 3 deep dive questions."""
    prompt = f"""Generate exactly 10 challenging deep-dive interview questions:

Career Goal / Job Description: {career_goal}
Experience Level: {experience_level}
Interview Type: {interview_type}

Structure:
- Round 1 (questions 1-5): Technical/Role-specific — demonstrate actual job knowledge
- Round 2 (questions 6-8): Pressure scenarios — real workplace crisis situations
- Round 3 (questions 9-10): Ambition — adjusted for {experience_level} level

IMPORTANT: These must be HARD, real questions from senior-level interviews at top companies.
Scenarios must be realistic workplace situations requiring critical thinking.

Return ONLY valid JSON array:
[
  {{
    "order": 1,
    "question_type": "technical",
    "section": "Technical Knowledge",
    "question_text": "...",
    "options": null,
    "correct_answer": null,
    "ideal_answer_guide": "What an excellent answer covers..."
  }},
  ...
]"""

    response = ai_service.generate(prompt, system=ALEX_PERSONA, max_tokens=3500, temperature=0.7)
    start = response.find('[')
    end = response.rfind(']') + 1
    questions = json.loads(response[start:end])
    for q in questions:
        q['question_type'] = sanitize_question_type(q.get('question_type', 'short_answer'))
    return questions


def evaluate_multiple_choice(question, user_answer: str) -> Dict:
    """Evaluate a multiple choice answer — simple match."""
    is_correct = user_answer.strip().lower().startswith(question.correct_answer.strip().lower()[0].lower())
    return {
        'score': 10.0 if is_correct else 0.0,
        'is_correct': is_correct,
        'feedback': f"Correct! {question.ideal_answer_guide}" if is_correct else f"The correct answer is: {question.correct_answer}. {question.ideal_answer_guide}",
        'needs_review': not is_correct,
    }


def evaluate_written_answer(question, user_answer: str) -> Dict:
    """Use Claude to evaluate a written/behavioural/technical answer."""
    prompt = f"""Evaluate this interview answer. Be fair but honest.

Question: {question.question_text}
Question Type: {question.question_type}
Ideal Answer Guide: {question.ideal_answer_guide}

Candidate's Answer: {user_answer}

Evaluate on:
1. Relevance — did they answer what was asked?
2. Quality — depth, specifics, examples
3. Communication — grammar, clarity, professionalism
4. Completeness — did they cover key points?

Return ONLY valid JSON:
{{
  "score": <0-10 float>,
  "is_correct": <true if score >= 6, false otherwise>,
  "feedback": "<2-3 sentence specific feedback mentioning what was good and what to improve>",
  "needs_review": <true if score < 7>
}}"""

    response = ai_service.generate(prompt, system=ALEX_PERSONA, max_tokens=500, temperature=0.3)
    start = response.find('{')
    end = response.rfind('}') + 1
    result = json.loads(response[start:end])
    return result


def evaluate_answer(question, user_answer: str) -> Dict:
    """Route to correct evaluator based on question type."""
    if question.question_type in ('multiple_choice', 'situational'):
        return evaluate_multiple_choice(question, user_answer)
    return evaluate_written_answer(question, user_answer)


def calculate_phase_score(session, phase: int) -> float:
    """Calculate the average score for a phase."""
    from interview_system.models import InterviewAnswer, InterviewQuestion
    questions = InterviewQuestion.objects.filter(session=session, phase=phase)
    answers = InterviewAnswer.objects.filter(question__in=questions)
    if not answers.exists():
        return 0.0
    total = sum(a.score or 0 for a in answers)
    return round((total / (answers.count() * 10)) * 100, 1)


def generate_review_opening(session, phase: int) -> str:
    """Generate Alex's opening message for the review session."""
    score_field = f'phase{phase}_score'
    score = getattr(session, score_field) or 0
    passed = score >= 60 if phase == 1 else (score >= 65 if phase == 2 else score >= 70)

    if passed:
        return f"Well done! You scored {score}% on Phase {phase} — you passed! Let me go through a few points to help you do even better next time. We'll focus on the questions where you can improve."
    else:
        return f"You scored {score}% on Phase {phase} — just below the pass mark. Don't worry at all, this is exactly what practice is for. Let me go through each question you missed so you understand exactly what interviewers are looking for."


def generate_review_explanation(question, answer, career_goal: str) -> str:
    """Claude generates a coaching explanation for a wrong/weak answer."""
    prompt = f"""You are Alex, an interview coach. Explain to a candidate why their answer was weak and how to improve it.
Be encouraging, specific, and give a real example of a strong answer.

Job Context: {career_goal}
Question: {question.question_text}
Their Answer: {answer.answer_text}
Score: {answer.score}/10
Your feedback: {answer.feedback}
Ideal Answer Guide: {question.ideal_answer_guide}

Write a coaching explanation in 2-3 sentences. Be warm and encouraging.
Start with something positive if possible, then explain the improvement.
Do NOT use bullet points. Write as natural speech (it will be spoken aloud)."""

    return ai_service.generate(prompt, system=ALEX_PERSONA, max_tokens=300, temperature=0.7)


def generate_intro_greeting(session) -> str:
    """Generate Alex's first greeting message for the intro phase."""
    prompt = f"""You are meeting a job candidate for the very first time at the start of an interview simulation.

Career Goal: {session.career_goal}
Experience Level: {session.experience_level}
Interview Type: {session.interview_type}

Write your opening greeting in 2-3 natural sentences:
1. Introduce yourself as Alex from CareerFromZero
2. Welcome them warmly
3. Ask how they're feeling today

Be warm and natural — like a real interviewer. Do NOT mention the interview phases yet."""

    return ai_service.generate(prompt, system=ALEX_PERSONA, max_tokens=150, temperature=0.8)


def chat_intro(session, user_message: str, conversation_history: List[Dict]) -> Dict:
    """
    Handle intro conversation. Returns { text, start_phase1 }.
    start_phase1 is True when the candidate is ready to begin.
    """
    system = f"""{ALEX_PERSONA}

You are in the PRE-INTERVIEW introduction phase.
Career Goal: {session.career_goal}
Experience Level: {session.experience_level}
Interview Type: {session.interview_type}

Guide the conversation naturally in this order:
1. Respond warmly to how they're feeling
2. Ask 1-2 warm-up questions (e.g. "Tell me a bit about yourself" or "What drew you to this kind of role?")
3. Explain the 3 phases:
   - Phase 1: Written screening test (10 questions, tests role knowledge)
   - Phase 2: Conversational HR/behavioural interview (15 questions)
   - Phase 3: Deep-dive technical interview (10 challenging questions)
4. Ask if they are ready to begin Phase 1

When the candidate clearly says they are ready to begin / start / yes / let's go — add [READY_TO_START] at the very end of your response.

Rules:
- Be warm, encouraging, and conversational
- Keep responses to 2-4 sentences
- Stay on topic — this is interview preparation
- Do NOT add [READY_TO_START] until they confirm they're ready"""

    messages = [{"role": "system", "content": system}] + conversation_history + [{"role": "user", "content": user_message}]
    response = ai_service.chat(messages, max_tokens=350, temperature=0.8)

    start_phase1 = '[READY_TO_START]' in response
    clean_response = response.replace('[READY_TO_START]', '').strip()
    return {'text': clean_response, 'start_phase1': start_phase1}


def chat_question_coaching(session, question, answer, user_message: str, conversation_history: List[Dict]) -> str:
    """Handle coaching conversation about a specific answered question."""
    system = f"""{ALEX_PERSONA}

You are coaching the candidate on a specific interview question they just answered.
Career Goal: {session.career_goal}
Question: {question.question_text}
Question Type: {question.question_type}
Their Answer: {answer.answer_text}
Score: {answer.score}/10
Your evaluation: {answer.feedback}
Ideal Answer Guide: {question.ideal_answer_guide}

Your job:
- Help them understand what was strong and what to improve
- If they ask for an example answer, give a brief one
- If they ask follow-up questions, answer helpfully
- If they go off topic, gently redirect to interview prep
- Keep responses to 3-4 sentences max
- Be encouraging and specific"""

    messages = [{"role": "system", "content": system}] + conversation_history + [{"role": "user", "content": user_message}]
    return ai_service.chat(messages, max_tokens=350, temperature=0.7)


def chat_review(session, phase: int, user_message: str, conversation_history: List[Dict]) -> str:
    """
    Handle a user message during review session. Claude responds as Alex.
    Keeps the conversation focused on the interview questions and coaching.
    """
    from interview_system.models import InterviewQuestion, InterviewAnswer
    weak_questions = []
    questions = InterviewQuestion.objects.filter(session=session, phase=phase)
    for q in questions:
        try:
            if q.answer.needs_review:
                weak_questions.append(f"Q: {q.question_text}\nTheir answer: {q.answer.answer_text}\nIdeal: {q.ideal_answer_guide}")
        except Exception:
            pass

    system = f"""{ALEX_PERSONA}

You are currently in a POST-INTERVIEW REVIEW SESSION for Phase {phase}.
Career goal: {session.career_goal}
Experience level: {session.experience_level}

Questions the candidate needs to review:
{chr(10).join(weak_questions) if weak_questions else 'All answers were strong — do a brief positive review.'}

Your job: Coach them through their weak answers.
- If they ask a question about an answer, explain it clearly with examples.
- If they go off topic, gently redirect: "That's a good thought — let's keep focused on your interview preparation."
- Be encouraging and specific. Speak naturally (responses will be read aloud).
- Keep responses under 4 sentences."""

    messages = [{"role": "system", "content": system}] + conversation_history + [{"role": "user", "content": user_message}]
    return ai_service.chat(messages, max_tokens=400, temperature=0.7)


def generate_final_report(session) -> Dict:
    """Generate the full final report after all 3 phases."""
    from interview_system.models import InterviewQuestion, InterviewAnswer

    all_answers = []
    for phase in [1, 2, 3]:
        questions = InterviewQuestion.objects.filter(session=session, phase=phase)
        for q in questions:
            try:
                all_answers.append(f"Phase {phase} | {q.question_type} | Score: {q.answer.score}/10 | Q: {q.question_text[:100]}")
            except Exception:
                pass

    prompt = f"""Generate a comprehensive interview performance report.

Candidate: Applied for {session.career_goal}
Level: {session.experience_level}
Phase 1 Score: {session.phase1_score}%
Phase 2 Score: {session.phase2_score}%
Phase 3 Score: {session.phase3_score}%
Overall Score: {session.overall_score}%

Answer summary:
{chr(10).join(all_answers)}

Return ONLY valid JSON:
{{
  "summary": "<2-3 sentence overall assessment>",
  "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
  "improvements": ["<area 1 with specific advice>", "<area 2 with specific advice>"],
  "communication_score": <0-10>,
  "technical_score": <0-10>,
  "problem_solving_score": <0-10>,
  "culture_fit_score": <0-10>,
  "encouragement": "<2 sentence personalised encouragement to retake and improve>",
  "certificate_worthy": <true if overall >= 70>
}}"""

    response = ai_service.generate(prompt, system=ALEX_PERSONA, max_tokens=800, temperature=0.5)
    start = response.find('{')
    end = response.rfind('}') + 1
    return json.loads(response[start:end])


def text_to_speech(text: str) -> Optional[bytes]:
    """Convert text to speech using OpenAI TTS. Returns MP3 bytes or None."""
    try:
        return openai_service.text_to_speech(text, voice='nova')
    except Exception as e:
        logger.error("TTS error: %s", e)
        return None


def transcribe_audio(audio_file) -> str:
    """Transcribe audio using OpenAI Whisper."""
    return openai_service.transcribe(audio_file)
