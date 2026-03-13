from .hs_advisor import get_hs_code
from .market_engine import get_stats

def run_analysis(cat):
    # 1. HS 코드 판정
    hs, reason = get_hs_code(cat)
    if not hs:
        return {"error": reason}

    # 2. 5개년 실적 수집 (DB + API)
    data = get_stats(cat, hs)
    
    return {
        "category": cat,
        "hs_code": hs,
        "reason": reason,
        "stats": data
    }