from django.urls import path
from . import views

urlpatterns = [
    path('sessions/', views.list_create_sessions, name='interview_sessions'),
    path('sessions/<uuid:session_id>/', views.session_detail, name='session_detail'),
    path('sessions/<uuid:session_id>/answer/', views.submit_answer, name='submit_answer'),
    path('sessions/<uuid:session_id>/complete-phase/', views.complete_phase, name='complete_phase'),
    path('sessions/<uuid:session_id>/review/', views.get_review, name='get_review'),
    path('sessions/<uuid:session_id>/review/chat/', views.review_chat, name='review_chat'),
    path('sessions/<uuid:session_id>/next-phase/', views.next_phase, name='next_phase'),
    path('sessions/<uuid:session_id>/report/', views.get_report, name='get_report'),
    path('tts/', views.tts_endpoint, name='tts'),
    path('transcribe/', views.transcribe_endpoint, name='transcribe'),
]
