from django.db import models


class ProductRanking(models.Model):
    """채널별 Top10 랭킹 스냅샷 (DB1)"""
    PLATFORM_CHOICES = [
        ('Ulta', 'Ulta'),
        ('Sephora', 'Sephora'),
        ('Qoo10', 'Qoo10'),
        ('Rakuten', 'Rakuten'),
    ]
    COUNTRY_CHOICES = [('US', 'US'), ('JP', 'JP')]

    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    country = models.CharField(max_length=2, choices=COUNTRY_CHOICES)
    rank = models.PositiveSmallIntegerField()
    platform_item_id = models.CharField(max_length=100)  # Ulta/Sephora: product_id, Qoo10: item_id, Rakuten: shop_id_item_id
    title = models.TextField()
    brand = models.CharField(max_length=200, blank=True, default='')
    price = models.CharField(max_length=100, blank=True, default='')
    rating = models.FloatField(null=True, blank=True)
    reviews_count = models.IntegerField(null=True, blank=True)
    url = models.URLField(max_length=500)
    collected_at = models.DateTimeField()

    class Meta:
        unique_together = ('platform', 'platform_item_id', 'collected_at')
        ordering = ['platform', 'rank']

    def __str__(self):
        return f"[{self.platform}] #{self.rank} {self.title[:40]}"


class ProductReview(models.Model):
    """채널별 상품 리뷰 (DB2)"""
    platform = models.CharField(max_length=20)
    country = models.CharField(max_length=2)
    platform_item_id = models.CharField(max_length=100, db_index=True)
    review_id = models.CharField(max_length=100)   # 플랫폼 원본 ID
    author = models.CharField(max_length=200, blank=True, default='')
    rating = models.FloatField(null=True, blank=True)
    # 제목: Ulta=headline, Sephora=Title, Qoo10/Rakuten=없음
    title_original = models.TextField(blank=True, default='')
    title_ko = models.TextField(blank=True, default='')
    # 본문 원문 / 영어번역 / 한국어번역
    body_original = models.TextField(blank=True, default='')  # 원문 (EN or JP)
    body_en = models.TextField(blank=True, default='')        # 영어 (JP→EN, EN은 원문과 동일)
    body_ko = models.TextField(blank=True, default='')        # 한국어 번역
    review_date = models.DateField(null=True, blank=True)
    # KeyBERT + GPT 분류 결과
    keybert_keywords = models.JSONField(default=list, blank=True)   # ["moisturizing", "hydration", ...]
    primary_category = models.CharField(max_length=50, blank=True, default='')  # "효과_성분"
    categories = models.JSONField(default=list, blank=True)         # ["효과_성분", "재구매_추천"]

    class Meta:
        unique_together = ('platform', 'platform_item_id', 'review_id')

    def __str__(self):
        return f"[{self.platform}] {self.platform_item_id} - {self.author}"


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


class MetaAdSummary(models.Model):
    """Meta 광고 라이브러리 브랜드별 90일 요약"""
    CHANNEL_CHOICES = [
        ('ulta', 'Ulta'),
        ('sephora', 'Sephora'),
        ('qoo10', 'Qoo10'),
        ('rakuten', 'Rakuten'),
    ]
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    brand = models.CharField(max_length=200)
    total_ads = models.IntegerField(default=0)
    image_ads = models.IntegerField(default=0)
    video_ads = models.IntegerField(default=0)
    image_ratio = models.FloatField(default=0)
    video_ratio = models.FloatField(default=0)
    latest_ad_date = models.DateField(null=True, blank=True)
    recent_30d_ads = models.IntegerField(default=0)
    latest_ad_text = models.TextField(blank=True, default='')
    page_id = models.CharField(max_length=50, blank=True, default='')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('channel', 'brand')

    def __str__(self):
        return f"[{self.channel}] {self.brand}"


class MetaAd(models.Model):
    """Meta 광고 라이브러리 개별 광고 레코드"""
    CHANNEL_CHOICES = MetaAdSummary.CHANNEL_CHOICES
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    brand = models.CharField(max_length=200, db_index=True)
    library_id = models.CharField(max_length=50, blank=True, default='')
    media_type = models.CharField(max_length=10, blank=True, default='')  # image / video
    start_date = models.DateField(null=True, blank=True)
    ad_text = models.TextField(blank=True, default='')
    page_id = models.CharField(max_length=50, blank=True, default='')
    market = models.CharField(max_length=2, blank=True, default='')  # US / JP
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('channel', 'library_id')
        indexes = [
            models.Index(fields=['channel', 'brand']),
            models.Index(fields=['market']),
        ]

    def __str__(self):
        return f"[{self.channel}] {self.brand} - {self.library_id}"


class ReviewAnalysisCache(models.Model):
    """상품별 리뷰 분석 결과 캐시"""
    platform = models.CharField(max_length=20)
    platform_item_id = models.CharField(max_length=100)
    result = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('platform', 'platform_item_id')

    def __str__(self):
        return f"[{self.platform}] {self.platform_item_id}"
