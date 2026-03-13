from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services.main import run_analysis # main.py의 실행 함수

class MatchAPIView(APIView):
    def post(self, request):
        category = request.data.get('category')
        
        if not category:
            return Response({"error": "카테고리를 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)
        
        # 통합 파이프라인 실행 (HS 판정 -> DB 체크 -> API 수집)
        result = run_analysis(category)
        
        if "error" in result:
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        return Response(result, status=status.HTTP_200_OK)