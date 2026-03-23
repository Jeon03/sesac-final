# AI 광고 마케팅 전략 제안 — 설계 문서

---

## 개요

사용자 제품 정보와 경쟁 브랜드의 Meta 광고 데이터를 분석하여,
타겟 국가에 최적화된 **광고 브랜드 컨셉 · 핵심 메시징 · 추천 카피 · 마케팅 인사이트**를 자동 생성한다.

---

## 전체 파이프라인

```
[사용자 입력] → [광고 데이터 수집] → [전처리·분석] → [GPT 프롬프트 구성] → [GPT 생성] → [결과 출력]
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

### 1-2. 경쟁 브랜드 광고 데이터

| 항목 | 출처 | 설명 |
|------|------|------|
| 개별 광고 레코드 | `MetaAd` 모델 | 브랜드별 모든 광고 (문구, 유형, 게재일) |
| 채널 매핑 | US: ulta + sephora / JP: qoo10 + rakuten | 국가별 채널 |
| 필터 조건 | 최근 90일 (`start_date >= today - 90d`) | 활성 광고만 분석 |

### 1-3. 시장 트렌드 데이터

| 항목 | 출처 | 설명 |
|------|------|------|
| 인기 성분 | `MarketResearch.trends.ingredients` | 국가별 트렌드 성분 |
| 기능 트렌드 | `MarketResearch.trends.functions` | 국가별 기능성 트렌드 |
| 상세 정보 | `MarketResearch.trends.details` | 트렌드 배경 설명 |

---

## 2. 전처리 · 분석

### 2-1. 광고 데이터 집계

```python
# MetaAd에서 국가 채널의 최근 90일 광고 조회
ads = MetaAd.objects.filter(channel__in=channels, start_date__gte=cutoff)
```

**브랜드별 집계 항목:**

| 항목 | 설명 |
|------|------|
| `texts` | 해당 브랜드의 모든 광고 문구 리스트 |
| `image` | 이미지 광고 수 |
| `video` | 영상 광고 수 |
| `total` | 전체 광고 수 |

### 2-2. 광고 문구 키워드 빈도 분석

```python
# 전체 광고 문구에서 단어 빈도 집계 (2글자 이상)
word_counter = Counter()
for text in all_texts:
    words = [w.strip(".,!?\"'()[]") for w in text.split()]
    words = [w for w in words if len(w) >= 2]
    word_counter.update(words)

top_keywords = word_counter.most_common(30)
```

### 2-3. 전체 광고 유형 비율

```python
image_ratio = total_image / (total_image + total_video)
video_ratio = total_video / (total_image + total_video)
```

---

## 3. GPT 프롬프트 구성

### 3-1. System 메시지

- 역할: K-뷰티 브랜드 해외 진출 마케팅 전략 전문가
- 출력 형식: 지정된 JSON 구조로만 응답 요구

### 3-2. User 메시지에 포함되는 컨텍스트

| 섹션 | 내용 |
|------|------|
| 사용자 제품 정보 | 제품명, 카테고리, 성분, 효능 |
| 타겟 시장 | 국가명 |
| 시장 트렌드 | 인기 성분, 기능 트렌드, 상세 설명 |
| 광고 통계 요약 | 전체 광고 수, 이미지/영상 비율, 빈출 키워드 Top 15 |
| 브랜드별 광고 데이터 | 상위 6개 브랜드 × 최대 10개 광고 문구 + 유형별 수 |

### 3-3. GPT 파라미터

| 파라미터 | 값 | 이유 |
|----------|-----|------|
| 모델 | `gpt-4o` | 복합적 컨텍스트 분석 + 창의적 카피 생성 |
| temperature | `0.3` | 분석 근거 기반이되 약간의 창의성 허용 |

---

## 4. GPT 출력 구조

```json
{
  "brand_concept": "추천 브랜드 포지셔닝 컨셉 (영문, 한 문장)",
  "concept_reasoning": "브랜드 컨셉 선정 이유 (한국어, 2~3문장)",
  "key_messages": [
    "핵심 메시징 포인트 1",
    "핵심 메시징 포인트 2"
  ],
  "headline": "추천 광고 헤드라인 (영문)",
  "body_text": "추천 광고 본문 (영문, 2~3문장)",
  "detailed_insight": "상세 마케팅 인사이트 (한국어, 3~4문장)"
}
```

| 필드 | 설명 | 언어 |
|------|------|------|
| `brand_concept` | 시장에서 차별화 가능한 브랜드 포지셔닝 | 영문 |
| `concept_reasoning` | 경쟁사 분석·트렌드 기반 컨셉 선정 근거 | 한국어 |
| `key_messages` | 광고에서 강조할 핵심 소구점 (2개) | 혼합 |
| `headline` | 실제 광고에 사용 가능한 헤드라인 카피 | 영문 |
| `body_text` | 광고 본문 카피 | 영문 |
| `detailed_insight` | 시장 트렌드·경쟁사 패턴·제안 근거 통합 인사이트 | 한국어 |

---

## 5. 후처리 · 검증

### 5-1. JSON 파싱

```python
# GPT 응답에서 ```json ... ``` 감싸기 제거 후 파싱
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
    "total_ads": 총 분석 광고 수,
    "brand_count": 분석 브랜드 수,
    "image_ratio": 이미지 비율,
    "video_ratio": 영상 비율,
}
result["country"] = 타겟 국가 코드
```

---

## 6. 예외 처리

| 상황 | 처리 방법 |
|------|----------|
| MetaAd 데이터 없음 (0개 브랜드) | `{"error": "...시장의 Meta 광고 데이터가 없습니다."}` 반환 |
| MarketResearch 트렌드 없음 | 트렌드 필드를 "데이터 없음"으로 채워서 GPT에 전달 |
| GPT 응답 JSON 파싱 실패 | `{"error": "GPT 응답 파싱 실패", "raw_response": ...}` 반환 |
| 광고 문구가 대부분 비어있음 | 키워드 빈도·유형 비율 등 정량 데이터 + 트렌드로 보완 생성 |

---

## 7. DB 스키마

### MetaAd (개별 광고 레코드)

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `channel` | CharField(20) | ulta / sephora / qoo10 / rakuten |
| `brand` | CharField(200) | 브랜드명 |
| `library_id` | CharField(50) | Meta 광고 라이브러리 ID (unique with channel) |
| `media_type` | CharField(10) | image / video |
| `start_date` | DateField | 광고 게재 시작일 |
| `ad_text` | TextField | 광고 문구 |
| `page_id` | CharField(50) | Facebook 페이지 ID |
| `market` | CharField(2) | US / JP |

**인덱스:** `(channel, brand)`, `(market)`
**유니크:** `(channel, library_id)`

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
  "concept_reasoning": "전문적인 과학적 근거와 투명한 성분 공개를 강조하는...",
  "key_messages": [
    "피부 본연의 건강을 되찾아주는 72시간 장벽 보호",
    "불필요한 향료와 자극 성분을 배제한 고농축 진정 포뮬러"
  ],
  "headline": "Say Goodbye to Sensitive Skin Flare-ups.",
  "body_text": "Experience the power of Centella combined with Panthenol. Dermatologist-tested, Fragrance-free.",
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
- **레이아웃:** 파란 그라데이션 배경, 좌우 2컬럼
  - 좌측: 브랜드 컨셉 + 선정 이유 + 핵심 메시징
  - 우측: 추천 광고 카피 (Headline + Body) + Detailed Insight
