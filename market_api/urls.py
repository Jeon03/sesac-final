from django.urls import path
from .views import MatchAPIView, ResearchAPIView, TradeStatsView

urlpatterns = [
    # POST http://127.0.0.1:8000/api/match/
    path('match/', MatchAPIView.as_view(), name='match_api'),
    # GET  http://127.0.0.1:8000/api/research/?category=기초화장품&country=JP
    path('research/', ResearchAPIView.as_view(), name='research_api'),
    # GET  http://127.0.0.1:8000/api/trade-stats/?category=기초화장품&country=US
    path('trade-stats/', TradeStatsView.as_view(), name='trade_stats_api'),
]