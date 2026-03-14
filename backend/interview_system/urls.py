from django.urls import path
from . import views

urlpatterns = [
    path('sessions/', views.list_create_sessions, name='interview_sessions'),
    path('sessions/<uuid:session_id>/', views.session_detail, name='session_detail'),
    path('sessions/<uuid:session_id>/intro/', views.intro_chat, name='intro_chat'),
    path('sessions/<uuid:session_id>/intro/stream/', views.stream_intro_chat, name='stream_intro_chat'),
    path('sessions/<uuid:session_id>/start-phase1/', views.start_phase1, name='start_phase1'),
    path('sessions/<uuid:session_id>/answer/', views.submit_answer, name='submit_answer'),
    path('sessions/<uuid:session_id>/complete-phase/', views.complete_phase, name='complete_phase'),
    path('sessions/<uuid:session_id>/review/', views.get_review, name='get_review'),
    path('sessions/<uuid:session_id>/review/chat/', views.review_chat, name='review_chat'),
    path('sessions/<uuid:session_id>/review/stream/', views.stream_review_chat, name='stream_review_chat'),
    path('sessions/<uuid:session_id>/next-phase/', views.next_phase, name='next_phase'),
    path('sessions/<uuid:session_id>/report/', views.get_report, name='get_report'),
    path('sessions/<uuid:session_id>/question-coach/', views.question_coach, name='question_coach'),
    path('sessions/<uuid:session_id>/question-coach/stream/', views.stream_question_coach, name='stream_question_coach'),
    path('tts/', views.tts_endpoint, name='tts'),
    path('transcribe/', views.transcribe_endpoint, name='transcribe'),
]
