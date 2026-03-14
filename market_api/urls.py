from django.urls import path
from .views import MatchAPIView, ResearchAPIView

urlpatterns = [
    # POST http://127.0.0.1:8000/api/match/
    path('match/', MatchAPIView.as_view(), name='match_api'),
    # GET  http://127.0.0.1:8000/api/research/?category=기초화장품&country=JP
    path('research/', ResearchAPIView.as_view(), name='research_api'),
]