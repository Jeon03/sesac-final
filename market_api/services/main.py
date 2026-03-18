from .research_engine import get_research_dict


def run_analysis(cat):
    # 시장 리서치 데이터 조회 (미국, 일본)
    research = {}
    for country in ["US", "JP"]:
        r = get_research_dict(cat, country)
        if r:
            research[country] = r

    return {
        "category": cat,
        "research": research,
    }