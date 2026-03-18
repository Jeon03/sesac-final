"""
섹션별 특화 LLM 추출기.

각 시장 조사 항목(market_size, kbeauty_share, trends, channels, competitors)마다
전용 프롬프트로 해당 데이터만 정밀 추출.

출력 JSON에는 수치 외에도 보고서 작성용 description, source_url, source_quote 포함.
"""
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate


# ── 공통 규칙 (모든 프롬프트 끝에 추가) ──────────────────────────────────────
_COMMON_RULES = """
[엄격한 추출 규칙 - 반드시 준수]
- 원문에 명시적으로 등장하지 않는 수치·정보는 절대 생성하지 마세요.
- 추론, 추정, 일반 상식, 학습 지식으로 값을 채우지 마세요.
- 원문에 없으면 반드시 빈 문자열("") 또는 빈 리스트([])로 반환하세요.
- "일반적으로", "보통", "대부분" 등 추측성 표현도 금지합니다.
- 원문이 일본어 또는 영어라도 모든 출력은 한국어로 작성하세요 (브랜드명·채널명·성분명 등 고유명사는 원어 유지).
- source_quote: 위 수치/정보가 실제 등장하는 원문 문장을 그대로 발췌 (번역 금지, 원어 그대로). 없으면 "".
- description: 원문에 있는 내용만 사용해 보고서 본문에 그대로 쓸 수 있는 2~3문장 한국어 설명문을 작성하세요.
- 순수 JSON만 반환 (```json 블록 없이).
"""

# ── 1. 시장 규모·성장률 ────────────────────────────────────────────────────────
_MARKET_SIZE_SYSTEM = """당신은 K-Beauty 글로벌 시장 분석 전문가입니다.
아래 원문에서 **스킨케어 시장 규모 및 성장률** 정보만 추출하세요.
원문에 명시되지 않은 값은 절대 추측하지 말고 빈 문자열("")로 반환하세요.

반드시 아래 JSON 형식으로만 반환하세요:
{{
  "value": "시장 규모 (원문 단위 그대로, 예: $25.04B, USD 7.8 Billion)",
  "growth_rate": "전년 대비 성장률 (예: 0.6%). 없으면 빈 문자열",
  "cagr": "연평균 성장률 CAGR (예: 3.86%). 없으면 빈 문자열",
  "year": "기준연도 (예: 2024)",
  "forecast_year": "전망 목표연도 (예: 2034)",
  "forecast_value": "전망 시장 규모 (원문 단위 그대로, 예: $36.56B)",
  "forecast": "향후 전망 요약 1~2문장",
  "description": "보고서용 설명문 2~3문장 (수치·성장 배경·전망 포함)",
  "source_quote": "위 수치가 등장하는 원문 발췌 (원어 그대로)"
}}
""" + _COMMON_RULES

MARKET_SIZE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _MARKET_SIZE_SYSTEM),
    ("human", "국가: {country}\n출처 URL: {source_url}\n\n[원문]\n{raw_text}"),
])

# ── 2. K-뷰티 점유율 ──────────────────────────────────────────────────────────
_KBEAUTY_SHARE_SYSTEM = """당신은 K-Beauty 글로벌 시장 분석 전문가입니다.
아래 원문에서 **해당 국가 내 K-뷰티(한국 화장품) 수입/소비 시장 점유율** 정보만 추출하세요.
원문에 명시되지 않은 값은 절대 추측하지 말고 빈 문자열("") 또는 빈 리스트([])로 반환하세요.

원문이 일본어인 경우 수치와 내용을 정확히 번역하여 한국어로 작성하세요.
일본어 금액 단위는 원문 표기 그대로 유지하세요 (예: 1,342.7億円).

반드시 아래 JSON 형식으로만 반환하세요:
{{
  "share": "K-뷰티 시장 점유율 또는 수입 비중 (예: 30.3%). 없으면 빈 문자열",
  "rank": "수입국 순위 (예: 1위). 없으면 빈 문자열",
  "export_value": "한국→해당국 화장품 수출/수입액 (원문 단위 그대로, 예: 1,342.7億円, $10.2B). 없으면 빈 문자열",
  "yoy_growth": "전년 대비 성장률 (예: 전년 대비 140%). 없으면 빈 문자열",
  "growth_trend": "점유율 성장 추이 1문장. 없으면 빈 문자열",
  "competing_countries": ["주요 경쟁국 목록 (예: 프랑스, 미국). 없으면 빈 리스트"],
  "details": "점유율 관련 상세 설명 1~2문장",
  "description": "보고서용 설명문 2~3문장 (점유율 의미·배경·시사점 포함)",
  "source_quote": "위 수치가 등장하는 원문 발췌 (원어 그대로, 일본어면 일본어로)"
}}
""" + _COMMON_RULES

KBEAUTY_SHARE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _KBEAUTY_SHARE_SYSTEM),
    ("human", "국가: {country}\n출처 URL: {source_url}\n\n[원문]\n{raw_text}"),
])

# ── 3. 성분·기능 트렌드 ────────────────────────────────────────────────────────
_TRENDS_SYSTEM = """당신은 K-Beauty 글로벌 시장 분석 전문가입니다.
아래 원문에서 **스킨케어 소비자 트렌드 - 인기 성분, 제형, 기능·효능** 정보만 추출하세요.
원문에 명시되지 않은 성분·제형·기능은 절대 추가하지 마세요. 원문에 없으면 빈 리스트([])로 반환하세요.

성분명 표준화 규칙 (한국 화장품업계 통용 표기 사용):
- Retinol / レチノール → 레티놀
- Hyaluronic Acid / ヒアルロン酸 → 히알루론산
- Niacinamide / ナイアシンアミド → 나이아신아마이드
- Ceramide / セラミド → 세라마이드
- Peptide / ペプチド → 펩타이드
- Vitamin C / ビタミンC → 비타민 C
- Centella Asiatica / ツボクサ → 센텔라아시아티카
- Bakuchiol / バクチオール → 바쿠치올
- Fermented ingredients / 発酵成分 → 발효 성분
그 외 성분도 위와 같은 방식으로 한국 화장품업계 통용 표기로 작성하세요.

반드시 아래 JSON 형식으로만 반환하세요:
{{
  "ingredients": ["인기 성분 리스트 (최대 7개, 언급 빈도 높은 순, 한국 통용 표기)"],
  "formulations": ["인기 제형 리스트 (최대 5개, 예: 세럼, 크림, 토너, 에센스)"],
  "functions": ["인기 기능·효능 리스트 (최대 7개, 예: 보습, 미백, 안티에이징, 진정)"],
  "rising_keywords": ["최근 부상 중인 트렌드 키워드 (최대 5개). 없으면 빈 리스트"],
  "consumer_needs": "해당 국가 소비자의 핵심 니즈 1~2문장",
  "details": "트렌드 전체 요약 2~3문장",
  "description": "보고서용 설명문 2~3문장 (트렌드 배경·소비자 니즈·K-뷰티 시사점 포함)",
  "source_quote": "트렌드 관련 원문 발췌 (가장 핵심적인 문장, 원어 그대로)"
}}
""" + _COMMON_RULES

TRENDS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _TRENDS_SYSTEM),
    ("human", "국가: {country}\n출처 URL: {source_url}\n\n[원문]\n{raw_text}"),
])

# ── 4. 유통 채널 ──────────────────────────────────────────────────────────────
_CHANNELS_SYSTEM = """당신은 K-Beauty 글로벌 시장 분석 전문가입니다.
아래 원문에서 **K-뷰티 제품의 온·오프라인 유통 채널** 정보만 추출하세요.
원문에 명시되지 않은 채널은 절대 추가하지 마세요. 원문에 없으면 빈 리스트([])로 반환하세요.

채널명은 원어 그대로 사용하세요 (예: Amazon, Sephora, Ulta Beauty, Qoo10, Rakuten).

반드시 아래 JSON 형식으로만 반환하세요:
{{
  "online": [
    {{
      "name": "채널명 원어 그대로",
      "description": "K-뷰티 판매 특징·점유율 1문장",
      "rank": 1
    }}
  ],
  "offline": [
    {{
      "name": "채널명 원어 그대로",
      "description": "K-뷰티 입점 현황 또는 특징 1문장"
    }}
  ],
  "exclusive_deals": [
    {{
      "brand": "독점 계약 브랜드명",
      "channel": "독점 채널명",
      "type": "온라인 전용 / 오프라인 전용 / 전체 독점"
    }}
  ],
  "online_ratio": "온라인 판매 비중 (예: 65%). 없으면 빈 문자열",
  "key_platform": "K-뷰티 판매 핵심 플랫폼 1개",
  "details": "유통 채널 전체 요약 1~2문장",
  "description": "보고서용 설명문 2~3문장 (온·오프라인 비중·주요 채널·독점 계약 현황·진출 시사점 포함)",
  "source_quote": "유통 채널 관련 원문 발췌 (원어 그대로)"
}}

- online, offline: 원문에 언급된 채널만 포함. 원문에 없는 채널은 절대 추가하지 마세요.
- exclusive_deals: 원문에 독점 계약(exclusive) 관련 내용이 없으면 반드시 빈 리스트([]).
""" + _COMMON_RULES

CHANNELS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _CHANNELS_SYSTEM),
    ("human", "국가: {country}\n출처 URL: {source_url}\n\n[원문]\n{raw_text}"),
])

# ── 5. 경쟁 브랜드 ────────────────────────────────────────────────────────────
_COMPETITORS_SYSTEM = """당신은 K-Beauty 글로벌 시장 분석 전문가입니다.
아래 원문에서 **해당 국가 스킨케어 시장의 주요 경쟁 브랜드** 정보만 추출하세요.
원문에 명시되지 않은 브랜드는 절대 추가하지 마세요. 원문에 없으면 빈 리스트([]) 또는 빈 문자열("")로 반환하세요.
현지 브랜드·글로벌 브랜드·K-뷰티 브랜드 모두 포함하세요.

반드시 아래 JSON 형식으로만 반환하세요:
{{
  "brands": [
    {{
      "name": "브랜드명 (원어 그대로)",
      "origin": "브랜드 국적 (예: 미국, 프랑스, 일본, 한국)",
      "market_share": "시장 점유율 (예: 28%). 없으면 빈 문자열",
      "annual_sales": "연 매출 (원문 단위 그대로, 예: $1.2B). 없으면 빈 문자열",
      "description": "시장 내 포지셔닝·특징 1~2문장",
      "rank": 1
    }}
  ],
  "kbeauty_brands": ["원문에 언급된 K-뷰티 브랜드 목록. 없으면 빈 리스트"],
  "market_leader": "시장 1위 브랜드명. 없으면 빈 문자열",
  "market_leader_share": "1위 브랜드 점유율. 없으면 빈 문자열",
  "details": "경쟁 구도 전체 요약 1~2문장",
  "description": "보고서용 설명문 2~3문장 (경쟁 구도·K-뷰티 포지셔닝·진입 시사점 포함)",
  "source_quote": "경쟁 브랜드 관련 원문 발췌 (원어 그대로)"
}}

- brands는 최대 7개. rank는 원문 언급 순서 또는 매출/점유율 높은 순으로 부여.
""" + _COMMON_RULES

COMPETITORS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _COMPETITORS_SYSTEM),
    ("human", "국가: {country}\n출처 URL: {source_url}\n\n[원문]\n{raw_text}"),
])

# ── 섹션별 프롬프트 매핑 ──────────────────────────────────────────────────────
SECTION_PROMPTS = {
    "market_size":   MARKET_SIZE_PROMPT,
    "kbeauty_share": KBEAUTY_SHARE_PROMPT,
    "trends":        TRENDS_PROMPT,
    "channels":      CHANNELS_PROMPT,
    "competitors":   COMPETITORS_PROMPT,
}


def _parse_llm_json(text: str) -> dict:
    """LLM 응답에서 JSON 파싱 (```json 블록 자동 제거)"""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]
    return json.loads(text.strip())


def extract_section(
    section: str,
    country: str,
    raw_text: str,
    source_url: str,
    max_chars: int = 20000,
) -> dict:
    """
    단일 섹션 데이터를 LLM으로 추출.

    Args:
        section: 섹션명 (market_size / kbeauty_share / trends / channels / competitors)
        country: 국가 코드 (US / JP)
        raw_text: 크롤링된 원문 텍스트
        source_url: 출처 URL (결과 JSON에 주입)
        max_chars: LLM에 전달할 최대 문자수

    Returns:
        섹션 데이터 dict (source_url 포함)
    """
    prompt = SECTION_PROMPTS.get(section)
    if not prompt:
        raise ValueError(f"알 수 없는 섹션: {section}")

    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    chain = prompt | llm

    result = chain.invoke({
        "country": country,
        "source_url": source_url,
        "raw_text": raw_text[:max_chars],
    })

    data = _parse_llm_json(result.content)
    data["source_url"] = source_url  # URL 항상 주입
    return data


def extract_all_sections(
    country: str,
    crawled: dict[str, tuple[str, str]],
    category: str = "기초화장품",
) -> dict:
    """
    모든 섹션 데이터를 순서대로 LLM 추출.

    Args:
        country: 국가 코드
        crawled: {section: (text, source_url)} - section_crawler.crawl_all_sections() 결과
        category: 화장품 카테고리 (로그용)

    Returns:
        {section: extracted_dict} 형태의 전체 결과
    """
    results = {}

    for section, (text, url) in crawled.items():
        print(f"   [{country}] {section} LLM 추출 중...")

        if not text:
            print(f"      원문 없음 - 섹션 건너뜀")
            results[section] = {"source_url": url}
            continue

        try:
            data = extract_section(section, country, text, url)
            results[section] = data
            print(f"      추출 완료")
        except Exception as e:
            print(f"      추출 실패: {e}")
            results[section] = {"source_url": url, "error": str(e)}

    return results
