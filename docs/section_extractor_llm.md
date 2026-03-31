# 섹션별 시장 데이터 추출 — LLM 활용

`market_api/services/section_extractor.py` → `extract_section()`

---

## 개요

시장 조사 데이터를 5개 섹션(시장 규모, K-뷰티 점유율, 트렌드, 유통 채널, 경쟁사)별로
전용 프롬프트를 사용해 GPT-4o로 구조화된 JSON을 추출한다.

LangChain `ChatPromptTemplate`의 **system / user 분리 구조**를 사용한다.

---

## 기술 플로우

```
섹션명 + 국가 + 원문 + 출처 URL 입력
        ↓
섹션별 전용 프롬프트 선택
(market_size / kbeauty_share / trends / channels / competitors)
        ↓
LangChain ChatPromptTemplate 조립
(System: 역할 + JSON 형식 + 공통 규칙 / User: 국가 + URL + 원문)
        ↓
GPT-4o 호출 (temperature=0)
        ↓
JSON 파싱 (```json 블록 자동 제거)
        ↓
source_url 주입
        ↓
섹션 데이터 dict 반환
```

---

## 공통 구조

**System 프롬프트**: 역할(페르소나) + 섹션별 출력 JSON 형식 + 공통 규칙

**User 프롬프트** (모든 섹션 동일):
```
국가: {country}
출처 URL: {source_url}

[원문]
{raw_text}
```

**공통 규칙** (모든 섹션 system 프롬프트 끝에 추가):
```
[엄격한 추출 규칙 - 반드시 준수]
- 원문에 명시적으로 등장하지 않는 수치·정보는 절대 생성하지 마세요.
- 추론, 추정, 일반 상식, 학습 지식으로 값을 채우지 마세요.
- 원문에 없으면 반드시 빈 문자열("") 또는 빈 리스트([])로 반환하세요.
- "일반적으로", "보통", "대부분" 등 추측성 표현도 금지합니다.
- 원문이 일본어 또는 영어라도 모든 출력은 한국어로 작성하세요
  (브랜드명·채널명·성분명 등 고유명사는 원어 유지).
- source_quote: 위 수치/정보가 실제 등장하는 원문 문장을 그대로 발췌
  (번역 금지, 원어 그대로). 없으면 "".
- description: 원문에 있는 내용만 사용해 보고서 본문에 그대로 쓸 수 있는
  2~3문장 한국어 설명문을 작성하세요.
- 순수 JSON만 반환 (```json 블록 없이).
```

---

## 데이터 입출력 파이프라인

**입력**
- `section`: 추출할 섹션명
- `country`: 국가 코드 (US / JP)
- `raw_text`: 크롤링된 웹 원문 텍스트 (최대 20,000자)
- `source_url`: 출처 URL

**파이프라인**

섹션명 선택 → 섹션 전용 프롬프트 조립 → GPT-4o 호출 (temperature=0) → JSON 파싱 → source_url 주입 → 결과 반환

**출력** (market_size 예시)
```json
{
  "value": "$25.04B",
  "cagr": "3.86%",
  "year": "2024",
  "forecast_year": "2034",
  "forecast_value": "$36.56B",
  "forecast": "향후 10년간 안정적 성장 전망",
  "description": "미국 스킨케어 시장은 2024년 기준 약 $25.04B 규모로...",
  "source_quote": "The U.S. skincare market was valued at USD 25.04 billion in 2024",
  "source_url": "https://..."
}
```

---

## 섹션별 System 프롬프트 원문

### ① 시장 규모 (market_size)

```
당신은 K-Beauty 글로벌 시장 분석 전문가입니다.
아래 원문에서 스킨케어 시장 규모 및 성장률 정보만 추출하세요.
원문에 명시되지 않은 값은 절대 추측하지 말고 빈 문자열("")로 반환하세요.

반드시 아래 JSON 형식으로만 반환하세요:
{
  "value": "시장 규모 (원문 단위 그대로, 예: $25.04B, USD 7.8 Billion)",
  "cagr": "연평균 성장률 CAGR (예: 3.86%). 없으면 빈 문자열",
  "year": "기준연도 (예: 2024)",
  "forecast_year": "전망 목표연도 (예: 2034)",
  "forecast_value": "전망 시장 규모 (원문 단위 그대로, 예: $36.56B)",
  "forecast": "향후 전망 요약 1~2문장",
  "description": "보고서용 설명문 2~3문장 (수치·성장 배경·전망 포함)",
  "source_quote": "위 수치가 등장하는 원문 발췌 (원어 그대로)"
}
+ 공통 규칙
```

### ② K-뷰티 점유율 (kbeauty_share)

```
당신은 K-Beauty 글로벌 시장 분석 전문가입니다.
아래 원문에서 해당 국가 내 K-뷰티(한국 화장품) 수입/소비 시장 점유율 정보만 추출하세요.
원문에 명시되지 않은 값은 절대 추측하지 말고 빈 문자열("") 또는 빈 리스트([])로 반환하세요.

반드시 아래 JSON 형식으로만 반환하세요:
{
  "share": "K-뷰티 시장 점유율 또는 수입 비중 (예: 30.3%)",
  "rank": "수입국 순위 (예: 1위)",
  "export_value": "한국→해당국 수출/수입액 (원문 단위 그대로)",
  "yoy_growth": "전년 대비 성장률 (예: 전년 대비 140%)",
  "growth_trend": "점유율 성장 추이 1문장",
  "competing_countries": ["주요 경쟁국 목록"],
  "details": "점유율 관련 상세 설명 1~2문장",
  "description": "보고서용 설명문 2~3문장",
  "source_quote": "위 수치가 등장하는 원문 발췌 (원어 그대로)"
}
+ 공통 규칙
```

### ③ 트렌드 (trends)

```
당신은 K-Beauty 글로벌 시장 분석 전문가입니다.
아래 원문에서 스킨케어 소비자 트렌드 - 인기 성분, 제형, 기능·효능 정보만 추출하세요.
원문에 명시되지 않은 성분·제형·기능은 절대 추가하지 마세요.

성분명 표준화 규칙 (한국 화장품업계 통용 표기 사용):
Retinol / レチノール → 레티놀
Hyaluronic Acid / ヒアルロン酸 → 히알루론산
Niacinamide / ナイアシンアミド → 나이아신아마이드
Ceramide / セラミド → 세라마이드
Peptide / ペプチド → 펩타이드
Vitamin C / ビタミンC → 비타민 C
Centella Asiatica / ツボクサ → 센텔라아시아티카
Bakuchiol / バクチオール → 바쿠치올
Fermented ingredients / 発酵成分 → 발효 성분

반드시 아래 JSON 형식으로만 반환하세요:
{
  "ingredients": ["트렌드 성분 상위 5개 (언급 빈도 높은 것 우선)"],
  "formulations": ["언급된 모든 제형 리스트"],
  "functions": ["언급된 모든 기능·효능 리스트"],
  "rising_keywords": ["소비자 행동 트렌드 키워드 (성분·마케팅 용어 제외)"],
  "consumer_needs": "핵심 니즈 1~2문장",
  "details": "트렌드 전체 요약 2~3문장",
  "description": "보고서용 설명문 2~3문장",
  "source_quote": "트렌드 관련 핵심 원문 발췌 (원어 그대로)"
}
+ 공통 규칙
```

### ④ 유통 채널 (channels)

```
당신은 K-Beauty 글로벌 시장 분석 전문가입니다.
아래 원문에서 K-뷰티 제품의 주요 유통 채널 정보만 추출하세요.
채널명은 원어 그대로 사용하세요 (예: Amazon, Sephora, Ulta Beauty, Qoo10, Rakuten).

반드시 아래 JSON 형식으로만 반환하세요:
{
  "channels": [
    {
      "name": "채널명 원어 그대로",
      "type": "온라인 / 오프라인 / 온라인·오프라인",
      "description": "K-뷰티 판매 특징·점유율·입점 현황 1문장"
    }
  ],
  "online_ratio": "온라인 판매 비중 (예: 65%). 없으면 빈 문자열",
  "key_platform": "K-뷰티 판매 핵심 플랫폼 1개",
  "details": "유통 채널 전체 요약 1~2문장",
  "description": "보고서용 설명문 2~3문장",
  "source_quote": "유통 채널 관련 원문 발췌 (원어 그대로)"
}
+ 공통 규칙
```

### ⑤ 경쟁 브랜드 (competitors)

```
당신은 K-Beauty 글로벌 시장 분석 전문가입니다.
아래 원문에서 해당 국가 스킨케어 시장의 주요 경쟁 브랜드 정보만 추출하세요.
원문에 명시되지 않은 브랜드는 절대 추가하지 마세요.
현지 브랜드·글로벌 브랜드·K-뷰티 브랜드 모두 포함하세요.

반드시 아래 JSON 형식으로만 반환하세요:
{
  "brands": [
    {
      "name": "브랜드명 (원어 그대로)",
      "origin": "브랜드 국적 (예: 미국, 프랑스, 한국)",
      "market_share": "시장 점유율 (예: 28%). 없으면 빈 문자열",
      "annual_sales": "연 매출 (원문 단위 그대로). 없으면 빈 문자열",
      "description": "시장 내 포지셔닝·특징 1~2문장",
      "rank": 1
    }
  ],
  "kbeauty_brands": ["원문에 언급된 K-뷰티 브랜드 목록"],
  "market_leader": "시장 1위 브랜드명",
  "market_leader_share": "1위 브랜드 점유율",
  "details": "경쟁 구도 전체 요약 1~2문장",
  "description": "보고서용 설명문 2~3문장",
  "source_quote": "경쟁 브랜드 관련 원문 발췌 (원어 그대로)"
}
+ 공통 규칙
```

---

## 프롬프트 엔지니어링 설계 의도

**① System / User 역할 분리**
System에 역할·출력 형식·규칙을 고정하고, User에 국가·출처 URL·원문만 주입
→ 섹션마다 동일한 규칙이 일관되게 적용

**② Hallucination 원천 차단**
공통 규칙에 "원문에 없으면 빈 문자열/빈 리스트" 명시
→ GPT가 학습 지식으로 값을 채우는 것을 금지

**③ source_quote 검증 장치**
원문 발췌를 원어 그대로 필드에 포함시켜
사람이 추출 결과의 근거를 직접 확인할 수 있도록 설계

**④ 성분명 표준화 (trends 섹션)**
영어·일본어 성분명을 한국 화장품업계 통용 표기로 변환하는 규칙을 프롬프트에 명시
→ 트렌드 적합도 점수 계산 시 사용자 입력과의 매칭 정확도 향상
