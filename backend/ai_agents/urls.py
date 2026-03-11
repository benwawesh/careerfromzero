from django.urls import path
from .views_ai import (
    WriteCVView, RevampCVView,
    CustomizeCVView, WriteCoverLetterView,
    CareerGuidanceView, AIJobMatchView,
    TokenBalanceCheckView,
)

urlpatterns = [
    # CV Agent
    path('cv/write/', WriteCVView.as_view(), name='ai_cv_write'),
    path('cv/revamp/', RevampCVView.as_view(), name='ai_cv_revamp'),

    # CV Customization Agent
    path('cv/customize/', CustomizeCVView.as_view(), name='ai_cv_customize'),
    path('cv/cover-letter/', WriteCoverLetterView.as_view(), name='ai_cover_letter'),

    # Career Guidance Agent
    path('career/guidance/', CareerGuidanceView.as_view(), name='ai_career_guidance'),

    # Job Matching Agent
    path('jobs/match/', AIJobMatchView.as_view(), name='ai_job_match'),

    # Token info
    path('tokens/', TokenBalanceCheckView.as_view(), name='ai_token_balance'),
]
