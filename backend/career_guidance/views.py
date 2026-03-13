import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import GuidanceSession, GuidanceTopic, GuidanceMessage
from .services.guidance_service import (
    generate_greeting,
    chat_onboarding,
    generate_roadmap,
    chat_lesson,
    run_quiz,
    chat_general,
    generate_tts,
)

logger = logging.getLogger(__name__)


def _serialize_topic(t: GuidanceTopic) -> dict:
    return {
        'id': t.id,
        'order': t.order,
        'title': t.title,
        'description': t.description,
        'estimated_days': t.estimated_days,
        'status': t.status,
        'score': t.score,
        'passed': t.passed,
    }


def _serialize_session(s: GuidanceSession) -> dict:
    return {
        'id': str(s.id),
        'goal': s.goal,
        'current_level': s.current_level,
        'time_commitment': s.time_commitment,
        'status': s.status,
        'topics': [_serialize_topic(t) for t in s.topics.all()],
        'created_at': s.created_at.isoformat(),
        'updated_at': s.updated_at.isoformat(),
    }


def _history_for_session(session, topic=None):
    """Build Claude-compatible conversation history from saved messages."""
    qs = session.messages.filter(topic=topic).order_by('created_at')
    history = []
    for m in qs:
        role = 'assistant' if m.role == 'alex' else 'user'
        history.append({'role': role, 'content': m.content})
    return history


def _save_message(session, role, content, topic=None):
    GuidanceMessage.objects.create(session=session, role=role, content=content, topic=topic)


# ─── Sessions ─────────────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def list_create_sessions(request):
    if request.method == 'GET':
        sessions = GuidanceSession.objects.filter(user=request.user)
        return Response([_serialize_session(s) for s in sessions])

    # POST — create new session
    goal = request.data.get('goal', '').strip()
    if not goal:
        return Response({'error': 'goal is required'}, status=status.HTTP_400_BAD_REQUEST)

    session = GuidanceSession.objects.create(
        user=request.user,
        goal=goal,
        status='onboarding',
    )
    return Response(_serialize_session(session), status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def session_messages(request, session_id):
    """Return saved messages for a session to restore chat history on resume."""
    try:
        session = GuidanceSession.objects.get(id=session_id, user=request.user)
    except GuidanceSession.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    topic_id = request.query_params.get('topic')
    if topic_id:
        try:
            topic = GuidanceTopic.objects.get(id=topic_id, session=session)
            qs = session.messages.filter(topic=topic).order_by('created_at')
        except GuidanceTopic.DoesNotExist:
            return Response({'error': 'Topic not found'}, status=status.HTTP_404_NOT_FOUND)
    else:
        qs = session.messages.filter(topic=None).order_by('created_at')

    return Response([{'role': m.role, 'content': m.content} for m in qs])


@api_view(['GET', 'DELETE'])
@permission_classes([IsAuthenticated])
def session_detail(request, session_id):
    try:
        session = GuidanceSession.objects.get(id=session_id, user=request.user)
    except GuidanceSession.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'DELETE':
        session.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    return Response(_serialize_session(session))


# ─── Onboarding chat ───────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def onboarding_chat(request, session_id):
    """
    Handles the intro conversation where Alex learns about the user.
    Empty message triggers Alex's greeting.
    Returns: { response, audio, start_roadmap }
    """
    try:
        session = GuidanceSession.objects.get(id=session_id, user=request.user)
    except GuidanceSession.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    if session.status != 'onboarding':
        return Response({'error': 'Session is not in onboarding'}, status=status.HTTP_400_BAD_REQUEST)

    message = request.data.get('message', '').strip()
    include_audio = request.data.get('include_audio', False)

    # Empty message = greeting
    if not message:
        existing = session.messages.count()
        if existing > 0:
            return Response({'error': 'message is required'}, status=status.HTTP_400_BAD_REQUEST)
        text = generate_greeting(session)
        _save_message(session, 'alex', text)
        audio = generate_tts(text) if include_audio else None
        return Response({'response': text, 'audio': audio, 'start_roadmap': False})

    history = _history_for_session(session)
    _save_message(session, 'user', message)

    result = chat_onboarding(session, message, history)
    _save_message(session, 'alex', result['text'])

    if result['start_roadmap']:
        _extract_and_save_profile(session)

    audio = generate_tts(result['text']) if include_audio else None
    return Response({
        'response': result['text'],
        'audio': audio,
        'start_roadmap': result['start_roadmap'],
    })


def _extract_and_save_profile(session):
    """Ask Claude to extract level and time commitment from onboarding messages."""
    import json as _json
    from ai_agents.services.ai_service import ai_service
    messages_text = '\n'.join(
        f"{'Alex' if m.role == 'alex' else 'User'}: {m.content}"
        for m in session.messages.order_by('created_at')
    )
    prompt = f"""From this onboarding conversation, extract:
1. experience_level — one of: beginner, some_experience, intermediate, experienced
2. time_commitment — a short string like "1 hour per day" or "3 hours per week"

Conversation:
{messages_text}

Return ONLY valid JSON:
{{"experience_level": "...", "time_commitment": "..."}}"""

    try:
        response = ai_service.generate(prompt, max_tokens=100)
        start = response.find('{')
        end = response.rfind('}') + 1
        data = _json.loads(response[start:end])
        session.current_level = data.get('experience_level', 'beginner')
        session.time_commitment = data.get('time_commitment', '')
        session.save()
    except Exception as e:
        logger.warning(f"Profile extraction failed: {e}")
        session.current_level = 'beginner'
        session.save()


# ─── Start roadmap ─────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_roadmap(request, session_id):
    """Generate roadmap topics and transition session to active."""
    try:
        session = GuidanceSession.objects.get(id=session_id, user=request.user)
    except GuidanceSession.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    if session.status != 'onboarding':
        return Response({'error': 'Session is not in onboarding'}, status=status.HTTP_400_BAD_REQUEST)

    messages_text = ' | '.join(
        m.content for m in session.messages.filter(role='user').order_by('created_at')
    )

    try:
        topics_data = generate_roadmap(session, messages_text)
    except Exception as e:
        logger.error(f"Roadmap generation failed: {e}")
        return Response({'error': 'Failed to generate roadmap. Please try again.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    GuidanceTopic.objects.filter(session=session).delete()
    for t in topics_data:
        GuidanceTopic.objects.create(
            session=session,
            order=t.get('order', 1),
            title=t.get('title', ''),
            description=t.get('description', ''),
            estimated_days=t.get('estimated_days', 1),
        )

    first = session.topics.first()
    if first:
        first.status = 'in_progress'
        first.save()

    session.status = 'active'
    session.save()

    return Response(_serialize_session(session))


# ─── Lesson chat ───────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def lesson_chat(request, session_id, topic_id):
    """
    Lesson conversation for a specific topic.
    Empty message → Alex opens the lesson.
    Returns: { response, audio, quiz_ready }
    """
    try:
        session = GuidanceSession.objects.get(id=session_id, user=request.user)
        topic = GuidanceTopic.objects.get(id=topic_id, session=session)
    except (GuidanceSession.DoesNotExist, GuidanceTopic.DoesNotExist):
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    if topic.status == 'complete':
        return Response({'error': 'Topic is already complete'}, status=status.HTTP_400_BAD_REQUEST)

    message = request.data.get('message', '').strip()
    include_audio = request.data.get('include_audio', False)

    if not message:
        existing = session.messages.filter(topic=topic).count()
        if existing > 0:
            return Response({'error': 'message is required'}, status=status.HTTP_400_BAD_REQUEST)
        open_msg = f"Let's start with: {topic.title}"
        result = chat_lesson(session, topic, open_msg, [])
        _save_message(session, 'alex', result['text'], topic=topic)
        audio = generate_tts(result['text']) if include_audio else None
        return Response({'response': result['text'], 'audio': audio, 'quiz_ready': result['quiz_ready']})

    history = _history_for_session(session, topic=topic)
    _save_message(session, 'user', message, topic=topic)

    result = chat_lesson(session, topic, message, history)
    _save_message(session, 'alex', result['text'], topic=topic)

    if topic.status == 'pending':
        topic.status = 'in_progress'
        topic.save()

    audio = generate_tts(result['text']) if include_audio else None
    return Response({'response': result['text'], 'audio': audio, 'quiz_ready': result['quiz_ready']})


# ─── Quiz chat ─────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def quiz_chat(request, session_id, topic_id):
    """
    Quiz conversation for a specific topic.
    Empty message → Alex starts the quiz.
    Returns: { response, audio, quiz_complete, score, passed }
    """
    try:
        session = GuidanceSession.objects.get(id=session_id, user=request.user)
        topic = GuidanceTopic.objects.get(id=topic_id, session=session)
    except (GuidanceSession.DoesNotExist, GuidanceTopic.DoesNotExist):
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    message = request.data.get('message', '').strip()
    include_audio = request.data.get('include_audio', False)

    if not message:
        existing = session.messages.filter(topic=topic).count()
        if existing > 0:
            return Response({'error': 'message is required'}, status=status.HTTP_400_BAD_REQUEST)
        start_msg = f"Great work on the lesson! Now let's do a quick quiz to check your understanding of {topic.title}. Ready? Here's your first question:"
        _save_message(session, 'alex', start_msg, topic=topic)
        audio = generate_tts(start_msg) if include_audio else None
        return Response({'response': start_msg, 'audio': audio, 'quiz_complete': False, 'score': None, 'passed': None})

    history = _history_for_session(session, topic=topic)
    _save_message(session, 'user', message, topic=topic)

    result = run_quiz(session, topic, message, history)
    _save_message(session, 'alex', result['text'], topic=topic)

    if result['quiz_complete']:
        topic.score = result['score']
        topic.passed = result['passed']
        topic.status = 'complete'
        topic.save()

        if result['passed']:
            next_topic = session.topics.filter(order=topic.order + 1).first()
            if next_topic:
                next_topic.status = 'in_progress'
                next_topic.save()
            else:
                session.status = 'complete'
                session.save()

    audio = generate_tts(result['text']) if include_audio else None
    return Response({
        'response': result['text'],
        'audio': audio,
        'quiz_complete': result['quiz_complete'],
        'score': result['score'],
        'passed': result['passed'],
    })


# ─── General chat ──────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def general_chat(request, session_id):
    """
    General coaching conversation (not tied to a specific topic).
    Returns: { response, audio }
    """
    try:
        session = GuidanceSession.objects.get(id=session_id, user=request.user)
    except GuidanceSession.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    message = request.data.get('message', '').strip()
    if not message:
        return Response({'error': 'message is required'}, status=status.HTTP_400_BAD_REQUEST)

    include_audio = request.data.get('include_audio', False)
    history = _history_for_session(session, topic=None)[-20:]
    _save_message(session, 'user', message)

    text = chat_general(session, message, history)
    _save_message(session, 'alex', text)

    audio = generate_tts(text) if include_audio else None
    return Response({'response': text, 'audio': audio})
