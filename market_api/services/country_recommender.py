"""
AI 최적 국가 추천 서비스
설계 문서: docs/scoring_design.md 참고

AI Score (0~100) = 트렌드 적합도(40%) + 시장 규모 점수(35%) + 리뷰 유사도(25%)
"""
import os
import re
import json
from collections import Counter
from openai import OpenAI

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def _gpt(messages: list, temperature: float = 0) -> str:
    resp = _get_client().chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=temperature,
    )
    return resp.choices[0].message.content.strip()


# ── 공통 유틸 ─────────────────────────────────────────────────────────

def _parse_number(text: str) -> float:
    """'$18.4B', '$500M' 등 → 십억 달러 기준 float"""
    if not text:
        return 0.0
    text = text.replace(",", "")
    match = re.search(r"[\d.]+", text)
    if not match:
        return 0.0
    val = float(match.group())
    upper = text.upper()
    if "T" in upper:
        val *= 1000
    elif "M" in upper and "B" not in upper:
        val /= 1000
    return val


def _parse_pct(text: str) -> float:
    """'6.96%' → 0.0696"""
    if not text:
        return 0.0
    match = re.search(r"[\d.]+", text)
    return float(match.group()) / 100 if match else 0.0


def _normalize_pair(a: float, b: float):
    """두 값을 상대 비율로 정규화 (합 = 1.0)"""
    total = a + b
    if total == 0:
        return 0.5, 0.5
    return a / total, b / total


# ── 1. 시장 규모 점수 (50%) ───────────────────────────────────────────

def _calc_export_growth(category: str, country: str) -> float:
    """MarketStat에서 최근 2개년 평균 YoY 수출 성장률 계산"""
    from market_api.models import MarketStat
    stats = list(
        MarketStat.objects.filter(category=category, country=country)
        .order_by("year")
        .values_list("year", "amount")
    )
    if len(stats) < 2:
        return 0.0
    # 최근 3개 연도로 2개 YoY 계산
    recent = stats[-3:]
    yoys = []
    for i in range(1, len(recent)):
        prev = recent[i - 1][1]
        curr = recent[i][1]
        if prev and prev > 0:
            yoys.append((curr - prev) / prev)
    return sum(yoys) / len(yoys) if yoys else 0.0


def _calc_ad_activity(country: str) -> float:
    """MetaAdSummary에서 국가별 채널 total_ads 합산"""
    from django.db.models import Sum
    from market_api.models import MetaAdSummary
    CHANNEL_MAP = {"US": ["ulta", "sephora"], "JP": ["qoo10", "rakuten"]}
    channels = CHANNEL_MAP.get(country, [])
    total = MetaAdSummary.objects.filter(channel__in=channels).aggregate(s=Sum("total_ads"))["s"]
    return float(total or 0)


def calc_market_score(category: str, research_map: dict, export_growth: dict) -> dict:
    """
    국가별 시장 규모 점수 산출
    반환: {country: score (0~1)}
    """
    raw = {}
    for country, r in research_map.items():
        ms = r.get("market_size", {})
        ks = r.get("kbeauty_share", {})
        raw[country] = {
            "size":       _parse_number(ms.get("value", "")),
            "growth":     _parse_pct(ms.get("cagr") or ms.get("growth_rate", "")),
            "kbeauty":    _parse_pct(ks.get("share", "")),
            "ad_activity": _calc_ad_activity(country),
        }

    countries = list(raw.keys())
    if len(countries) < 2:
        return {countries[0]: 0.5} if countries else {}

    c1, c2 = countries[0], countries[1]

    def norm(key):
        return dict(zip([c1, c2], _normalize_pair(raw[c1][key], raw[c2][key])))

    # 수출 성장률 음수 처리: shift to positive
    raw_eg_c1 = export_growth.get(c1, 0.0)
    raw_eg_c2 = export_growth.get(c2, 0.0)
    min_eg = min(raw_eg_c1, raw_eg_c2, 0)
    adj_c1 = raw_eg_c1 - min_eg
    adj_c2 = raw_eg_c2 - min_eg
    n_export_total = adj_c1 + adj_c2
    if n_export_total == 0:
        n_export = {c1: 0.5, c2: 0.5}
    else:
        n_export = {c1: adj_c1 / n_export_total, c2: adj_c2 / n_export_total}

    n_size = norm("size")
    n_growth = norm("growth")
    n_kb = norm("kbeauty")
    n_ads = norm("ad_activity")

    result = {}
    for c in countries:
        result[c] = (
            n_size[c]   * 0.10 +
            n_growth[c] * 0.25 +
            n_kb[c]     * 0.25 +
            n_export[c] * 0.20 +
            n_ads[c]    * 0.20
        )
    return result


# ── 2. 트렌드 적합도 점수 (40%) ───────────────────────────────────────

def calc_trend_score(ingredients: str, effects: str, research_map: dict) -> dict:
    """
    GPT로 트렌드 적합도 채점 (temperature=0, 출력 검증 포함)
    반환: {country: {"score": 0~1, "matched": [...], "reasoning": "..."}}
    """
    raw_results = {}

    for country, r in research_map.items():
        trends = r.get("trends", {})
        ing_list = trends.get("ingredients", [])
        fn_list  = trends.get("functions", [])
        details  = trends.get("details", "")

        if not ing_list and not fn_list:
            raw_results[country] = {"score": 0.5, "matched": [], "reasoning": ""}
            continue

        country_name = {"US": "미국", "JP": "일본"}.get(country, country)

        prompt = f"""당신은 K-Beauty 시장 분석 전문가입니다.

[사용자 제품 정보]
- 주요 성분: {ingredients}
- 핵심 효능: {effects}

[{country_name} 시장 트렌드]
- 트렌딩 성분: {', '.join(ing_list)}
- 트렌딩 기능: {', '.join(fn_list)}
- 트렌드 상세: {details[:500]}

위 제품이 {country_name} 시장 트렌드와 얼마나 부합하는지 0~10점으로 채점하세요.
- 성분/효능이 트렌드 목록과 의미적으로 일치하는 항목을 찾으세요 (한국어·영어 무관)
- matched_keywords는 반드시 위 트렌드 목록에 실제로 있는 항목만 포함하세요

반드시 아래 JSON 형식만 반환하세요:
{{"score": 7.5, "matched_keywords": ["CICA", "보습"], "reasoning": "한두 문장 근거"}}"""

        try:
            raw = _gpt([{"role": "user", "content": prompt}], temperature=0)
            start, end = raw.find("{"), raw.rfind("}") + 1
            data = json.loads(raw[start:end])

            # 출력 검증: 실제 트렌드 목록에 있는 항목만 인정
            actual = set(ing_list + fn_list)
            verified = [k for k in data.get("matched_keywords", []) if k in actual]

            score = max(0.0, min(10.0, float(data.get("score", 5.0)))) / 10.0

            raw_results[country] = {
                "score":     score,
                "matched":   verified,
                "reasoning": data.get("reasoning", ""),
            }
        except Exception:
            raw_results[country] = {"score": 0.5, "matched": [], "reasoning": ""}

    # 국가 간 상대 비율 정규화
    countries = list(raw_results.keys())
    if len(countries) == 2:
        c1, c2 = countries
        n1, n2 = _normalize_pair(raw_results[c1]["score"], raw_results[c2]["score"])
        raw_results[c1]["score"] = n1
        raw_results[c2]["score"] = n2

    return raw_results


# ── 3. 리뷰 유사도 점수 (25%) ─────────────────────────────────────────

# 사용자 입력 키워드 → ReviewAnalysisCache 카테고리 매핑 테이블
KEYWORD_CATEGORY_MAP = {
    "보습": "효과 / 성분",    "수분": "효과 / 성분",    "촉촉": "효과 / 성분",
    "진정": "효과 / 성분",    "장벽": "효과 / 성분",    "재생": "효과 / 성분",
    "미백": "효과 / 성분",    "탄력": "효과 / 성분",    "주름": "효과 / 성분",
    "항산화": "효과 / 성분",  "성분": "효과 / 성분",    "효과": "효과 / 성분",
    "발림": "발림성",          "흡수": "발림성",          "텍스처": "발림성",
    "가벼": "발림성",          "끈적": "발림성",          "도포": "발림성",
    "향": "향",               "냄새": "향",              "아로마": "향",
    "자극": "피부 자극",       "민감": "피부 자극",       "트러블": "피부 자극",
    "저자극": "피부 자극",     "예민": "피부 자극",
    "지속": "지속력",          "밀착": "지속력",          "유지": "지속력",
    "가성비": "가격 적절성",   "가격": "가격 적절성",     "합리": "가격 적절성",
    "커버": "커버력 / 색상",   "색상": "커버력 / 색상",   "발색": "커버력 / 색상",
    "재구매": "재구매 / 추천", "추천": "재구매 / 추천",
}


def _get_country_review_data(country: str) -> dict:
    """국가별 Top10 상품 ReviewAnalysisCache 집계"""
    from market_api.models import ProductRanking, ReviewAnalysisCache

    PLATFORM_MAP = {"US": ["Ulta", "Sephora"], "JP": ["Qoo10", "Rakuten"]}
    platforms = PLATFORM_MAP.get(country, [])

    all_keywords = []
    cat_scores_raw = {}  # {category_label: [scores]}

    for platform in platforms:
        top_ids = ProductRanking.objects.filter(
            platform=platform, country=country, rank__lte=10
        ).values_list("platform_item_id", flat=True)

        for item_id in top_ids:
            cache = ReviewAnalysisCache.objects.filter(
                platform=platform, platform_item_id=item_id
            ).first()
            if not cache or not cache.result:
                continue

            for kw in cache.result.get("top_keywords", []):
                all_keywords.append(kw.lstrip("#"))

            for cs in cache.result.get("category_scores", []):
                cat   = cs.get("category", "")
                score = cs.get("score")
                if cat and score is not None:
                    cat_scores_raw.setdefault(cat, []).append(score)

    avg_cat_scores = {
        cat: sum(v) / len(v)
        for cat, v in cat_scores_raw.items()
    }

    return {
        "keywords":       [kw for kw, _ in Counter(all_keywords).most_common(30)],
        "category_scores": avg_cat_scores,
    }


def _user_to_categories(ingredients: str, effects: str) -> list:
    """사용자 입력에서 관련 리뷰 카테고리 추출 (규칙 테이블 기반)"""
    combined = f"{ingredients} {effects}".lower()
    matched = set()
    for keyword, category in KEYWORD_CATEGORY_MAP.items():
        if keyword in combined:
            matched.add(category)
    return list(matched) if matched else ["효과 / 성분"]


def calc_review_score(ingredients: str, effects: str, countries: list) -> dict:
    """
    리뷰 유사도 점수 산출
    반환: {country: score (0~1)}
    """
    user_categories = _user_to_categories(ingredients, effects)
    user_keywords = {
        kw.strip()
        for kw in re.split(r"[,\s]+", f"{ingredients} {effects}")
        if len(kw.strip()) > 1
    }

    raw = {}
    for country in countries:
        review_data   = _get_country_review_data(country)
        country_kws   = set(review_data["keywords"])
        cat_scores    = review_data["category_scores"]

        # 키워드 오버랩 (가중치 0.6)
        if country_kws and user_keywords:
            overlap       = len(user_keywords & country_kws)
            keyword_score = min(overlap / len(user_keywords), 1.0)
        else:
            keyword_score = 0.5

        # 카테고리 성향 (가중치 0.4)
        relevant = [cat_scores[c] for c in user_categories if c in cat_scores]
        category_score = (sum(relevant) / len(relevant) / 5.0) if relevant else 0.5

        raw[country] = keyword_score * 0.6 + category_score * 0.4

    # 국가 간 상대 비율 정규화
    countries_list = list(raw.keys())
    if len(countries_list) == 2:
        c1, c2 = countries_list
        n1, n2 = _normalize_pair(raw[c1], raw[c2])
        raw[c1], raw[c2] = n1, n2

    return raw


# ── 선정 근거 생성 ────────────────────────────────────────────────────

def _generate_rationale(
    product_name: str,
    ingredients: str,
    effects: str,
    top_country: str,
    score_detail: dict,
    trend_reasoning: str,
    market_research: dict,
) -> str:
    country_name = {"US": "미국", "JP": "일본"}.get(top_country, top_country)
    ms = market_research.get("market_size", {})
    channels = market_research.get("channels", {})
    online = ", ".join([
        c.get("name", c) if isinstance(c, dict) else str(c)
        for c in channels.get("online", [])[:3]
    ])

    prompt = f"""당신은 K-Beauty 글로벌 진출 전문 컨설턴트입니다.

[분석 제품]
- 제품명: {product_name}
- 주요 성분: {ingredients}
- 핵심 효능: {effects}

[최적 추천 국가: {country_name}]
- AI Score: {score_detail['total']:.1f} / 100
- 시장 규모: {ms.get('value', 'N/A')}, 성장률: {ms.get('cagr', 'N/A')}
- 트렌드 부합 근거: {trend_reasoning}
- 주요 유통 채널: {online or 'N/A'}

위 데이터를 바탕으로 {country_name}이 최적 진출 국가인 이유를 3~4문장으로 설명하세요.
- 제품 성분/효능과 현지 트렌드의 연관성을 구체적으로 언급
- 시장 성장성 및 K-뷰티 수용도 언급
- 추천 유통 채널 언급
- 한국어, 전문가적이고 간결한 어조"""

    try:
        return _gpt([{"role": "user", "content": prompt}], temperature=0.3)
    except Exception:
        return ""


# ── 메인 함수 ─────────────────────────────────────────────────────────

def recommend_countries(
    product_name: str,
    category: str,
    ingredients: str,
    effects: str,
) -> dict:
    """
    사용자 제품 정보 기반 최적 진출 국가 추천

    반환:
    {
        "recommended_countries": [...],  # 점수 순 정렬
        "top_country": {...},
        "rationale": "...",
    }
    """
    from market_api.services.research_engine import get_research_dict

    countries = ["US", "JP"]

    # 시장 리서치 데이터 수집
    research_map = {}
    for country in countries:
        r = get_research_dict(category, country)
        if r:
            research_map[country] = r

    if not research_map:
        return {"error": "시장 데이터가 없습니다. 먼저 시장 리서치를 실행하세요."}

    # 수출 성장률 계산
    export_growth = {c: _calc_export_growth(category, c) for c in research_map}

    # 3가지 점수 계산
    market_scores = calc_market_score(category, research_map, export_growth)
    trend_results = calc_trend_score(ingredients, effects, research_map)
    review_scores = calc_review_score(ingredients, effects, list(research_map.keys()))

    # AI Score 합산 및 결과 구성
    country_results = []
    for country in research_map:
        m  = market_scores.get(country, 0.5)
        tr = trend_results.get(country, {})
        t  = tr.get("score", 0.5) if isinstance(tr, dict) else 0.5
        rv = review_scores.get(country, 0.5)

        ai_score = (t * 0.25 + m * 0.50 + rv * 0.25) * 100

        comp = research_map[country].get("competitors", {})

        country_results.append({
            "country": country,
            "score":   round(ai_score, 1),
            "score_detail": {
                "total":  round(ai_score, 1),
                "trend":  round(t  * 100, 1),
                "market": round(m  * 100, 1),
                "review": round(rv * 100, 1),
            },
            "trend_matched":   tr.get("matched", []) if isinstance(tr, dict) else [],
            "trend_reasoning": tr.get("reasoning", "") if isinstance(tr, dict) else "",
            "similar_brands":  comp.get("brands", [])[:5],
            "channels":        research_map[country].get("channels", {}),
            "market_research": {
                k: v for k, v in research_map[country].items()
                if k in ["market_size", "kbeauty_share", "trends", "channels", "competitors"]
            },
        })

    country_results.sort(key=lambda x: x["score"], reverse=True)
    top = country_results[0]

    # 선정 근거 생성
    rationale = _generate_rationale(
        product_name=product_name,
        ingredients=ingredients,
        effects=effects,
        top_country=top["country"],
        score_detail=top["score_detail"],
        trend_reasoning=top["trend_reasoning"],
        market_research=top["market_research"],
    )

    return {
        "recommended_countries": country_results,
        "top_country":           top,
        "rationale":             rationale,
    }
