from django.urls import path
from . import views

urlpatterns = [
    path('sessions/', views.list_create_sessions),
    path('sessions/<uuid:session_id>/', views.session_detail),
    path('sessions/<uuid:session_id>/messages/', views.session_messages),
    path('sessions/<uuid:session_id>/onboarding/', views.onboarding_chat),
    path('sessions/<uuid:session_id>/onboarding/stream/', views.stream_onboarding_chat),
    path('sessions/<uuid:session_id>/start-roadmap/', views.start_roadmap),
    path('sessions/<uuid:session_id>/chat/', views.general_chat),
    path('sessions/<uuid:session_id>/chat/stream/', views.stream_general_chat),
    path('sessions/<uuid:session_id>/topics/<int:topic_id>/lesson/', views.lesson_chat),
    path('sessions/<uuid:session_id>/topics/<int:topic_id>/lesson/stream/', views.stream_lesson_chat),
    path('sessions/<uuid:session_id>/topics/<int:topic_id>/quiz/', views.quiz_chat),
    path('sessions/<uuid:session_id>/topics/<int:topic_id>/quiz/stream/', views.stream_quiz_chat),
    path('tts/', views.tts),
]
