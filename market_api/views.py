from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services.main import run_analysis
from .services.research_engine import get_research_dict
from .services.hs_map import get_hs_code, COUNTRY_CODE_MAP, get_fetch_years
from .services.trass_service import fetch_api
from .models import MarketStat


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
