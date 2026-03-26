"""
AI 최적 국가 추천 서비스
설계 문서: docs/scoring_design.md 참고

AI Score (0~100) = 트렌드 적합도(25%) + 시장 규모 점수(50%) + 리뷰 유사도(25%)
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


# 지표별 독립 정규화 기준 범위 (실제 US/JP 데이터 기반)
# size: US K-beauty ~24B, JP ~0.9B → 상한 30B
# growth: JP 8.38%, US 4.2~10% → 상한 15%
# kbeauty: JP 42%, US ~4% → 상한 50%
# ad_activity: 채널별 90일 광고 합산, 실측치 없으므로 보수적 상한
# export_growth: JP YoY +22~27% → 상한 50%, 하락 고려 하한 -30%
METRIC_RANGES = {
    "size":          (0.0,   30.0),
    "growth":        (0.0,    0.15),
    "kbeauty":       (0.0,    0.50),
    "ad_activity":   (0.0, 5000.0),
    "export_growth": (-0.30,  0.50),
}


def _normalize_independent(value: float, key: str) -> float:
    """지표별 고정 범위로 독립 정규화 (0~1)"""
    min_v, max_v = METRIC_RANGES[key]
    if max_v == min_v:
        return 0.5
    return max(0.0, min(1.0, (value - min_v) / (max_v - min_v)))


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

    def norm(key):
        return {c: _normalize_independent(raw[c][key], key) for c in countries}

    n_export = {c: _normalize_independent(export_growth.get(c, 0.0), "export_growth")
                for c in countries}

    n_size = norm("size")
    n_growth = norm("growth")
    n_kb = norm("kbeauty")
    n_ads = norm("ad_activity")

    result = {}
    for c in countries:
        result[c] = (
            n_size[c]   * 0.10 +
            n_growth[c] * 0.20 +
            n_kb[c]     * 0.30 +
            n_export[c] * 0.30 +
            n_ads[c]    * 0.10
        )
    return result


# ── 2. 트렌드 적합도 점수 (40%) ───────────────────────────────────────

def calc_trend_score(ingredients: str, effects: str, research_map: dict) -> dict:
    """
    GPT로 트렌드 적합도 채점 (temperature=0, 출력 검증 포함)
    반환: {country: {"score": 0~1, "matched": [...], "reasoning": "..."}}
    """
    # 입력이 없으면 모든 국가 중립값 반환
    if not ingredients.strip() and not effects.strip():
        return {c: {"score": 0.5, "matched": [], "reasoning": ""} for c in research_map}

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

        user_inputs = [k.strip() for k in re.split(r"[,\s]+", f"{ingredients} {effects}") if k.strip()]

        prompt = f"""당신은 K-Beauty 시장 분석 전문가입니다.

[사용자 제품 정보]
- 주요 성분: {ingredients}
- 핵심 효능: {effects}

[{country_name} 시장 트렌드]
- 트렌딩 성분: {', '.join(ing_list)}
- 트렌딩 기능: {', '.join(fn_list)}
- 트렌드 상세: {details[:500]}

사용자 제품의 성분/효능 중 위 트렌드 목록과 의미적으로 일치하는 항목을 찾으세요 (한국어·영어 무관).
- matched_keywords는 반드시 위 트렌드 목록에 실제로 있는 항목만 포함하세요
- 점수는 포함하지 마세요

반드시 아래 JSON 형식만 반환하세요:
{{"matched_keywords": ["CICA", "보습"], "reasoning": "한두 문장 근거"}}"""

        try:
            raw = _gpt([{"role": "user", "content": prompt}], temperature=0)
            start, end = raw.find("{"), raw.rfind("}") + 1
            data = json.loads(raw[start:end])

            # 출력 검증: 실제 트렌드 목록에 있는 항목만 인정
            actual = set(ing_list + fn_list)
            verified = [k for k in data.get("matched_keywords", []) if k in actual]

            # 제곱근 스케일: 첫 매칭에 큰 점수 부여
            max_possible = min(len(user_inputs), len(ing_list + fn_list))
            ratio = len(verified) / max_possible if max_possible > 0 else 0.0
            score = ratio ** 0.5  # sqrt: 1개 매칭도 의미있는 점수

            raw_results[country] = {
                "score":     min(score, 1.0),
                "matched":   verified,
                "reasoning": data.get("reasoning", ""),
            }
        except Exception:
            raw_results[country] = {"score": 0.5, "matched": [], "reasoning": ""}

    return raw_results


# ── 3. 리뷰 유사도 점수 (25%) ─────────────────────────────────────────

# 사용자 입력 키워드 → ReviewAnalysisCache 카테고리 매핑 테이블
# 키워드 → 카테고리 리스트 (하나의 성분이 여러 카테고리에 매핑 가능)
KEYWORD_CATEGORY_MAP = {
    # ── 보습 / 수분 ──────────────────────────────────────────────────────
    "보습": ["보습 / 수분"],    "수분": ["보습 / 수분"],    "촉촉": ["보습 / 수분"],
    "히알루론산": ["보습 / 수분"], "글리세린": ["보습 / 수분"], "세라마이드": ["보습 / 수분"],
    "판테놀": ["보습 / 수분"],
    # ── 미백 / 브라이트닝 ────────────────────────────────────────────────
    "미백": ["미백 / 브라이트닝"], "브라이트닝": ["미백 / 브라이트닝"], "광채": ["미백 / 브라이트닝"],
    "알부틴": ["미백 / 브라이트닝"], "트라넥삼산": ["미백 / 브라이트닝"],
    "나이아신아마이드": ["미백 / 브라이트닝"], "비타민 c": ["미백 / 브라이트닝"],
    # ── 모공 / 각질 ──────────────────────────────────────────────────────
    "각질": ["모공 / 각질"],    "모공": ["모공 / 각질"],    "피지": ["모공 / 각질"],
    "결 개선": ["모공 / 각질"],
    "aha": ["모공 / 각질", "피부 자극"], "bha": ["모공 / 각질", "피부 자극"],
    # ── 주름 / 노화 ──────────────────────────────────────────────────────
    "주름": ["주름 / 노화"],    "탄력": ["주름 / 노화"],    "항산화": ["주름 / 노화"],
    "재생": ["주름 / 노화"],    "리프팅": ["주름 / 노화"],
    "레티놀": ["주름 / 노화", "피부 자극"], "바쿠치올": ["주름 / 노화"],
    "펩타이드": ["주름 / 노화"], "아데노신": ["주름 / 노화"],
    # ── 진정 / 장벽 ──────────────────────────────────────────────────────
    "진정": ["진정 / 장벽"],    "장벽": ["진정 / 장벽"],    "시카": ["진정 / 장벽"],
    "병풀추출물": ["진정 / 장벽"], "마데카소사이드": ["진정 / 장벽"],
    "발효추출물": ["진정 / 장벽"], "pdrn": ["진정 / 장벽"],
    "스피큘": ["진정 / 장벽", "피부 자극"],
    # ── 그 외 효과 (세분류 미해당) ───────────────────────────────────────
    "성분": ["효과 / 성분"],    "효과": ["효과 / 성분"],    "기능성": ["효과 / 성분"],
    # ── 사용감 ───────────────────────────────────────────────────────────
    "발림": ["발림성"],  "흡수": ["발림성"],  "텍스처": ["발림성"],
    "가벼": ["발림성"],  "끈적": ["발림성"],  "도포": ["발림성"],
    # ── 기타 ────────────────────────────────────────────────────────────
    "향": ["향"],              "냄새": ["향"],              "아로마": ["향"],
    "자극": ["피부 자극"],     "민감": ["피부 자극"],       "트러블": ["피부 자극"],
    "저자극": ["피부 자극"],   "예민": ["피부 자극"],
    "지속": ["지속력"],        "밀착": ["지속력"],          "유지": ["지속력"],
    "가성비": ["가격 적절성"], "가격": ["가격 적절성"],     "합리": ["가격 적절성"],
    "커버": ["커버력 / 색상"], "색상": ["커버력 / 색상"],   "발색": ["커버력 / 색상"],
    "재구매": ["재구매 / 추천"], "추천": ["재구매 / 추천"],
}


def _get_country_review_data(country: str) -> dict:
    """국가별 Top10 상품 ReviewAnalysisCache 집계"""
    from market_api.models import ProductRanking, ReviewAnalysisCache

    PLATFORM_MAP = {"US": ["Ulta", "Sephora"], "JP": ["Qoo10", "Rakuten"]}
    platforms = PLATFORM_MAP.get(country, [])

    all_keywords = []
    # {category: {"score_sum": float, "weight_sum": int}}
    cat_scores_raw = {}

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

            weight = cache.result.get("review_count", 1) or 1

            for kw in cache.result.get("top_keywords", []):
                all_keywords.append(kw.lstrip("#"))

            for cs in cache.result.get("category_scores_v2", cache.result.get("category_scores", [])):
                cat   = cs.get("category", "")
                score = cs.get("score")
                if cat and score is not None:
                    acc = cat_scores_raw.setdefault(cat, {"score_sum": 0.0, "weight_sum": 0})
                    acc["score_sum"]  += score * weight
                    acc["weight_sum"] += weight

    # 리뷰 수 가중 평균
    avg_cat_scores = {
        cat: v["score_sum"] / v["weight_sum"]
        for cat, v in cat_scores_raw.items()
        if v["weight_sum"] > 0
    }

    return {
        "keywords":       [kw for kw, _ in Counter(all_keywords).most_common(30)],
        "category_scores": avg_cat_scores,
    }


def _user_to_categories(ingredients: str, effects: str) -> list:
    """사용자 입력에서 관련 리뷰 카테고리 추출 (규칙 테이블 기반)"""
    combined = f"{ingredients} {effects}".lower()
    matched = set()
    for keyword, categories in KEYWORD_CATEGORY_MAP.items():
        if keyword in combined:
            matched.update(categories)
    return list(matched) if matched else ["효과 / 성분"]


def calc_review_score(ingredients: str, effects: str, countries: list) -> dict:
    """
    리뷰 유사도 점수 산출
    반환: {country: score (0~1)}
    """
    user_categories = _user_to_categories(ingredients, effects)

    raw = {}
    for country in countries:
        review_data = _get_country_review_data(country)
        cat_scores  = review_data["category_scores"]

        relevant = [cat_scores[c] for c in user_categories if c in cat_scores]
        raw[country] = (sum(relevant) / len(relevant) / 5.0) if relevant else 0.5

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

        ai_score = (t * 0.15 + m * 0.50 + rv * 0.35) * 100

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
