from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services.main import run_analysis
from .services.research_engine import get_research_dict


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