from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from .services.main import run_analysis
from .services.research_engine import get_research_dict
from .services.hs_map import get_hs_code, COUNTRY_CODE_MAP, get_fetch_years
from .services.trass_service import fetch_api
from .models import MarketStat, ProductRanking, ReviewAnalysisCache, MetaAdSummary


class MatchAPIView(APIView):
    def post(self, request):
        category = request.data.get('category')

        if not category:
            return Response({"error": "카테고리를 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)

        # 통합 파이프라인 실행 (HS 판정 -> 수출통계 -> 시장리서치)
        result = run_analysis(category)

        if "error" in result:
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(result, status=status.HTTP_200_OK)


class TradeStatsView(APIView):
    """
    카테고리·국가별 연도별 수출 통계 조회.
    MarketStat DB 캐시 우선, 없으면 트라스 API 호출 후 저장.
    GET /api/trade-stats/?category=기초화장품&country=US
    """
    def get(self, request):
        category = request.query_params.get("category")
        country = request.query_params.get("country")
        if not category or not country:
            return Response({"error": "category, country 파라미터 필요"}, status=400)

        hs_code = get_hs_code(category)
        if not hs_code:
            return Response({"error": f"HS 코드 없음: {category}"}, status=404)

        country_code = COUNTRY_CODE_MAP.get(country, country)

        # DB 캐시 확인
        cached = list(
            MarketStat.objects.filter(category=category, country=country)
            .order_by("year")
            .values("year", "amount", "weight")
        )
        if cached:
            return Response({"hs_code": hs_code, "country": country, "stats": cached})

        # 트라스 API 호출 후 DB 저장
        stats = []
        for year in get_fetch_years():
            data = fetch_api(hs_code, country_code, year)
            if data:
                MarketStat.objects.update_or_create(
                    category=category,
                    country=country,
                    year=year,
                    defaults={
                        "hs_code": hs_code,
                        "amount": data["amount"],
                        "weight": data["weight"],
                    },
                )
                stats.append({"year": year, "amount": data["amount"], "weight": data["weight"]})

        if not stats:
            return Response({"error": "수출 통계 데이터를 가져올 수 없습니다."}, status=404)

        return Response({"hs_code": hs_code, "country": country, "stats": stats})


class RankingsView(APIView):
    """
    국가별 최신 Top5 랭킹 조회.
    GET /api/rankings/?country=US   → Ulta, Sephora 각 Top5
    GET /api/rankings/?country=JP   → Qoo10, Rakuten 각 Top5
    """
    PLATFORM_MAP = {
        "US": ["Ulta", "Sephora"],
        "JP": ["Qoo10", "Rakuten"],
    }

    def get(self, request):
        country = request.query_params.get("country", "US").upper()
        platforms = self.PLATFORM_MAP.get(country)
        if not platforms:
            return Response({"error": "country는 US 또는 JP"}, status=400)

        result = {}
        for platform in platforms:
            rows = (
                ProductRanking.objects
                .filter(platform=platform, country=country, rank__lte=10)
                .order_by("rank")
                .values("rank", "platform_item_id", "title", "brand",
                        "price", "rating", "reviews_count", "url")
            )
            result[platform] = list(rows)

        return Response({"country": country, "rankings": result})


class ReviewAnalysisView(APIView):
    """
    상품별 리뷰 분석 결과 조회 (ReviewAnalysisCache에서 읽기).
    GET /api/review-analysis/?platform=Sephora&item_id=P519160
    """

    def get(self, request):
        platform = request.query_params.get("platform")
        item_id = request.query_params.get("item_id")
        if not platform or not item_id:
            return Response({"error": "platform, item_id 파라미터 필요"}, status=400)

        cache = (
            ReviewAnalysisCache.objects
            .filter(platform=platform, platform_item_id=item_id)
            .first()
        )
        if not cache:
            return Response({"error": "분석 데이터 없음"}, status=404)

        return Response(cache.result)


class ReviewSummaryView(APIView):
    """
    국가별 Top10 상품 리뷰를 GPT로 통합 요약.
    GET /api/review-summary/?country=US
    Response: {country, platforms: {Sephora: {positive_summary, negative_summary, top_products}, ...}}
    """
    PLATFORM_MAP = {"US": ["Ulta", "Sephora"], "JP": ["Qoo10", "Rakuten"]}

    def get(self, request):
        import os
        from openai import OpenAI

        country = request.query_params.get("country", "US").upper()
        platforms = self.PLATFORM_MAP.get(country)
        if not platforms:
            return Response({"error": "country는 US 또는 JP"}, status=400)

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        result = {}

        for platform in platforms:
            rows = list(
                ProductRanking.objects
                .filter(platform=platform, country=country, rank__lte=10)
                .order_by("rank")
                .values("rank", "platform_item_id", "title", "brand", "rating")
            )

            positives, negatives = [], []
            for row in rows:
                cache = ReviewAnalysisCache.objects.filter(
                    platform=platform,
                    platform_item_id=row["platform_item_id"],
                ).first()
                if cache and cache.result:
                    sr = cache.result.get("sample_reviews", {})
                    label = (row["brand"] or row["title"] or "")[:20]
                    if sr.get("positive"):
                        positives.append(f"[{label}] {sr['positive']}")
                    if sr.get("negative"):
                        negatives.append(f"[{label}] {sr['negative']}")

            pos_text = "\n".join(positives) or "데이터 없음"
            neg_text = "\n".join(negatives) or "데이터 없음"

            prompt = (
                f"다음은 {platform} Top 10 베스트셀러 스킨케어 상품들의 소비자 리뷰 요약입니다.\n\n"
                f"[긍정 리뷰]\n{pos_text}\n\n"
                f"[부정 리뷰]\n{neg_text}\n\n"
                "위 리뷰들을 종합하여 아래 형식으로 각각 2~3문장씩 통합 요약하세요.\n"
                "긍정: ...\n부정: ...\n\n한국어로 작성하세요."
            )
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0.3,
            )
            text = resp.choices[0].message.content.strip()

            pos_summary, neg_summary = "", ""
            for line in text.splitlines():
                if line.startswith("긍정:"):
                    pos_summary = line.replace("긍정:", "").strip()
                elif line.startswith("부정:"):
                    neg_summary = line.replace("부정:", "").strip()

            result[platform] = {
                "top_products": [
                    {"rank": r["rank"], "brand": r["brand"] or "", "title": r["title"] or "", "rating": r["rating"]}
                    for r in rows
                ],
                "positive_summary": pos_summary or text,
                "negative_summary": neg_summary,
            }

        return Response({"country": country, "platforms": result})


class ResearchAPIView(APIView):
    """시장 리서치 데이터 단독 조회 API"""
    def get(self, request):
        category = request.query_params.get('category')
        country = request.query_params.get('country')

        if not category:
            return Response({"error": "category 파라미터를 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)

        countries = [country] if country else ["US", "JP"]
        result = {}

        for c in countries:
            data = get_research_dict(category, c)
            if data:
                result[c] = data

        if not result:
            return Response({"error": "해당 카테고리의 리서치 데이터가 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        return Response(result, status=status.HTTP_200_OK)


class CountryRecommendView(APIView):
    """
    제품 정보 기반 최적 진출 국가 추천
    POST /api/country-recommend/
    Body: {"product_name": "...", "category": "...", "ingredients": "...", "effects": "..."}
    """
    def post(self, request):
        product_name = request.data.get("product_name", "")
        category     = request.data.get("category", "")
        ingredients  = request.data.get("ingredients", "")
        effects      = request.data.get("effects", "")

        if not category:
            return Response({"error": "category 파라미터가 필요합니다."}, status=400)

        from .services.country_recommender import recommend_countries
        result = recommend_countries(
            product_name=product_name,
            category=category,
            ingredients=ingredients,
            effects=effects,
        )

        if "error" in result:
            return Response(result, status=404)

        return Response(result, status=200)


class AdStrategyView(APIView):
    """
    AI 마케팅 전략 제안
    POST /api/ad-strategy/
    Body: {"product_name": "...", "category": "...", "ingredients": "...", "effects": "...", "country": "US"}
    """
    def post(self, request):
        product_name = request.data.get("product_name", "")
        category     = request.data.get("category", "")
        ingredients  = request.data.get("ingredients", "")
        effects      = request.data.get("effects", "")
        country      = request.data.get("country", "US").upper()

        if not category:
            return Response({"error": "category 파라미터가 필요합니다."}, status=400)

        from .services.ad_strategy import generate_ad_strategy
        result = generate_ad_strategy(
            product_name=product_name,
            category=category,
            ingredients=ingredients,
            effects=effects,
            country=country,
        )

        if "error" in result:
            return Response(result, status=404)

        return Response(result, status=200)


class MetaAdView(APIView):
    """
    채널별 Meta 광고 요약 조회 (90일 기준 total_ads 상위 4개)
    GET /api/meta-ads/?country=US   → ulta + sephora 상위 4개
    GET /api/meta-ads/?country=JP   → qoo10 + rakuten 상위 4개
    """
    CHANNEL_MAP = {
        "US": ["ulta", "sephora"],
        "JP": ["qoo10", "rakuten"],
    }

    def get(self, request):
        country = request.query_params.get("country", "US").upper()
        channels = self.CHANNEL_MAP.get(country)
        if not channels:
            return Response({"error": "country는 US 또는 JP"}, status=400)

        rows = (
            MetaAdSummary.objects
            .filter(channel__in=channels)
            .order_by("-total_ads")
            .values(
                "channel", "brand", "total_ads", "image_ads", "video_ads",
                "image_ratio", "video_ratio", "latest_ad_date",
                "recent_30d_ads", "latest_ad_text", "page_id", "updated_at",
            )
        )
        # 브랜드 중복 제거 (ulta/sephora 동일 브랜드 → total_ads 높은 쪽 유지)
        seen_brands = {}
        for row in rows:
            brand = row["brand"]
            if brand not in seen_brands:
                seen_brands[brand] = row
        deduped = sorted(seen_brands.values(), key=lambda x: x["total_ads"], reverse=True)[:4]
        return Response({"country": country, "ads": deduped})


class AdImageView(APIView):
    """
    광고 이미지 생성
    POST /api/ad-image/
    multipart/form-data:
        image      (file)    — 제품 이미지
        product_name, category, ingredients, effects (str)
        headline1, headline2 (str, optional) — 광고 전략에서 생성된 헤드라인
    Response: {"images": [{"data": base64, "mime_type": "image/png"}, ...]}
    """
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        image_file = request.FILES.get("image")
        if not image_file:
            return Response({"error": "image 파일이 필요합니다."}, status=400)

        import json
        from .services.ad_image import generate_ad_images

        key_messages_raw = request.data.get("key_messages", "")
        try:
            key_messages = json.loads(key_messages_raw) if key_messages_raw else []
        except (json.JSONDecodeError, TypeError):
            key_messages = []

        result = generate_ad_images(
            image_file=image_file,
            product_name=request.data.get("product_name", ""),
            category=request.data.get("category", ""),
            ingredients=request.data.get("ingredients", ""),
            effects=request.data.get("effects", ""),
            brand_concept=request.data.get("brand_concept", ""),
            headline1=request.data.get("headline1", ""),
            body_text1=request.data.get("body_text1", ""),
            headline2=request.data.get("headline2", ""),
            body_text2=request.data.get("body_text2", ""),
            key_messages=key_messages,
            country=request.data.get("country", "US"),
        )

        if "error" in result:
            return Response(result, status=500)

        return Response(result, status=200)
