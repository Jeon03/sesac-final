import os
import json
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from market_api.models import MarketResearch


SUMMARIZE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """당신은 K-Beauty 글로벌 시장 분석 전문가입니다.
아래 크롤링된 원문 자료에서 K-뷰티 시장 분석에 필요한 핵심 정보만 추출하여 요약하세요.

다음 항목별로 핵심 수치와 내용을 간결하게 정리하세요:
1. 시장 규모 및 성장률 (구체적 수치 포함)
2. K-뷰티 시장 점유율 (%)
3. 주요 성분 및 기능 트렌드
4. 주요 유통 채널 (온라인/오프라인)
5. 주요 경쟁 브랜드

규칙:
- 원문에 있는 수치는 반드시 포함하세요 (출처 명시)
- 중복 내용은 제거하세요
- 네비게이션 텍스트, 광고성 문구, 이미지 설명 등 불필요한 내용은 제거하세요
- 3000자 이내로 요약하세요
- 한국어로 작성하세요
"""),
    ("human", "국가: {country}\n카테고리: {category}\n\n[원문 자료]\n{raw_text}"),
])


def summarize_crawled_text(category: str, country: str, raw_text: str) -> str:
    """크롤링 원문을 핵심 정보만 추출하여 요약 (딥리서치 전처리용)"""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    chain = SUMMARIZE_PROMPT | llm

    result = chain.invoke({
        "category": category,
        "country": country,
        "raw_text": raw_text[:100000],  # gpt-4o-mini 128k 컨텍스트 활용
    })

    return result.content.strip()


STRUCTURE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """당신은 K-Beauty 글로벌 시장 분석 전문가입니다.
아래 제공되는 원문 자료를 분석하여, 지정된 국가의 화장품/K-뷰티 시장 정보를 구조화된 JSON으로 추출하세요.

반드시 아래 JSON 형식만 반환하세요 (설명 텍스트 없이 순수 JSON만):
{{
  "market_size": {{
    "value": "시장 규모 (예: $19.62B)",
    "growth_rate": "전년 대비 성장률 (예: 6.96%)",
    "cagr": "연평균 성장률 (예: 6.96%)",
    "forecast": "향후 전망 요약 (1~2문장)",
    "year": "기준연도 (예: 2024)",
    "source_quote": "위 수치가 포함된 원문 발췌 (없으면 빈 문자열)"
  }},
  "kbeauty_share": {{
    "share": "K-뷰티 시장 점유율 (예: 15.8%)",
    "details": "점유율 관련 상세 설명 (1~2문장)",
    "source_quote": "위 수치가 포함된 원문 발췌 (없으면 빈 문자열)"
  }},
  "trends": {{
    "ingredients": ["인기 성분 리스트 (최대 5개)"],
    "functions": ["인기 기능/효능 리스트 (최대 5개)"],
    "details": "트렌드 요약 (2~3문장)",
    "source_quote": "트렌드 관련 원문 발췌 (없으면 빈 문자열)"
  }},
  "channels": {{
    "online": ["주요 온라인 채널 리스트"],
    "offline": ["주요 오프라인 채널 리스트"],
    "details": "유통 채널 관련 요약 (1~2문장)",
    "source_quote": "유통 채널 관련 원문 발췌 (없으면 빈 문자열)"
  }},
  "competitors": {{
    "brands": [
      {{"name": "브랜드명", "description": "간단 설명"}}
    ],
    "details": "경쟁 구도 요약 (1~2문장)",
    "source_quote": "경쟁 브랜드 관련 원문 발췌 (없으면 빈 문자열)"
  }},
  "summary": "종합 시장 요약 (3~5문장)"
}}

규칙:
- 원문에 해당 정보가 없으면 빈 문자열("")이나 빈 리스트([])로 채우세요.
- 수치에는 반드시 출처 자료의 원본 수치를 사용하세요. 추측하지 마세요.
- source_quote는 원문에서 해당 수치/정보가 실제로 등장하는 문장을 그대로 발췌하세요 (번역 금지, 원어 그대로).
- source_quote에 해당하는 원문이 없으면 반드시 빈 문자열("")로 두세요. 만들어내지 마세요.
- 한국어로 작성하세요 (브랜드명, 채널명 등 고유명사는 원어 유지).
"""),
    ("human", "국가: {country}\n카테고리: {category}\n\n[원문 자료]\n{raw_text}"),
])


def _call_llm(category: str, country: str, raw_text: str) -> dict:
    """원문 텍스트를 LLM으로 구조화된 JSON으로 변환"""
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    chain = STRUCTURE_PROMPT | llm

    result = chain.invoke({
        "category": category,
        "country": country,
        "raw_text": raw_text[:15000],  # 토큰 제한 고려
    })

    text = result.content.strip()
    # ```json ... ``` 블록 제거
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]

    return json.loads(text)


def process_and_save(category: str, country: str, raw_text: str,
                     sources: list = None, research_month: str = None):
    """
    크롤링된 원문을 LLM으로 구조화하여 MarketResearch DB에 저장.

    Args:
        category: 화장품 카테고리 (예: "기초화장품")
        country: 국가 코드 (예: "JP", "US")
        raw_text: 크롤링된 원문 텍스트
        sources: 출처 URL 리스트
        research_month: 조사 월 (예: "2026-03"), 미지정 시 현재 월
    """
    if not research_month:
        research_month = datetime.now().strftime("%Y-%m")

    print(f"🔍 {category}-{country} 시장 데이터 구조화 중...")

    data = _call_llm(category, country, raw_text)

    obj, created = MarketResearch.objects.update_or_create(
        category=category,
        country=country,
        research_month=research_month,
        defaults={
            "market_size": data.get("market_size", {}),
            "kbeauty_share": data.get("kbeauty_share", {}),
            "trends": data.get("trends", {}),
            "channels": data.get("channels", {}),
            "competitors": data.get("competitors", {}),
            "raw_summary": data.get("summary", ""),
            "sources": sources or [],
        }
    )

    action = "신규 생성" if created else "업데이트"
    print(f"✅ {category}-{country} ({research_month}) DB {action} 완료")
    return obj


def get_research(category: str, country: str, research_month: str = None):
    """DB에서 시장 리서치 데이터 조회"""
    if not research_month:
        research_month = datetime.now().strftime("%Y-%m")

    try:
        return MarketResearch.objects.get(
            category=category,
            country=country,
            research_month=research_month,
        )
    except MarketResearch.DoesNotExist:
        # 해당 월 데이터가 없으면 가장 최신 데이터 반환
        return MarketResearch.objects.filter(
            category=category,
            country=country,
        ).order_by('-research_month').first()


def get_research_dict(category: str, country: str, research_month: str = None):
    """DB에서 조회 후 dict로 반환 (API 응답용)"""
    obj = get_research(category, country, research_month)
    if not obj:
        return None

    # data_source: channels 또는 market_size에서 deep_research_engine이 저장한 값 추출
    data_source = (
        (obj.market_size or {}).get("data_source")
        or (obj.channels or {}).get("data_source")
        or "unknown"
    )

    return {
        "category": obj.category,
        "country": obj.country,
        "research_month": obj.research_month,
        "market_size": obj.market_size,
        "kbeauty_share": obj.kbeauty_share,
        "trends": obj.trends,
        "channels": obj.channels,
        "competitors": obj.competitors,
        "summary": obj.raw_summary,
        "sources": obj.sources,
        "updated_at": obj.updated_at.isoformat(),
        "data_source": data_source,
    }
