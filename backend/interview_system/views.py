import base64
import json as _json
import logging

from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import (
    InterviewSession,
    InterviewQuestion,
    InterviewAnswer,
    ReviewMessage,
)
from .services.interview_service import (
    generate_phase1_questions,
    generate_phase2_questions,
    generate_phase3_questions,
    evaluate_answer,
    calculate_phase_score,
    generate_review_opening,
    generate_intro_greeting,
    chat_intro,
    chat_review,
    chat_question_coaching,
    generate_final_report,
    text_to_speech,
    transcribe_audio,
)

logger = logging.getLogger(__name__)


def _sse_stream(token_gen, save_fn, tts_fn, sentinel_fn):
    """
    token_gen: generator yielding text tokens from Claude
    save_fn(clean_text): saves the response to DB
    tts_fn(clean_text): returns base64 audio or None
    sentinel_fn(full_text): returns (clean_text, metadata_dict)
    """
    def generator():
        full_text = ""
        try:
            for token in token_gen:
                full_text += token
                yield f"data: {_json.dumps({'type': 'text', 'content': token})}\n\n"
        except Exception as e:
            yield f"data: {_json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            return

        clean_text, metadata = sentinel_fn(full_text)

        try:
            save_fn(clean_text)
        except Exception as e:
            logger.error("Failed to save streamed response: %s", e)

        audio = None
        try:
            audio = tts_fn(clean_text)
        except Exception:
            pass

        done_event = {'type': 'done', 'full_text': clean_text, **metadata}
        if audio:
            done_event['audio'] = audio

        yield f"data: {_json.dumps(done_event)}\n\n"

    response = StreamingHttpResponse(generator(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


# ── Helpers ───────────────────────────────────────────────────────────────────

def _serialize_question(q: InterviewQuestion) -> dict:
    answer = None
    try:
        a = q.answer
        answer = {
            'answer_text': a.answer_text,
            'score': a.score,
            'feedback': a.feedback,
            'is_correct': a.is_correct,
            'needs_review': a.needs_review,
            'submitted_at': a.submitted_at.isoformat(),
        }
    except InterviewAnswer.DoesNotExist:
        pass

    return {
        'id': q.id,
        'phase': q.phase,
        'order': q.order,
        'question_type': q.question_type,
        'section': q.section,
        'question_text': q.question_text,
        'options': q.options,
        # Only expose correct_answer after the question has been answered
        'correct_answer': q.correct_answer if answer else None,
        'ideal_answer_guide': q.ideal_answer_guide if answer else None,
        'answer': answer,
    }


def _serialize_session(session: InterviewSession, include_questions: bool = False) -> dict:
    data = {
        'id': str(session.id),
        'career_goal': session.career_goal,
        'experience_level': session.experience_level,
        'interview_type': session.interview_type,
        'mode': session.mode,
        'status': session.status,
        'phase1_score': session.phase1_score,
        'phase2_score': session.phase2_score,
        'phase3_score': session.phase3_score,
        'overall_score': session.overall_score,
        'phase1_passed': session.phase1_passed,
        'phase2_passed': session.phase2_passed,
        'phase3_passed': session.phase3_passed,
        'created_at': session.created_at.isoformat(),
        'updated_at': session.updated_at.isoformat(),
    }
    if include_questions:
        # Determine current phase from status
        phase_map = {
            'intro': 1,
            'phase1_test': 1,
            'phase1_review': 1,
            'phase2_interview': 2,
            'phase2_review': 2,
            'phase3_interview': 3,
            'phase3_review': 3,
            'complete': 3,
        }
        current_phase = phase_map.get(session.status, 1)
        questions = session.questions.filter(phase=current_phase)
        data['questions'] = [_serialize_question(q) for q in questions]
        data['current_phase'] = current_phase
    return data


def _current_phase_number(session: InterviewSession) -> int:
    phase_map = {
        'intro': 1,
        'phase1_test': 1,
        'phase1_review': 1,
        'phase2_interview': 2,
        'phase2_review': 2,
        'phase3_interview': 3,
        'phase3_review': 3,
        'complete': 3,
    }
    return phase_map.get(session.status, 1)


def _save_questions(session: InterviewSession, questions: list, phase: int):
    """Bulk-create InterviewQuestion objects for a phase."""
    objs = []
    for q in questions:
        objs.append(InterviewQuestion(
            session=session,
            phase=phase,
            order=q.get('order', 0),
            question_type=q.get('question_type', 'short_answer'),
            question_text=q.get('question_text', ''),
            options=q.get('options'),
            correct_answer=q.get('correct_answer'),
            ideal_answer_guide=q.get('ideal_answer_guide'),
            section=q.get('section'),
        ))
    InterviewQuestion.objects.bulk_create(objs)


# ── Views ─────────────────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def list_create_sessions(request):
    """
    GET  — list the authenticated user's sessions.
    POST — create a new session and generate Phase 1 questions.
    """
    if request.method == 'GET':
        sessions = InterviewSession.objects.filter(user=request.user)
        return Response([_serialize_session(s) for s in sessions])

    # POST — create session
    career_goal = request.data.get('career_goal', '').strip()
    experience_level = request.data.get('experience_level', '').strip()
    interview_type = request.data.get('interview_type', '').strip()
    mode = request.data.get('mode', 'text').strip()

    if not career_goal or not experience_level or not interview_type:
        return Response(
            {'error': 'career_goal, experience_level, and interview_type are required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    session = InterviewSession.objects.create(
        user=request.user,
        career_goal=career_goal,
        experience_level=experience_level,
        interview_type=interview_type,
        mode=mode,
        status='intro',
    )

    return Response(_serialize_session(session), status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def session_detail(request, session_id):
    """GET — return session detail including questions for the current phase."""
    session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
    return Response(_serialize_session(session, include_questions=True))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_answer(request, session_id):
    """
    POST — submit an answer for a question.
    Body: { question_id, answer_text }
    """
    session = get_object_or_404(InterviewSession, id=session_id, user=request.user)

    question_id = request.data.get('question_id')
    answer_text = request.data.get('answer_text', '').strip()

    if not question_id or not answer_text:
        return Response(
            {'error': 'question_id and answer_text are required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    question = get_object_or_404(InterviewQuestion, id=question_id, session=session)

    # Prevent double-answering
    if hasattr(question, 'answer'):
        return Response(
            {'error': 'This question has already been answered.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        evaluation = evaluate_answer(question, answer_text)
    except Exception as e:
        logger.error("Answer evaluation failed: %s", e)
        return Response({'error': f'Evaluation failed: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    answer = InterviewAnswer.objects.create(
        question=question,
        answer_text=answer_text,
        score=evaluation.get('score'),
        feedback=evaluation.get('feedback'),
        is_correct=evaluation.get('is_correct'),
        needs_review=evaluation.get('needs_review', False),
    )

    # Find the next unanswered question in the same phase
    current_phase = question.phase
    answered_ids = InterviewAnswer.objects.filter(
        question__session=session, question__phase=current_phase
    ).values_list('question_id', flat=True)
    next_question_qs = InterviewQuestion.objects.filter(
        session=session, phase=current_phase
    ).exclude(id__in=answered_ids).order_by('order').first()

    return Response({
        'question_id': question.id,
        'score': answer.score,
        'feedback': answer.feedback,
        'is_correct': answer.is_correct,
        'needs_review': answer.needs_review,
        'next_question': _serialize_question(next_question_qs) if next_question_qs else None,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_phase(request, session_id):
    """
    POST — mark the current phase complete, calculate score, advance to review status.
    """
    session = get_object_or_404(InterviewSession, id=session_id, user=request.user)

    phase = _current_phase_number(session)

    # Verify all questions for this phase have been answered
    total_questions = InterviewQuestion.objects.filter(session=session, phase=phase).count()
    answered = InterviewAnswer.objects.filter(question__session=session, question__phase=phase).count()
    if answered < total_questions:
        return Response(
            {'error': f'Not all questions answered. {answered}/{total_questions} complete.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    score = calculate_phase_score(session, phase)
    pass_threshold = {1: 60.0, 2: 65.0, 3: 70.0}.get(phase, 60.0)
    passed = score >= pass_threshold

    # Persist score
    setattr(session, f'phase{phase}_score', score)
    setattr(session, f'phase{phase}_passed', passed)

    # Advance status to review
    next_status = {1: 'phase1_review', 2: 'phase2_review', 3: 'phase3_review'}.get(phase, 'complete')
    session.status = next_status
    session.save()

    # Generate Alex's opening review message
    opening = generate_review_opening(session, phase)
    review_msg = ReviewMessage.objects.create(
        session=session,
        phase=phase,
        role='alex',
        content=opening,
    )

    return Response({
        'phase': phase,
        'score': score,
        'passed': passed,
        'pass_threshold': pass_threshold,
        'status': session.status,
        'opening_message': opening,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_review(request, session_id):
    """GET — return all review messages for the current phase."""
    session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
    phase = _current_phase_number(session)

    messages = ReviewMessage.objects.filter(session=session, phase=phase)
    return Response({
        'phase': phase,
        'status': session.status,
        'messages': [
            {
                'id': m.id,
                'role': m.role,
                'content': m.content,
                'question_ref_id': m.question_ref_id,
                'created_at': m.created_at.isoformat(),
            }
            for m in messages
        ],
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def review_chat(request, session_id):
    """
    POST — send a message in the review session, get Alex's coaching response.
    Body: { message }
    Returns: { response, audio (optional base64) }
    """
    session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
    phase = _current_phase_number(session)

    user_message = request.data.get('message', '').strip()
    if not user_message:
        return Response({'error': 'message is required.'}, status=status.HTTP_400_BAD_REQUEST)

    # Save user's message
    ReviewMessage.objects.create(
        session=session,
        phase=phase,
        role='user',
        content=user_message,
    )

    # Build conversation history for Claude (exclude the message we just saved so we append it in the service)
    history_qs = ReviewMessage.objects.filter(session=session, phase=phase).order_by('created_at')
    conversation_history = []
    for m in history_qs:
        role = 'assistant' if m.role == 'alex' else 'user'
        conversation_history.append({'role': role, 'content': m.content})

    # Remove the last entry (user message we just added) — it's appended inside chat_review
    if conversation_history and conversation_history[-1]['role'] == 'user':
        conversation_history = conversation_history[:-1]

    try:
        alex_response = chat_review(session, phase, user_message, conversation_history)
    except Exception as e:
        logger.error("Review chat failed: %s", e)
        return Response({'error': f'Chat failed: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Save Alex's response
    ReviewMessage.objects.create(
        session=session,
        phase=phase,
        role='alex',
        content=alex_response,
    )

    # Optionally generate TTS if session is in voice mode
    audio_b64 = None
    if session.mode == 'voice':
        audio_bytes = text_to_speech(alex_response)
        if audio_bytes:
            audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')

    return Response({
        'response': alex_response,
        'audio': audio_b64,
        'format': 'mp3' if audio_b64 else None,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def next_phase(request, session_id):
    """
    POST — advance session to the next interview phase and generate questions.
    """
    session = get_object_or_404(InterviewSession, id=session_id, user=request.user)

    transitions = {
        'phase1_review': ('phase2_interview', 2),
        'phase2_review': ('phase3_interview', 3),
    }

    if session.status not in transitions:
        return Response(
            {'error': f'Cannot advance to next phase from status "{session.status}".'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    next_status, next_phase_num = transitions[session.status]

    # Generate questions for the next phase
    try:
        if next_phase_num == 2:
            questions_data = generate_phase2_questions(
                session.career_goal, session.experience_level, session.interview_type
            )
        else:
            questions_data = generate_phase3_questions(
                session.career_goal, session.experience_level, session.interview_type
            )
    except Exception as e:
        logger.error("Phase %s question generation failed: %s", next_phase_num, e)
        return Response(
            {'error': f'Failed to generate Phase {next_phase_num} questions: {e}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    session.status = next_status
    session.save()

    _save_questions(session, questions_data, phase=next_phase_num)

    # Return session detail with new questions
    return Response(_serialize_session(session, include_questions=True))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_report(request, session_id):
    """GET — return the final performance report."""
    session = get_object_or_404(InterviewSession, id=session_id, user=request.user)

    # Mark as complete if coming from phase3_review
    if session.status == 'phase3_review':
        # Calculate overall score from all phases
        scores = [s for s in [session.phase1_score, session.phase2_score, session.phase3_score] if s is not None]
        if scores:
            session.overall_score = round(sum(scores) / len(scores), 1)
        session.status = 'complete'
        session.save()

    if session.status != 'complete':
        return Response(
            {'error': 'Report is only available after all phases are complete.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        report = generate_final_report(session)
    except Exception as e:
        logger.error("Final report generation failed: %s", e)
        return Response({'error': f'Report generation failed: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({
        'session_id': str(session.id),
        'phase1_score': session.phase1_score,
        'phase2_score': session.phase2_score,
        'phase3_score': session.phase3_score,
        'overall_score': session.overall_score,
        'phase1_passed': session.phase1_passed,
        'phase2_passed': session.phase2_passed,
        'phase3_passed': session.phase3_passed,
        'report': report,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def intro_chat(request, session_id):
    """
    POST — handle intro conversation with Alex.
    Body: { message: "" } for greeting, { message: "..." } for conversation.
    Returns: { response, audio, start_phase1 }
    """
    session = get_object_or_404(InterviewSession, id=session_id, user=request.user)

    if session.status != 'intro':
        return Response({'error': 'Session is not in intro phase.'}, status=status.HTTP_400_BAD_REQUEST)

    user_message = request.data.get('message', '').strip()

    # Load existing conversation history (phase=0 for intro)
    history_qs = ReviewMessage.objects.filter(session=session, phase=0).order_by('created_at')
    conversation_history = []
    for m in history_qs:
        role = 'assistant' if m.role == 'alex' else 'user'
        conversation_history.append({'role': role, 'content': m.content})

    # Empty message with no history → generate greeting
    if not user_message and not conversation_history:
        try:
            greeting = generate_intro_greeting(session)
        except Exception as e:
            logger.error("Intro greeting failed: %s", e)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        ReviewMessage.objects.create(session=session, phase=0, role='alex', content=greeting)

        audio_b64 = None
        if session.mode == 'voice':
            audio_bytes = text_to_speech(greeting)
            if audio_bytes:
                audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')

        return Response({'response': greeting, 'audio': audio_b64, 'start_phase1': False})

    if not user_message:
        return Response({'error': 'message is required.'}, status=status.HTTP_400_BAD_REQUEST)

    # Save user message
    ReviewMessage.objects.create(session=session, phase=0, role='user', content=user_message)

    try:
        result = chat_intro(session, user_message, conversation_history)
    except Exception as e:
        logger.error("Intro chat failed: %s", e)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    alex_text = result['text']
    ReviewMessage.objects.create(session=session, phase=0, role='alex', content=alex_text)

    audio_b64 = None
    if session.mode == 'voice':
        audio_bytes = text_to_speech(alex_text)
        if audio_bytes:
            audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')

    return Response({
        'response': alex_text,
        'audio': audio_b64,
        'start_phase1': result['start_phase1'],
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_phase1(request, session_id):
    """
    POST — generate Phase 1 questions and advance session from intro → phase1_test.
    Returns: full session with questions.
    """
    session = get_object_or_404(InterviewSession, id=session_id, user=request.user)

    if session.status != 'intro':
        return Response({'error': 'Session is not in intro phase.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        questions_data = generate_phase1_questions(
            session.career_goal, session.experience_level, session.interview_type
        )
    except Exception as e:
        logger.error("Phase 1 question generation failed: %s", e)
        return Response({'error': f'Failed to generate questions: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    session.status = 'phase1_test'
    session.save()

    _save_questions(session, questions_data, phase=1)

    return Response(_serialize_session(session, include_questions=True))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def question_coach(request, session_id):
    """
    POST — coaching chat about a specific answered question.
    Body: { question_id, message }
    Returns: { response, audio }
    """
    session = get_object_or_404(InterviewSession, id=session_id, user=request.user)

    question_id = request.data.get('question_id')
    user_message = request.data.get('message', '').strip()

    if not question_id or not user_message:
        return Response({'error': 'question_id and message are required.'}, status=status.HTTP_400_BAD_REQUEST)

    question = get_object_or_404(InterviewQuestion, id=question_id, session=session)

    try:
        answer = question.answer
    except InterviewAnswer.DoesNotExist:
        return Response({'error': 'Question has not been answered yet.'}, status=status.HTTP_400_BAD_REQUEST)

    # Load coaching history for this question
    history_qs = ReviewMessage.objects.filter(session=session, question_ref=question).order_by('created_at')
    conversation_history = []
    for m in history_qs:
        role = 'assistant' if m.role == 'alex' else 'user'
        conversation_history.append({'role': role, 'content': m.content})

    # Save user message
    ReviewMessage.objects.create(
        session=session, phase=question.phase, role='user',
        content=user_message, question_ref=question
    )

    try:
        alex_response = chat_question_coaching(session, question, answer, user_message, conversation_history)
    except Exception as e:
        logger.error("Question coaching failed: %s", e)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    ReviewMessage.objects.create(
        session=session, phase=question.phase, role='alex',
        content=alex_response, question_ref=question
    )

    audio_b64 = None
    if session.mode == 'voice':
        audio_bytes = text_to_speech(alex_response)
        if audio_bytes:
            audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')

    return Response({
        'response': alex_response,
        'audio': audio_b64,
        'format': 'mp3' if audio_b64 else None,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def tts_endpoint(request):
    """
    POST — convert text to speech.
    Body: { text }
    Returns: { audio: <base64 mp3>, format: "mp3" }
    """
    text = request.data.get('text', '').strip()
    if not text:
        return Response({'error': 'text is required.'}, status=status.HTTP_400_BAD_REQUEST)

    audio_bytes = text_to_speech(text)
    if not audio_bytes:
        return Response({'error': 'TTS failed.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
    return Response({'audio': audio_b64, 'format': 'mp3'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def transcribe_endpoint(request):
    """
    POST — transcribe an uploaded audio file.
    Form-data: { audio: <file> }
    Returns: { text: "<transcription>" }
    """
    audio_file = request.FILES.get('audio')
    if not audio_file:
        return Response({'error': 'audio file is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        audio_file.seek(0)
        text = transcribe_audio(audio_file)
    except Exception as e:
        logger.error("Transcription failed: %s", e)
        return Response({'error': f'Transcription failed: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({'text': text})


# ── Streaming endpoints ────────────────────────────────────────────────────────

@csrf_exempt
def stream_intro_chat(request, session_id):
    """
    POST — SSE streaming version of intro_chat.
    Streams Claude tokens, then fires a 'done' event with clean text + optional audio.
    """
    from django.http import JsonResponse
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    from rest_framework_simplejwt.authentication import JWTAuthentication
    try:
        auth = JWTAuthentication()
        user_auth = auth.authenticate(request)
        if user_auth is None:
            from django.http import JsonResponse
            return JsonResponse({'error': 'Authentication required'}, status=401)
        request.user = user_auth[0]
    except Exception:
        from django.http import JsonResponse
        return JsonResponse({'error': 'Authentication required'}, status=401)

    session = get_object_or_404(InterviewSession, id=session_id, user=request.user)

    if session.status != 'intro':
        from django.http import JsonResponse
        return JsonResponse({'error': 'Session is not in intro phase.'}, status=400)

    import json as _json2
    try:
        body = _json2.loads(request.body)
    except Exception:
        body = {}

    user_message = body.get('message', '').strip()
    include_audio = body.get('include_audio', False)

    if not user_message:
        from django.http import JsonResponse
        return JsonResponse({'error': 'message is required.'}, status=400)

    # Load existing conversation history (phase=0 for intro)
    history_qs = ReviewMessage.objects.filter(session=session, phase=0).order_by('created_at')
    conversation_history = []
    for m in history_qs:
        role = 'assistant' if m.role == 'alex' else 'user'
        conversation_history.append({'role': role, 'content': m.content})

    # Save user message
    ReviewMessage.objects.create(session=session, phase=0, role='user', content=user_message)

    token_gen = chat_intro(session, user_message, conversation_history, stream=True)

    def save_fn(clean_text):
        ReviewMessage.objects.create(session=session, phase=0, role='alex', content=clean_text)

    def tts_fn(clean_text):
        if session.mode == 'voice' and include_audio:
            audio_bytes = text_to_speech(clean_text)
            if audio_bytes:
                return base64.b64encode(audio_bytes).decode('utf-8')
        return None

    def sentinel_fn(full_text):
        start_phase1 = '[READY_TO_START]' in full_text
        clean = full_text.replace('[READY_TO_START]', '').strip()
        return clean, {'start_phase1': start_phase1}

    return _sse_stream(token_gen, save_fn, tts_fn, sentinel_fn)


@csrf_exempt
def stream_review_chat(request, session_id):
    """
    POST — SSE streaming version of review_chat.
    """
    if request.method != 'POST':
        from django.http import JsonResponse
        return JsonResponse({'error': 'POST required'}, status=405)

    from rest_framework_simplejwt.authentication import JWTAuthentication
    try:
        auth = JWTAuthentication()
        user_auth = auth.authenticate(request)
        if user_auth is None:
            from django.http import JsonResponse
            return JsonResponse({'error': 'Authentication required'}, status=401)
        request.user = user_auth[0]
    except Exception:
        from django.http import JsonResponse
        return JsonResponse({'error': 'Authentication required'}, status=401)

    session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
    phase = _current_phase_number(session)

    import json as _json2
    try:
        body = _json2.loads(request.body)
    except Exception:
        body = {}

    user_message = body.get('message', '').strip()
    include_audio = body.get('include_audio', False)

    if not user_message:
        from django.http import JsonResponse
        return JsonResponse({'error': 'message is required.'}, status=400)

    # Save user's message
    ReviewMessage.objects.create(session=session, phase=phase, role='user', content=user_message)

    # Build conversation history
    history_qs = ReviewMessage.objects.filter(session=session, phase=phase).order_by('created_at')
    conversation_history = []
    for m in history_qs:
        role = 'assistant' if m.role == 'alex' else 'user'
        conversation_history.append({'role': role, 'content': m.content})

    # Remove the last user entry — it's appended inside chat_review
    if conversation_history and conversation_history[-1]['role'] == 'user':
        conversation_history = conversation_history[:-1]

    token_gen = chat_review(session, phase, user_message, conversation_history, stream=True)

    def save_fn(clean_text):
        ReviewMessage.objects.create(session=session, phase=phase, role='alex', content=clean_text)

    def tts_fn(clean_text):
        if session.mode == 'voice' and include_audio:
            audio_bytes = text_to_speech(clean_text)
            if audio_bytes:
                return base64.b64encode(audio_bytes).decode('utf-8')
        return None

    def sentinel_fn(full_text):
        return full_text, {}

    return _sse_stream(token_gen, save_fn, tts_fn, sentinel_fn)


@csrf_exempt
def stream_question_coach(request, session_id):
    """
    POST — SSE streaming version of question_coach.
    Body: { question_id, message, include_audio }
    """
    if request.method != 'POST':
        from django.http import JsonResponse
        return JsonResponse({'error': 'POST required'}, status=405)

    from rest_framework_simplejwt.authentication import JWTAuthentication
    try:
        auth = JWTAuthentication()
        user_auth = auth.authenticate(request)
        if user_auth is None:
            from django.http import JsonResponse
            return JsonResponse({'error': 'Authentication required'}, status=401)
        request.user = user_auth[0]
    except Exception:
        from django.http import JsonResponse
        return JsonResponse({'error': 'Authentication required'}, status=401)

    session = get_object_or_404(InterviewSession, id=session_id, user=request.user)

    import json as _json2
    try:
        body = _json2.loads(request.body)
    except Exception:
        body = {}

    question_id = body.get('question_id')
    user_message = body.get('message', '').strip()
    include_audio = body.get('include_audio', False)

    if not question_id or not user_message:
        from django.http import JsonResponse
        return JsonResponse({'error': 'question_id and message are required.'}, status=400)

    question = get_object_or_404(InterviewQuestion, id=question_id, session=session)

    try:
        answer = question.answer
    except InterviewAnswer.DoesNotExist:
        from django.http import JsonResponse
        return JsonResponse({'error': 'Question has not been answered yet.'}, status=400)

    # Load coaching history for this question
    history_qs = ReviewMessage.objects.filter(session=session, question_ref=question).order_by('created_at')
    conversation_history = []
    for m in history_qs:
        role = 'assistant' if m.role == 'alex' else 'user'
        conversation_history.append({'role': role, 'content': m.content})

    # Save user message
    ReviewMessage.objects.create(
        session=session, phase=question.phase, role='user',
        content=user_message, question_ref=question
    )

    token_gen = chat_question_coaching(session, question, answer, user_message, conversation_history, stream=True)

    def save_fn(clean_text):
        ReviewMessage.objects.create(
            session=session, phase=question.phase, role='alex',
            content=clean_text, question_ref=question
        )

    def tts_fn(clean_text):
        if session.mode == 'voice' and include_audio:
            audio_bytes = text_to_speech(clean_text)
            if audio_bytes:
                return base64.b64encode(audio_bytes).decode('utf-8')
        return None

    def sentinel_fn(full_text):
        return full_text, {}

    return _sse_stream(token_gen, save_fn, tts_fn, sentinel_fn)
