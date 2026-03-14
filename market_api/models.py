from django.db import models


class HsClassification(models.Model):
    """카테고리별 HS 코드 판정 결과 및 근거 저장"""
    category = models.CharField(max_length=100, unique=True)
    hs_code = models.CharField(max_length=10)
    reason = models.TextField()                      # RAG 판정 근거
    classified_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.category} → {self.hs_code}"


class MarketStat(models.Model):
    category = models.CharField(max_length=100)
    hs_code = models.CharField(max_length=10)
    country = models.CharField(max_length=2)  # US, JP
    year = models.CharField(max_length=4)     # 2021, 2022...
    amount = models.BigIntegerField()         # 수출액(USD)
    weight = models.BigIntegerField()         # 수출중량(kg)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('category', 'country', 'year')


class MarketResearch(models.Model):
    """카테고리·국가별 시장 리서치 데이터 (월별 스냅샷)"""
    category = models.CharField(max_length=100)       # 기초화장품, 메이크업 등
    country = models.CharField(max_length=10)          # US, JP
    research_month = models.CharField(max_length=7)    # 2026-03

    # 구조화된 시장 데이터 (JSON)
    market_size = models.JSONField(default=dict, blank=True)
    # {"value": "$18.4B", "growth_rate": "4.2%", "cagr": "6.96%", "forecast": "..."}

    kbeauty_share = models.JSONField(default=dict, blank=True)
    # {"share": "15.8%", "details": "..."}

    trends = models.JSONField(default=dict, blank=True)
    # {"ingredients": ["Retinol", "CICA", ...], "functions": ["안티에이징", ...], "details": "..."}

    channels = models.JSONField(default=dict, blank=True)
    # {"online": ["Amazon", "Sephora"], "offline": ["대형마트"], "details": "..."}

    competitors = models.JSONField(default=dict, blank=True)
    # {"brands": [{"name": "...", "description": "..."}], "details": "..."}

    raw_summary = models.TextField(blank=True)         # LLM 생성 종합 요약
    sources = models.JSONField(default=list, blank=True)  # 출처 URL 리스트

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('category', 'country', 'research_month')

    def __str__(self):
        return f"{self.category} - {self.country} ({self.research_month})"