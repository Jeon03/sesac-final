# AI 광고 마케팅 전략 제안 — 설계 문서

> 최종 업데이트: 2026-03-30
> 대상 파일: `market_api/services/ad_strategy.py`

---

## 개요

사용자 제품 정보와 4가지 데이터 소스를 종합하여,
타겟 국가에 최적화된 **광고 브랜드 컨셉 · 핵심 소구점 · 추천 카피 · 마케팅 인사이트**를 GPT-4o로 자동 생성한다.

---

## 전체 파이프라인

```
[사용자 입력]
     ↓
[① Meta 광고 데이터 수집]   [② 시장 트렌드 조회]   [③ 리뷰 요약 수집]
     ↓                              ↓                       ↓
[④ 제품-트렌드 매칭 분석]  ←──────────────────────────────┘
     ↓
[⑤ GPT 프롬프트 구성]
     ↓
[⑥ GPT-4o 호출]
     ↓
[⑦ JSON 파싱 · 후처리]
     ↓
[결과 출력]
```

---

## 1. 데이터 수집

### 1-1. 사용자 입력 데이터

| 항목 | 설명 | 예시 |
|------|------|------|
| 제품명 | 사용자 제품 이름 | "시카 장벽 크림" |
| 카테고리 | 제품 분류 | "스킨케어" |
| 주요 성분 | 핵심 성분 목록 | "병풀 추출물, 판테놀" |
| 핵심 효능 | 제품 소구 포인트 | "장벽 강화, 진정" |
| 타겟 국가 | 국가 추천 결과에서 자동 결정 | "US" |

### 1-2. 경쟁 브랜드 Meta 광고 데이터

| 항목 | 출처 | 설명 |
|------|------|------|
| 개별 광고 레코드 | `MetaAd` 모델 | 브랜드별 광고 문구·유형·게재일 |
| 채널 매핑 | US: ulta + sephora / JP: qoo10 + rakuten | 국가별 채널 |
| 필터 조건 | 최근 90일 (`start_date >= today - 90d`) | 활성 광고만 분석 |
| 브랜드 선택 | 광고 수 기준 상위 4개 브랜드 × 최대 30개 문구 | GPT 컨텍스트 최적화 |

### 1-3. 시장 트렌드 데이터

| 항목 | 출처 | 설명 |
|------|------|------|
| 인기 성분 | `MarketResearch.trends.ingredients` | 국가별 트렌드 성분 |
| 기능 트렌드 | `MarketResearch.trends.functions` | 국가별 기능성 트렌드 |
| 상세 정보 | `MarketResearch.trends.details` | 트렌드 배경 설명 (최대 300자) |

### 1-4. 소비자 리뷰 요약 데이터

채널별 Top10 상품(총 최대 20개)의 `ReviewAnalysisCache`에서 수집.

| 항목 | 출처 | 설명 |
|------|------|------|
| 긍정 요약 | `sample_reviews.positive` | GPT 생성 1문장 요약 |
| 부정 요약 | `sample_reviews.negative` | GPT 생성 1문장 요약 |
| 불만 카테고리 | `complaints` | 화장품 관련 상위 3개 카테고리 레이블 |

**부정 리뷰 필터링 — 제외 카테고리:**

| 제외 카테고리 | 이유 |
|-------------|------|
| 포장 / 배송 | 제품 성능과 무관 |
| 고객서비스 | 제품 성능과 무관 |
| 제품불량 | 마케팅 전략 컨텍스트에서 제외 |

---

## 2. 제품-시장 트렌드 매칭 분석

사용자 제품 성분·효능과 시장 트렌드 성분·기능의 **교집합**을 사전에 계산하여 GPT에 명시적으로 전달한다.

```python
matched_ingredients = [i for i in trend_ingredient_list if i.lower() in user_ingredients_lower]
matched_functions   = [f for f in trend_function_list   if f.lower() in user_effects_lower]
```

**목적:** GPT가 임의로 강점을 추정하지 않고, 실제 제품이 시장 트렌드와 겹치는 포인트를 전략의 중심으로 활용하도록 유도.

---

## 3. GPT 프롬프트 구성

### 3-1. System 메시지

- 역할: K-뷰티 브랜드 해외 진출 마케팅 전략 전문가
- 출력 형식: 지정된 JSON 구조로만 응답
- 광고 카피 언어: US → 영문 / JP → 일본어

**key_messages 생성 규칙 (system에 명시):**

1. 사용자 제품 성분·효능으로 실제 뒷받침 가능한 내용만 작성
2. 소비자 부정 리뷰 패턴이 있을 경우, 제품이 실제로 해결 가능한 불만에 한해서만 극복 소구점으로 활용
3. 화장품·뷰티 마케팅 감성 언어 사용 (고객이 느끼는 감각·감정·결과 중심)
4. 개발·비즈니스 용어 금지 ("멀티태스킹 기능", "효율적 루틴", "시간 절약" 등)
5. 뷰티 브랜드 광고 카피 스타일의 짧고 감성적인 문장

### 3-2. User 메시지 구성 (순서)

| 섹션 | 내용 |
|------|------|
| ① 사용자 제품 정보 | 제품명, 카테고리, 성분, 효능 |
| ② 시장 트렌드 | 인기 성분, 기능 트렌드, 상세 설명 |
| ③ 제품-시장 트렌드 매칭 | 교집합 계산 결과 + 전략 중심 활용 지시 |
| ④ Meta 광고 통계 | 전체 광고 수, 매체 비율, 빈출 키워드 Top15 |
| ⑤ 브랜드별 광고 문구 | 상위 4개 브랜드 × 최대 30개 문구 |
| ⑥ 긍정 리뷰 요약 | 채널별 Top10 상품 긍정 반응 |
| ⑦ 소비자 부정 리뷰 패턴 | 채널 2개 × Top10 = 최대 20개 부정 요약 + 극복 소구점 활용 지시 |

### 3-3. GPT 파라미터

| 파라미터 | 값 | 이유 |
|----------|-----|------|
| 모델 | `gpt-4o` | 복합 컨텍스트 분석 + 창의적 카피 생성 |
| temperature | `0.3` | 분석 근거 기반이되 약간의 창의성 허용 |

---

## 4. GPT 출력 구조

```json
{
  "brand_concept": "추천 브랜드 포지셔닝 컨셉 (영문 또는 일본어, 한 문장)",
  "concept_reasoning": "브랜드 컨셉 선정 이유 (한국어, 2~3문장)",
  "key_messages": [
    "핵심 소구점 1 (한국어, 뷰티 마케팅 언어)",
    "핵심 소구점 2 (한국어, 뷰티 마케팅 언어)",
    "핵심 소구점 3 (한국어, 뷰티 마케팅 언어)"
  ],
  "ad_copies": [
    {
      "headline": "광고 헤드라인 A (영문/일본어)",
      "body_text": "광고 본문 A (영문/일본어, 2~3문장)"
    },
    {
      "headline": "광고 헤드라인 B (영문/일본어)",
      "body_text": "광고 본문 B (영문/일본어, 2~3문장)"
    }
  ],
  "detailed_insight": "상세 마케팅 인사이트 (한국어, 3~4문장. 시장 트렌드·경쟁사 광고 패턴·제안 근거 포함)"
}
```

| 필드 | 설명 | 언어 |
|------|------|------|
| `brand_concept` | 시장에서 차별화 가능한 브랜드 포지셔닝 | 영문/일본어 |
| `concept_reasoning` | 경쟁사 분석·트렌드 기반 컨셉 선정 근거 | 한국어 |
| `key_messages` | 광고에서 강조할 핵심 소구점 3개 (성분·효능 기반, 뷰티 감성 언어) | 한국어 |
| `ad_copies` | 실제 광고에 사용 가능한 헤드라인+본문 카피 2세트 | 영문/일본어 |
| `detailed_insight` | 시장 트렌드·경쟁사 패턴·제안 근거 통합 인사이트 | 한국어 |

---

## 5. 후처리 · 검증

### 5-1. JSON 파싱

```python
cleaned = raw.strip()
if cleaned.startswith("```"):
    cleaned = cleaned.split("\n", 1)[1]
if cleaned.endswith("```"):
    cleaned = cleaned.rsplit("```", 1)[0]
result = json.loads(cleaned.strip())
```

### 5-2. 광고 통계 메타데이터 첨부

```python
result["ad_stats"] = {
    "total_ads": int,       # 총 분석 광고 수
    "brand_count": int,     # 분석 브랜드 수
    "image_ratio": float,   # 이미지 광고 비율
    "video_ratio": float,   # 영상 광고 비율
}
result["country"] = str     # 타겟 국가 코드
```

---

## 6. 예외 처리

| 상황 | 처리 방법 |
|------|----------|
| MetaAd 데이터 없음 | `{"error": "...시장의 Meta 광고 데이터가 없습니다."}` 반환 |
| MarketResearch 트렌드 없음 | 트렌드 필드를 "데이터 없음"으로 채워서 GPT에 전달 |
| 트렌드 매칭 결과 없음 | "없음"으로 표시, GPT가 성분·효능 기반으로 자체 판단 |
| ReviewAnalysisCache 없음 | 해당 섹션 생략, 나머지 데이터로 전략 생성 |
| GPT 응답 JSON 파싱 실패 | `{"error": "GPT 응답 파싱 실패", "raw_response": ...}` 반환 |

---

## 7. DB 스키마

### MetaAd (개별 광고 레코드)

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `channel` | CharField(20) | ulta / sephora / qoo10 / rakuten |
| `brand` | CharField(200) | 브랜드명 |
| `library_id` | CharField(50) | Meta 광고 라이브러리 ID |
| `media_type` | CharField(10) | image / video |
| `start_date` | DateField | 광고 게재 시작일 |
| `ad_text` | TextField | 광고 문구 |
| `page_id` | CharField(50) | Facebook 페이지 ID |
| `market` | CharField(2) | US / JP |

**인덱스:** `(channel, brand)`, `(market)`
**유니크:** `(channel, library_id)`

### ReviewAnalysisCache (리뷰 분석 캐시)

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `platform` | CharField(20) | ulta / sephora / qoo10 / rakuten |
| `platform_item_id` | CharField(100) | 상품 ID |
| `result` | JSONField | 분석 결과 전체 |

**result JSON 구조 (전략 관련 필드):**
```json
{
  "sample_reviews": {
    "positive": "긍정 리뷰 1문장 요약",
    "negative": "부정 리뷰 1문장 요약"
  },
  "complaints": [
    {"label": "효과 / 성분", "pct": 42},
    {"label": "발림성", "pct": 28}
  ]
}
```

---

## 8. API 명세

### `POST /api/ad-strategy/`

**Request Body:**
```json
{
  "product_name": "시카 장벽 크림",
  "category": "스킨케어",
  "ingredients": "병풀 추출물, 판테놀",
  "effects": "장벽 강화, 진정",
  "country": "US"
}
```

**Response (200):**
```json
{
  "brand_concept": "Clean & Science-Backed Skin Barrier Solution",
  "concept_reasoning": "미국 시장에서 'Skin Barrier Repair' 트렌드가 급상승 중이며...",
  "key_messages": [
    "병풀이 피부 장벽을 한 겹 한 겹 되살려냅니다",
    "자극받은 피부가 하루 만에 편안해지는 진정 포뮬러",
    "소비자들이 아쉬워했던 그 보습력, 판테놀이 채워드립니다"
  ],
  "ad_copies": [
    {
      "headline": "Say Goodbye to Sensitive Skin Flare-ups.",
      "body_text": "Experience the power of Centella combined with Panthenol. Dermatologist-tested, Fragrance-free."
    },
    {
      "headline": "Your Skin Barrier, Restored.",
      "body_text": "Clinically proven ingredients work overnight to rebuild and strengthen your skin's natural defense."
    }
  ],
  "detailed_insight": "현재 미국 MZ세대 사이에서는 'Skin Barrier Repair' 검색량이 전년 대비 45% 증가했습니다...",
  "ad_stats": {
    "total_ads": 342,
    "brand_count": 12,
    "image_ratio": 0.65,
    "video_ratio": 0.35
  },
  "country": "US"
}
```

---

## 9. 대시보드 배치

- **위치:** 대시보드 최하단 (국가별 시장 분석 탭 아래)
- **트리거:** 추천 1위 국가(`top_country`) 기준 자동 호출
- **레이아웃:** 파란 그라데이션 배경
  - 상단: 브랜드 컨셉 + 선정 이유
  - 좌측: 핵심 소구점 3개 카드
  - 우측: 광고 시안 2세트 (헤드라인 + 본문 + AI 생성 이미지)
  - 하단: 상세 마케팅 인사이트
