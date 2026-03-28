from django.urls import path
from .views import MatchAPIView, ResearchAPIView, TradeStatsView, RankingsView, ReviewAnalysisView, ReviewSummaryView, MetaAdView, CountryRecommendView, AdStrategyView, AdImageView

urlpatterns = [
    # POST http://127.0.0.1:8000/api/match/
    path('match/', MatchAPIView.as_view(), name='match_api'),
    # GET  http://127.0.0.1:8000/api/research/?category=기초화장품&country=JP
    path('research/', ResearchAPIView.as_view(), name='research_api'),
    # GET  http://127.0.0.1:8000/api/trade-stats/?category=기초화장품&country=US
    path('trade-stats/', TradeStatsView.as_view(), name='trade_stats_api'),
    # GET  http://127.0.0.1:8000/api/rankings/?country=US
    path('rankings/', RankingsView.as_view(), name='rankings_api'),
    # GET  http://127.0.0.1:8000/api/review-analysis/?platform=Sephora&item_id=P519160
    path('review-analysis/', ReviewAnalysisView.as_view(), name='review_analysis_api'),
    # GET  http://127.0.0.1:8000/api/review-summary/?country=US
    path('review-summary/', ReviewSummaryView.as_view(), name='review_summary_api'),
    # GET  http://127.0.0.1:8000/api/meta-ads/?country=US
    path('meta-ads/', MetaAdView.as_view(), name='meta_ads_api'),
    # POST http://127.0.0.1:8000/api/country-recommend/
    path('country-recommend/', CountryRecommendView.as_view(), name='country_recommend_api'),
    # POST http://127.0.0.1:8000/api/ad-strategy/
    path('ad-strategy/', AdStrategyView.as_view(), name='ad_strategy_api'),
    # POST http://127.0.0.1:8000/api/ad-image/
    path('ad-image/', AdImageView.as_view(), name='ad_image_api'),
]