"""
딥리서치 엔진 - Tavily 웹 검색으로 최신 시장 데이터 수집 후 LLM 구조화 저장.

크롤링 데이터가 없거나 보완이 필요할 때 사용.
폴백 전략: 크롤링 원문 → Tavily 딥리서치 → LLM 파라메트릭 지식 추정 → N/A
"""
import os
import json
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

DEEP_RESEARCH_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """당신은 K-Beauty 글로벌 시장 분석 전문가입니다.
아래 제공되는 웹 검색 결과를 분석하여, 지정된 국가의 **K-뷰티(한국 화장품) 수입/소비 시장** 정보를 구조화된 JSON으로 추출하세요.

⚠️ 중요 추출 기준:
- market_size.value: 해당 국가에서 K-뷰티(한국 화장품) 제품이 소비되는 시장 규모. 전체 뷰티 시장이 아닌 K-뷰티 특화 수치를 우선. USD 기준으로 변환하여 표기 (예: $2.1B). 엔화나 다른 통화는 반드시 달러로 환산.
- market_size.growth_rate / cagr: K-뷰티 카테고리의 성장률. 전체 시장 성장률과 혼용 금지. 단일 연도 급등(예: 코로나 회복기)이 아닌 안정적 CAGR 우선.
- kbeauty_share.share: 해당 국가 전체 수입 화장품 또는 뷰티 시장에서 K-뷰티가 차지하는 점유율(%).

반드시 아래 JSON 형식만 반환하세요 (설명 텍스트 없이 순수 JSON만):
{{
  "market_size": {{
    "value": "K-뷰티 시장 규모 USD 기준 (예: $2.1B). 엔/위안 등 외화는 달러로 환산",
    "growth_rate": "전년 대비 성장률 (예: 6.96%). 단일연도 급등 수치 지양",
    "cagr": "연평균 성장률 (예: 6.96%)",
    "forecast": "향후 전망 요약 (1~2문장)",
    "year": "기준연도 (예: 2024)",
    "source_quote": "위 수치가 포함된 원문 발췌 (없으면 빈 문자열)"
  }},
  "kbeauty_share": {{
    "share": "해당국 뷰티/화장품 수입 시장 내 K-뷰티 점유율 (예: 15.8%)",
    "details": "점유율 관련 상세 설명 (1~2문장)",
    "source_quote": "위 수치가 포함된 원문 발췌 (없으면 빈 문자열)"
  }},
  "trends": {{
    "ingredients": ["인기 성분 리스트 (최대 5개)"],
    "formulations": ["인기 제형 리스트 (최대 5개)"],
    "functions": ["인기 기능/효능 리스트 (최대 5개)"],
    "details": "트렌드 요약 (2~3문장)",
    "source_quote": "트렌드 관련 원문 발췌 (없으면 빈 문자열)"
  }},
  "channels": {{
    "online": [
      {{"name": "채널명 (예: Sephora, Ulta, Amazon / Qoo10, Rakuten, Amazon Japan)", "description": "K-뷰티 판매 특징 또는 점유율 설명 (1문장)", "rank": 1}},
      {{"name": "2순위 채널명", "description": "K-뷰티 판매 특징 (1문장)", "rank": 2}},
      {{"name": "3순위 채널명", "description": "K-뷰티 판매 특징 (1문장)", "rank": 3}}
    ],
    "offline": [
      {{"name": "채널명 (예: Target, Costco / 백화점, 드럭스토어)", "description": "특징 (1문장)"}}
    ],
    "online_ratio": "온라인 비중 (예: 65%)",
    "details": "유통 채널 전체 요약 (1~2문장)",
    "source_quote": "유통 채널 관련 원문 발췌 (없으면 빈 문자열)"
  }},
  "competitors": {{
    "brands": [
      {{"name": "브랜드명", "description": "간단 설명", "rank": 1}}
    ],
    "details": "경쟁 구도 요약 (1~2문장)",
    "source_quote": "경쟁 브랜드 관련 원문 발췌 (없으면 빈 문자열)"
  }},
  "top_products": [
    {{"rank": 1, "name": "제품명", "brand": "브랜드", "channel": "주요 판매 채널", "feature": "핵심 특징"}}
  ],
  "summary": "종합 시장 요약 (3~5문장)",
  "data_source": "원문 수치 사용 시 'verified', 추정값 포함 시 'estimated'"
}}

규칙:
- 원문에 해당 정보가 없으면 빈 문자열("")이나 빈 리스트([])로 채우세요.
- 수치는 반드시 출처 자료의 원본 수치를 기반으로 하세요. 없으면 비워두세요.
- source_quote는 원문에서 해당 수치/정보가 실제로 등장하는 문장을 그대로 발췌하세요 (번역 금지, 원어 그대로).
- source_quote에 해당하는 원문이 없으면 반드시 빈 문자열("")로 두세요. 만들어내지 마세요.
- 엔화(JPY) 등 외화는 1 USD = 150 JPY 기준으로 달러 환산하여 표기하세요.
- 전체 뷰티 시장 수치를 K-뷰티 수치로 오해하지 마세요.
- 한국어로 작성하세요 (브랜드명, 채널명 등 고유명사는 원어 유지).
- top_products는 실제 언급된 제품만 포함하고, 없으면 빈 리스트로 두세요.
- channels.online은 반드시 3개 이상 포함하세요. 원문에 없으면 해당 국가의 K-뷰티 유통에서 잘 알려진 채널(US: Sephora·Ulta·Amazon, JP: Qoo10·Rakuten·Amazon Japan)을 포함하세요.
"""),
    ("human", "국가: {country}\n카테고리: {category}\n\n[수집 자료]\n{raw_text}"),
])


def _call_llm_deep(category: str, country: str, raw_text: str) -> dict:
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    chain = DEEP_RESEARCH_PROMPT | llm

    result = chain.invoke({
        "category": category,
        "country": country,
        "raw_text": raw_text[:20000],
    })

    text = result.content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]

    return json.loads(text)


def _tavily_search(category: str, country_name: str) -> tuple[str, list[str]]:
    """Tavily로 웹 검색. TAVILY_API_KEY 없으면 빈 결과 반환."""
    try:
        from tavily import TavilyClient
    except ImportError:
        print("⚠️  tavily-python 미설치. pip install tavily-python")
        return "", []

    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        print("⚠️  TAVILY_API_KEY 미설정. 웹 검색 건너뜁니다.")
        return "", []

    client = TavilyClient(api_key=api_key)

    # 현재 날짜 기준으로 연도 동적 생성
    now = datetime.now()
    this_year = now.year
    last_year = this_year - 1

    # 목적별 세분화 쿼리 (현재 시점 기준)
    queries = [
        f"K-beauty {category} market size CAGR growth rate {country_name} {last_year} {this_year} report",
        f"Korean cosmetics {category} consumer trends ingredients {country_name} {this_year}",
        f"top selling K-beauty {category} products Amazon Sephora Qoo10 Rakuten {country_name} {this_year}",
        f"K-beauty {category} distribution channels online offline retailers {country_name} {this_year}",
        f"K-beauty {category} competitive brands market share {country_name} local vs Korean {this_year}",
        f"K-beauty {category} export statistics South Korea to {country_name} {last_year}",
    ]
    print(f"   - 검색 기준 연도: {last_year}~{this_year}")

    all_texts = []
    sources = []

    for query in queries:
        try:
            results = client.search(query=query, search_depth="advanced", max_results=5)
            for r in results.get("results", []):
                content = r.get("content", "")
                url = r.get("url", "")
                if content:
                    all_texts.append(f"[출처: {url}]\n{content}")
                if url:
                    sources.append(url)
        except Exception as e:
            print(f"⚠️  Tavily 검색 실패 ({query[:40]}...): {e}")

    return "\n\n---\n\n".join(all_texts), list(set(sources))


def run_deep_research(
    category: str,
    country: str,
    extra_crawled_text: str = "",
    research_month: str = None,
    force: bool = False,
) -> object:
    """
    딥리서치 실행 후 MarketResearch DB에 저장.

    Args:
        category: 화장품 카테고리
        country: 국가 코드 (US, JP)
        extra_crawled_text: 팀원 크롤링 원문 (선택, 있으면 병합)
        research_month: 조사 월 (미지정 시 현재 월)
        force: True면 기존 DB 데이터 덮어쓰기

    Returns:
        MarketResearch 인스턴스
    """
    from market_api.models import MarketResearch

    if not research_month:
        research_month = datetime.now().strftime("%Y-%m")

    # force=False이고 이미 데이터가 있으면 스킵
    if not force:
        exists = MarketResearch.objects.filter(
            category=category,
            country=country,
            research_month=research_month,
        ).exists()
        if exists:
            print(f"⏭️  {category}-{country} ({research_month}) 이미 존재. --force로 덮어쓰기 가능.")
            return MarketResearch.objects.get(
                category=category, country=country, research_month=research_month
            )

    country_name_map = {"US": "United States", "JP": "Japan"}
    country_name = country_name_map.get(country, country)

    print(f"🌐 딥리서치 시작: {category} - {country_name}")

    # 1. Tavily 웹 검색
    web_text, web_sources = _tavily_search(category, country_name)

    # 2. 크롤링 원문 병합 (크롤링 데이터 우선)
    parts = []
    if extra_crawled_text.strip():
        parts.append(f"[팀 크롤링 자료]\n{extra_crawled_text}")
    if web_text:
        parts.append(f"[웹 검색 결과]\n{web_text}")

    combined_text = "\n\n===\n\n".join(parts)

    if not combined_text.strip():
        print(f"⚠️  {category}-{country} 수집된 자료 없음. LLM 지식 기반으로 추정합니다.")
        combined_text = f"위 카테고리({category})의 {country_name} 시장에 대한 별도 수집 자료가 없습니다. 보유한 지식으로 최대한 분석해주세요."

    print(f"   - 웹 검색 {len(web_sources)}개 소스 수집")
    print(f"   - 크롤링 원문: {'있음' if extra_crawled_text.strip() else '없음'}")
    print(f"   - LLM 구조화 중...")

    data = _call_llm_deep(category, country, combined_text)

    all_sources = list(set(web_sources))
    data_source = data.get("data_source", "estimated")

    # market_size에 data_source 주입 (get_research_dict가 읽어서 대시보드에 전달)
    market_size = data.get("market_size", {})
    market_size["data_source"] = data_source

    # top_products를 channels에 저장 (별도 모델 필드 없이)
    channels = data.get("channels", {})
    top_products = data.get("top_products", [])
    if top_products:
        channels["top_products"] = top_products

    obj, created = MarketResearch.objects.update_or_create(
        category=category,
        country=country,
        research_month=research_month,
        defaults={
            "market_size": market_size,
            "kbeauty_share": data.get("kbeauty_share", {}),
            "trends": data.get("trends", {}),
            "channels": channels,
            "competitors": data.get("competitors", {}),
            "raw_summary": data.get("summary", ""),
            "sources": all_sources,
        }
    )

    action = "신규 생성" if created else "업데이트"
    data_src = data.get("data_source", "unknown")
    print(f"✅ {category}-{country} 딥리서치 DB {action} 완료 (출처 신뢰도: {data_src})")
    return obj
