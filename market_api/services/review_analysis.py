"""
상품별 리뷰 분석 로직
load_review_data.py에서 호출하여 ReviewAnalysisCache에 저장
"""
import json
import os
from collections import Counter
from pathlib import Path

from openai import OpenAI

_KO_MAP_PATH = Path(__file__).resolve().parents[2] / "crawling" / "keyword_ko_map.json"
try:
    with open(_KO_MAP_PATH, encoding="utf-8") as _f:
        KW_KO_MAP: dict = json.load(_f)
except Exception:
    KW_KO_MAP = {}


def reload_kw_map():
    """keyword_ko_map.json을 다시 읽어 KW_KO_MAP 갱신 (파이프라인 실행 후 호출)"""
    global KW_KO_MAP
    try:
        with open(_KO_MAP_PATH, encoding="utf-8") as f:
            KW_KO_MAP = json.load(f)
    except Exception:
        pass

CATEGORY_LABEL = {
    "효과_성분":          "효과 / 성분",
    "사용감_텍스처":      "발림성",
    "향_냄새":            "향",
    "피부_트러블_부작용": "피부 자극",
    "포장_배송":          "포장 / 배송",
    "가격_가성비":        "가격 적절성",
    "재구매_추천":        "재구매 / 추천",
    "고객서비스":         "고객서비스",
    "제품불량":           "제품불량",
    "커버력_색상":        "커버력 / 색상",
    "지속력_밀착력":      "지속력",
    "부정_리뷰":          "부정 리뷰",
}

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def _gpt(prompt: str, system: str = "") -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = _get_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.3,
    )
    return resp.choices[0].message.content.strip()


def _summarize_reviews(reviews: list, group: str) -> str:
    """긍정/부정 리뷰 그룹 요약"""
    if not reviews:
        return ""

    if len(reviews) <= 100:
        texts = [r["body_ko"] for r in reviews if r.get("body_ko") and len(r["body_ko"]) > 10]
        if not texts:
            return ""
        content = "\n".join(f"- {t[:200]}" for t in texts[:100])
        prompt = f"""다음은 {group} 리뷰들입니다.
{content}

규칙: 반드시 1문장. 90~110자 분량. '~입니다'로 끝내는 따뜻한 말투. 리뷰 건수·상품명·플랫폼명 언급 금지. 한국어로 작성."""
    else:
        all_kw = []
        for r in reviews:
            all_kw.extend(r.get("keybert_keywords") or [])
        top_kw = [(KW_KO_MAP.get(kw, kw), cnt) for kw, cnt in Counter(all_kw).most_common(10)]
        kw_str = ", ".join(f"{kw}({cnt}회)" for kw, cnt in top_kw)

        cat_ratings = {}
        for r in reviews:
            cat = r.get("primary_category", "")
            if cat and cat != "미분류" and r.get("rating") is not None:
                cat_ratings.setdefault(cat, []).append(r["rating"])
        cat_str = ", ".join(
            f"{CATEGORY_LABEL.get(c, c)} {round(sum(v)/len(v),1)}점"
            for c, v in sorted(cat_ratings.items(), key=lambda x: -len(x[1]))[:3]
        )

        prompt = f"""주요 키워드: {kw_str}
카테고리 평점: {cat_str}

규칙: 반드시 1문장. 90~110자 분량. '~입니다'로 끝내는 따뜻한 말투. 리뷰 건수·상품명·플랫폼명 언급 금지. 한국어로 작성."""

    return _gpt(prompt)


def _generate_opportunities(country: str,
                             complaints: list, category_scores: list,
                             sentiment: dict,
                             positive_summary: str, negative_summary: str) -> list:
    """긍정/부정 요약 + 불만사항 기반 시장 기회 생성"""
    if not complaints and not positive_summary and not negative_summary:
        return []

    complaint_str = ", ".join(f"{c['label']}({c['pct']}%)" for c in complaints)
    strength_str = ", ".join(
        f"{c['category']} {c['score']}점" for c in category_scores[:3]
    )
    country_name = {"US": "미국", "JP": "일본"}.get(country, country)

    prompt = f"""다음은 {country_name} 소비자 리뷰 분석 데이터입니다.

- 긍정 비율: {sentiment.get('positive', 0)}% / 부정 비율: {sentiment.get('negative', 0)}%
- 주요 강점: {strength_str}
- 긍정 리뷰 요약: {positive_summary or '없음'}
- 부정 리뷰 요약: {negative_summary or '없음'}
- 주요 불만사항: {complaint_str or '없음'}

위 데이터를 바탕으로 한국 뷰티 브랜드가 공략할 수 있는 시장 기회 3가지를 제시해주세요.
긍정 강점 활용, 불만사항 개선, 새로운 포지셔닝 등 다양한 관점에서 분석하세요.
규칙:
- title: 4자 이내 명사형 키워드 (예: 저자극, 커버력, 향)
- description: title을 반복하지 말고, 위 데이터에서 근거를 찾아 25자 이내 인사이트 한 줄
JSON 형식으로만 응답: [{{"title": "...", "description": "..."}}, ...]"""

    try:
        raw = _gpt(prompt)
        # JSON 파싱
        start = raw.find("[")
        end = raw.rfind("]") + 1
        return json.loads(raw[start:end])
    except Exception:
        return []


def compute_review_analysis(platform: str, item_id: str, reviews: list, ranking: dict) -> dict:
    """
    상품 1개의 전체 리뷰 분석 결과를 계산하여 반환
    reviews: ProductReview queryset을 list(values(...))로 변환한 것
    ranking: ProductRanking.values(...).first()
    """
    if not reviews:
        return {}

    country = reviews[0].get("country", "US")

    # 1. 총 평점
    if platform == "Sephora" and ranking and ranking.get("rating"):
        total_rating = round(ranking["rating"], 1)
    else:
        ratings = [r["rating"] for r in reviews if r["rating"] is not None]
        total_rating = round(sum(ratings) / len(ratings), 1) if ratings else None

    platform_reviews_count = ranking.get("reviews_count") if ranking else None
    review_count = len(reviews)

    # 2. 긍/중립/부정 분류
    positive = [r for r in reviews if r["rating"] and r["rating"] >= 4]
    negative = [r for r in reviews if r["rating"] and r["rating"] <= 2]
    neutral  = [r for r in reviews if r["rating"] and 2 < r["rating"] < 4]
    total = len(reviews)
    sentiment = {
        "positive": round(len(positive) / total * 100) if total else 0,
        "neutral":  round(len(neutral)  / total * 100) if total else 0,
        "negative": round(len(negative) / total * 100) if total else 0,
    }

    # 3. 카테고리별 만족도 (10건 이상, 건수 많은 순)
    cat_ratings = {}
    for r in reviews:
        cat = r["primary_category"]
        if cat and cat != "미분류" and r["rating"] is not None:
            cat_ratings.setdefault(cat, []).append(r["rating"])
    category_scores = [
        {
            "category": CATEGORY_LABEL.get(cat, cat),
            "score": round(sum(v) / len(v), 1),
            "count": len(v),
        }
        for cat, v in cat_ratings.items()
        if len(v) >= 10
    ]
    category_scores.sort(key=lambda x: -x["count"])

    # 4. 핵심 키워드 TOP 8 (한국어 번역)
    all_keywords = []
    for r in reviews:
        all_keywords.extend(r["keybert_keywords"] or [])
    top_keywords = [
        f"#{KW_KO_MAP.get(kw, kw).replace(' ', '')}"
        for kw, _ in Counter(all_keywords).most_common(8)
    ]

    # 5. 주요 불만사항
    complaint_counter = Counter()
    for r in negative:
        for cat in (r["categories"] or []):
            if cat != "미분류":
                complaint_counter[CATEGORY_LABEL.get(cat, cat)] += 1
    total_complaints = sum(complaint_counter.values()) or 1
    complaints = [
        {"label": label, "pct": round(cnt / total_complaints * 100)}
        for label, cnt in complaint_counter.most_common(3)
    ]

    # 6. GPT 요약 (긍정 / 부정)
    positive_summary = _summarize_reviews(positive, "긍정")
    negative_summary = _summarize_reviews(negative, "부정")

    # 7. GPT 시장 기회
    opportunities = _generate_opportunities(
        country, complaints, category_scores, sentiment,
        positive_summary, negative_summary
    )

    return {
        "total_rating": total_rating,
        "review_count": review_count,
        "platform_reviews_count": platform_reviews_count,
        "sentiment": sentiment,
        "category_scores": category_scores,
        "top_keywords": top_keywords,
        "sample_reviews": {
            "positive": positive_summary,
            "negative": negative_summary,
        },
        "complaints": complaints,
        "opportunities": opportunities,
    }
