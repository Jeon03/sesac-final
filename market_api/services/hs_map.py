"""
카테고리별 HS 코드 하드코딩 매핑 (6자리 기준).
한국 관세청 무역통계 API(트라스) 조회용.
"""
from datetime import datetime

CATEGORY_HS_MAP = {
    "스킨케어": "330499",  # 피부용 화장품 기타
}

# 트라스 API 국가 코드 매핑
COUNTRY_CODE_MAP = {
    "US": "US",
    "JP": "JP",
}


def get_fetch_years() -> list[str]:
    """현재 연도 기준 전년도까지 5년치 반환 (예: 2026 기준 → 2021~2025)"""
    end = datetime.now().year - 1
    return [str(y) for y in range(end - 4, end + 1)]


def get_hs_code(category: str) -> str | None:
    return CATEGORY_HS_MAP.get(category)
