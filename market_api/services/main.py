from .hs_advisor import get_hs_code
from .market_engine import get_stats
from .research_engine import get_research_dict


def run_analysis(cat):
    # 1. HS 코드 판정
    hs, reason = get_hs_code(cat)
    if not hs:
        return {"error": reason}

    # 2. 5개년 실적 수집 (DB + API)
    data = get_stats(cat, hs)

    # 3. 시장 리서치 데이터 조회 (미국, 일본)
    research = {}
    for country in ["US", "JP"]:
        r = get_research_dict(cat, country)
        if r:
            research[country] = r

    return {
        "category": cat,
        "hs_code": hs,
        "reason": reason,
        "stats": data,
        "research": research,
    }