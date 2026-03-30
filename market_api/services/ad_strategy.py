"""
AI 마케팅 전략 제안 서비스

아래 4가지 데이터를 종합하여 GPT-4o가 광고 전략을 생성한다.

1. 경쟁 브랜드 Meta 광고 데이터 (최근 90일)
   - 채널별 광고 수·매체 비율·빈출 키워드·브랜드별 광고 문구

2. 시장 트렌드 (MarketResearch)
   - 인기 성분·기능 트렌드

3. 제품-시장 트렌드 매칭 분석
   - 사용자 입력 성분·효능과 시장 트렌드 성분·기능의 교집합을 계산하여
     실제 강점으로 강조 가능한 포인트를 GPT에 명시적으로 전달

4. 소비자 리뷰 분석 (ReviewAnalysisCache 기반)
   - 채널별 Top10 상품의 긍정·부정 요약 및 불만 카테고리 (최대 20개)
   - 화장품 관련 부정 리뷰 패턴에서, 사용자 제품 성분·효능으로
     실제 해결 가능한 불만만 선별하여 극복 소구점으로 활용

key_messages(핵심 소구점) 생성 원칙:
   - 사용자 제품 성분·효능으로 뒷받침 가능한 내용만 포함
   - 화장품 마케팅 감성 언어 사용 (개발·비즈니스 용어 금지)
   - 뷰티 브랜드 광고 카피 스타일의 짧고 감성적인 문장
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

# 제품 성능과 무관한 불만 카테고리 (마케팅 전략 컨텍스트에서 제외)
EXCLUDED_COMPLAINT_LABELS = {"포장 / 배송", "고객서비스", "제품불량"}
EXCLUDED_COMPLAINT_CATEGORIES = {"포장_배송", "고객서비스", "제품불량"}  # primary_category 기준


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


def _get_top_review_summaries(country: str) -> dict:
    """
    해당 국가 채널별 Top10 상품의 리뷰 요약 수집.
    - 긍정: ReviewAnalysisCache.sample_reviews.positive
    - 부정: ReviewAnalysisCache.sample_reviews.negative
    - 불만 카테고리: complaints에서 포장/배송·고객서비스·제품불량 제외 후 상위 3개 레이블
    Returns:
        {channel: [{"rank": int, "title": str, "positive": str, "negative": str, "complaints": [str]}, ...]}
    """
    from market_api.models import ProductRanking, ReviewAnalysisCache

    channels = CHANNEL_MAP.get(country, [])
    result = {}

    for channel in channels:
        top_products = (
            ProductRanking.objects
            .filter(platform__iexact=channel, country=country)
            .order_by("rank")
            .values("rank", "title", "platform", "platform_item_id")[:10]
        )

        summaries = []
        for product in top_products:
            cache = (
                ReviewAnalysisCache.objects
                .filter(
                    platform=product["platform"],
                    platform_item_id=product["platform_item_id"],
                )
                .values("result")
                .first()
            )
            if not cache or not cache["result"]:
                continue

            res = cache["result"]
            positive_summary = res.get("sample_reviews", {}).get("positive", "")
            negative_summary = res.get("sample_reviews", {}).get("negative", "")
            filtered_complaints = [
                c["label"]
                for c in res.get("complaints", [])
                if c.get("label") not in EXCLUDED_COMPLAINT_LABELS
            ][:3]

            if not positive_summary and not negative_summary and not filtered_complaints:
                continue

            summaries.append({
                "rank": product["rank"],
                "title": product["title"],
                "positive": positive_summary,
                "negative": negative_summary,
                "complaints": filtered_complaints,
            })

        if summaries:
            result[channel] = summaries

    return result


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
    review_summaries: dict,
) -> list:
    """
    GPT-4o에 전달할 system/user 메시지 구성.

    user_msg 구성 순서:
      1. 사용자 제품 정보 (제품명·카테고리·성분·효능)
      2. 시장 트렌드 (인기 성분·기능·상세)
      3. 제품-시장 트렌드 매칭 분석 (교집합 계산 결과)
      4. 경쟁 브랜드 Meta 광고 분석 (광고 수·매체 비율·키워드·브랜드별 문구)
      5. 채널별 인기 상품 긍정 리뷰 요약
      6. 소비자 부정 리뷰 패턴 (채널 2개 × Top10 = 최대 20개 요약)
         → 사용자 제품 성분·효능으로 해결 가능한 불만만 소구점에 반영하도록 지시

    Returns:
        [{"role": "system", "content": ...}, {"role": "user", "content": ...}]
    """
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
    trend_ingredient_list = trends.get("ingredients", [])
    trend_function_list   = trends.get("functions", [])
    trend_ingredients = ", ".join(trend_ingredient_list) or "데이터 없음"
    trend_functions   = ", ".join(trend_function_list)   or "데이터 없음"
    trend_details     = trends.get("details", "")

    # 제품-시장 트렌드 매칭 분석
    user_ingredients_lower = (ingredients or "").lower()
    user_effects_lower     = (effects or "").lower()
    matched_ingredients = [i for i in trend_ingredient_list if i.lower() in user_ingredients_lower]
    matched_functions   = [f for f in trend_function_list   if f.lower() in user_effects_lower]

    # 키워드 빈도
    top_kw = ", ".join(f"{w}({c})" for w, c in ad_data["top_keywords"][:15])

    # 채널별 Top 상품 리뷰 요약 섹션 (긍정) + 부정 리뷰 요약 수집
    review_section_parts = []
    negative_reviews_all = []
    for channel, items in review_summaries.items():
        lines = [f"### {channel.upper()} 인기 상품 리뷰 요약"]
        for item in items[:10]:
            lines.append(f"  #{item['rank']} {item['title'][:50]}")
            if item["positive"]:
                lines.append(f"    - 긍정: {item['positive']}")
            if item.get("negative"):
                negative_reviews_all.append(item["negative"])
            if item["complaints"]:
                lines.append(f"    - 주요 불만: {', '.join(item['complaints'])}")
        review_section_parts.append("\n".join(lines))
    review_section = "\n\n".join(review_section_parts)

    # 부정 리뷰 요약 섹션 (최대 20개, 채널 2개 × 10개)
    negative_section = ""
    if negative_reviews_all:
        neg_lines = "\n".join(f"  - {n}" for n in negative_reviews_all[:20])
        negative_section = f"## 소비자 부정 리뷰 패턴 (화장품 관련만)\n{neg_lines}"

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

중요: key_messages(핵심 소구점) 작성 규칙
1. 반드시 사용자가 입력한 성분·효능으로 실제 뒷받침 가능한 내용만 작성하세요.
   - 제품 성분·효능에 없는 기능은 소구점으로 절대 사용하지 마세요.
   - 소비자 부정 리뷰 패턴이 있다면, 그 불만을 이 제품의 성분·효능이 실제로 해결할 수 있는 경우에만 극복 소구점으로 활용하세요.
2. 화장품·뷰티 마케팅 언어로 작성하세요.
   - 고객이 느끼는 감각·감정·결과 중심 ("피부가 촉촉하게 살아납니다", "자연스럽게 빛나는 피부톤" 등)
   - 기능/기술 설명 문체 금지 ("멀티태스킹 기능", "효율적 루틴", "시간 절약" 같은 개발·비즈니스 용어 사용 금지)
   - 짧고 감성적인 문장으로, 뷰티 브랜드 광고 카피처럼 작성

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

    matched_ing_str = ", ".join(matched_ingredients) if matched_ingredients else "없음"
    matched_fn_str  = ", ".join(matched_functions)   if matched_functions   else "없음"

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

## 제품-시장 트렌드 매칭 분석
- 제품 성분 중 시장 트렌드와 일치: {matched_ing_str}
- 제품 효능 중 시장 트렌드와 일치: {matched_fn_str}
→ 위 매칭 포인트가 있다면 이를 광고 전략과 핵심 소구점의 중심으로 활용하세요.

## 경쟁 브랜드 Meta 광고 분석 (최근 90일)
- 전체 광고 수: {ad_data['total_ads']}건
- 이미지 비율: {ad_data['image_ratio']*100:.0f}% / 영상 비율: {ad_data['video_ratio']*100:.0f}%
- 광고 문구 내 빈출 키워드: {top_kw}

### 브랜드별 광고 데이터
{brand_section}
{f'''
## {country_label} 채널별 인기 상품 리뷰 요약 (소비자 실제 반응)
{review_section}
''' if review_section else ''}{f'''
{negative_section}
→ 위 부정 리뷰 패턴 중, 사용자 제품의 성분·효능으로 실제 해결 가능한 불만에 한해서만 극복 소구점을 key_messages에 포함하세요. 제품이 뒷받침할 수 없는 불만은 무시하세요.
''' if negative_section else ''}
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

    처리 흐름:
      1. Meta 광고 데이터 수집 (_collect_ad_data)
      2. 시장 트렌드 조회 (_get_trends)
      3. Top10 상품 리뷰 요약 수집 — 긍정·부정·불만 카테고리 포함 (_get_top_review_summaries)
      4. GPT 프롬프트 구성 및 호출 (_build_prompt → _gpt)
      5. JSON 파싱 후 결과 반환

    Returns:
        {
            "brand_concept": str,           # 추천 브랜드 포지셔닝 컨셉 (영문/일본어)
            "concept_reasoning": str,       # 컨셉 선정 이유 (한국어)
            "key_messages": [str],          # 핵심 소구점 3개 (한국어, 뷰티 마케팅 언어)
            "ad_copies": [                  # 광고 카피 2개
                {"headline": str, "body_text": str}
            ],
            "detailed_insight": str,        # 상세 마케팅 인사이트 (한국어)
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

    # 3. 채널별 Top10 상품 리뷰 요약 (긍정·부정·불만 카테고리)
    review_summaries = _get_top_review_summaries(country)

    # 4. GPT 프롬프트 구성 & 호출
    messages = _build_prompt(
        product_name, category, ingredients, effects,
        country, ad_data, trends, review_summaries,
    )
    raw = _gpt(messages)

    # 5. JSON 파싱
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

    # 6. 광고 통계 추가
    result["ad_stats"] = {
        "total_ads": ad_data["total_ads"],
        "brand_count": len(ad_data["brands"]),
        "image_ratio": ad_data["image_ratio"],
        "video_ratio": ad_data["video_ratio"],
    }
    result["country"] = country

    return result
