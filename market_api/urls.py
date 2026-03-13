from django.urls import path
from .views import MatchAPIView # views.py에 정의할 클래스

urlpatterns = [
    # 최종 주소: http://127.0.0.1:8000/api/match/
    path('match/', MatchAPIView.as_view(), name='match_api'),
]