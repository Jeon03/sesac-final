"""
AI 마케팅 전략 제안 서비스

경쟁 브랜드 Meta 광고 데이터를 분석하여
사용자 제품에 맞는 광고 컨셉·카피·인사이트를 GPT로 생성한다.
"""
import os
import json
from collections import Counter
from datetime import timedelta

from django.utils import timezone

from openai import OpenAI

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def _gpt(messages: list, temperature: float = 0.3) -> str:
    resp = _get_client().chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=temperature,
    )
    return resp.choices[0].message.content.strip()


CHANNEL_MAP = {
    "US": ["ulta", "sephora"],
    "JP": ["qoo10", "rakuten"],
}

COUNTRY_LABEL = {"US": "미국", "JP": "일본"}


def _collect_ad_data(country: str) -> dict:
    """
    해당 국가 채널의 개별 광고 데이터를 수집하여 분석용 dict 반환.
    Returns:
        {
            "brands": {brand: {"texts": [...], "image": int, "video": int, "total": int}},
            "total_ads": int,
            "all_texts": [str, ...],
            "top_keywords": [(word, count), ...],
            "image_ratio": float,
            "video_ratio": float,
        }
    """
    from market_api.models import MetaAd

    channels = CHANNEL_MAP.get(country, [])
    cutoff = timezone.now().date() - timedelta(days=90)

    ads = MetaAd.objects.filter(
        channel__in=channels,
        start_date__gte=cutoff,
    ).values("brand", "ad_text", "media_type")

    brands = {}
    all_texts = []
    total_image = 0
    total_video = 0

    for ad in ads:
        brand = ad["brand"]
        text = (ad["ad_text"] or "").strip()
        mtype = (ad["media_type"] or "").lower()

        if brand not in brands:
            brands[brand] = {"texts": [], "image": 0, "video": 0, "total": 0}

        brands[brand]["total"] += 1
        if mtype == "image":
            brands[brand]["image"] += 1
            total_image += 1
        elif mtype == "video":
            brands[brand]["video"] += 1
            total_video += 1

        if text:
            brands[brand]["texts"].append(text)
            all_texts.append(text)

    total = total_image + total_video
    # 간단한 키워드 빈도 분석 (2글자 이상 단어)
    word_counter = Counter()
    for t in all_texts:
        words = [w.strip(".,!?\"'()[]") for w in t.split()]
        words = [w for w in words if len(w) >= 2]
        word_counter.update(words)

    return {
        "brands": brands,
        "total_ads": total,
        "all_texts": all_texts,
        "top_keywords": word_counter.most_common(30),
        "image_ratio": round(total_image / total, 2) if total else 0,
        "video_ratio": round(total_video / total, 2) if total else 0,
    }


def _get_trends(category: str, country: str) -> dict:
    """MarketResearch에서 트렌드 데이터 가져오기"""
    from market_api.models import MarketResearch
    mr = (
        MarketResearch.objects
        .filter(category=category, country=country)
        .order_by("-research_month")
        .first()
    )
    if not mr:
        return {}
    return mr.trends or {}


def _build_prompt(
    product_name: str,
    category: str,
    ingredients: str,
    effects: str,
    country: str,
    ad_data: dict,
    trends: dict,
) -> list:
    """GPT 프롬프트 구성"""
    country_label = COUNTRY_LABEL.get(country, country)

    # 브랜드별 광고 문구 요약 (상위 4개 브랜드)
    sorted_brands = sorted(
        ad_data["brands"].items(),
        key=lambda x: x[1]["total"],
        reverse=True,
    )[:4]

    brand_summaries = []
    for brand, info in sorted_brands:
        texts = info["texts"][:30]  # 브랜드당 최대 30개 문구
        text_block = "\n".join(f'  - "{t}"' for t in texts) if texts else "  (광고 문구 없음)"
        brand_summaries.append(
            f"**{brand}** (총 {info['total']}건, 이미지 {info['image']}건, 영상 {info['video']}건)\n{text_block}"
        )

    brand_section = "\n\n".join(brand_summaries)

    # 트렌드 정보
    trend_ingredients = ", ".join(trends.get("ingredients", [])) or "데이터 없음"
    trend_functions = ", ".join(trends.get("functions", [])) or "데이터 없음"
    trend_details = trends.get("details", "")

    # 키워드 빈도
    top_kw = ", ".join(f"{w}({c})" for w, c in ad_data["top_keywords"][:15])

    # 국가별 카피 언어 설정
    if country == "JP":
        copy_lang = "일본어"
        copy_lang_en = "Japanese"
    else:
        copy_lang = "영문"
        copy_lang_en = "English"

    system_msg = f"""당신은 K-뷰티 브랜드의 해외 진출을 돕는 마케팅 전략 전문가입니다.
{country_label} 시장의 경쟁 브랜드 Meta 광고 데이터를 분석하고,
사용자의 제품에 최적화된 광고 전략과 카피를 제안해주세요.

중요: 광고 카피(brand_concept, ad_copies)는 반드시 {copy_lang}({copy_lang_en})로 작성하세요.

반드시 아래 JSON 형식으로만 응답하세요:
{{
  "brand_concept": "추천 브랜드 포지셔닝 컨셉 ({copy_lang}, 한 문장)",
  "concept_reasoning": "브랜드 컨셉 선정 이유 (한국어, 2~3문장)",
  "key_messages": ["핵심 상품 소구점 1 (한국어)", "핵심 상품 소구점 2 (한국어)", "핵심 상품 소구점 3 (한국어)"],
  "ad_copies": [
    {{"headline": "광고 헤드라인 A ({copy_lang})", "body_text": "광고 본문 A ({copy_lang}, 2~3문장)"}},
    {{"headline": "광고 헤드라인 B ({copy_lang})", "body_text": "광고 본문 B ({copy_lang}, 2~3문장)"}}
  ],
  "detailed_insight": "상세 마케팅 인사이트 (한국어, 3~4문장. 시장 트렌드·경쟁사 광고 패턴·제안 근거 포함)"
}}"""

    user_msg = f"""## 사용자 제품 정보
- 제품명: {product_name or '(미입력)'}
- 카테고리: {category}
- 주요 성분: {ingredients or '(미입력)'}
- 핵심 효능: {effects or '(미입력)'}

## 타겟 시장: {country_label}

## {country_label} 시장 트렌드
- 인기 성분: {trend_ingredients}
- 기능 트렌드: {trend_functions}
- 상세: {trend_details[:300] if trend_details else '없음'}

## 경쟁 브랜드 Meta 광고 분석 (최근 90일)
- 전체 광고 수: {ad_data['total_ads']}건
- 이미지 비율: {ad_data['image_ratio']*100:.0f}% / 영상 비율: {ad_data['video_ratio']*100:.0f}%
- 광고 문구 내 빈출 키워드: {top_kw}

### 브랜드별 광고 데이터
{brand_section}

위 데이터를 기반으로, 이 제품이 {country_label} 시장에서 차별화할 수 있는 광고 전략을 JSON으로 제안해주세요."""

    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]


def generate_ad_strategy(
    product_name: str,
    category: str,
    ingredients: str,
    effects: str,
    country: str,
) -> dict:
    """
    광고 마케팅 전략 생성 메인 함수.
    Returns:
        {
            "brand_concept": str,
            "concept_reasoning": str,
            "key_messages": [str],
            "headline": str,
            "body_text": str,
            "detailed_insight": str,
            "ad_stats": {
                "total_ads": int,
                "brand_count": int,
                "image_ratio": float,
                "video_ratio": float,
            },
            "country": str,
        }
    """
    # 1. 광고 데이터 수집
    ad_data = _collect_ad_data(country)

    if not ad_data["brands"]:
        return {"error": f"{COUNTRY_LABEL.get(country, country)} 시장의 Meta 광고 데이터가 없습니다."}

    # 2. 트렌드 데이터
    trends = _get_trends(category, country)

    # 3. GPT 프롬프트 구성 & 호출
    messages = _build_prompt(
        product_name, category, ingredients, effects,
        country, ad_data, trends,
    )
    raw = _gpt(messages)

    # 4. JSON 파싱
    try:
        # ```json ... ``` 감싸기 제거
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        result = json.loads(cleaned.strip())
    except (json.JSONDecodeError, IndexError):
        return {"error": "GPT 응답 파싱 실패", "raw_response": raw}

    # 5. 광고 통계 추가
    result["ad_stats"] = {
        "total_ads": ad_data["total_ads"],
        "brand_count": len(ad_data["brands"]),
        "image_ratio": ad_data["image_ratio"],
        "video_ratio": ad_data["video_ratio"],
    }
    result["country"] = country

    return result
