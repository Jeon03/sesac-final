# AI 최적 국가 추천 — 점수 설계 문서

> 최종 업데이트: 2026-03-29
> 주요 변경: 리뷰 카테고리 v2 세분화 적용, 정규화 방식 독립 범위로 변경, 가중치 조정

---

## 전체 AI Score 구성

```
AI Score (0~100) = 시장 규모 점수(50%) + 리뷰 유사도(35%) + 트렌드 적합도(15%)
```

---

## 1. 시장 규모 점수 (50%) — `calc_market_score()`

### 개요
국가별 시장 매력도를 5개 지표의 가중 합산으로 산출 (0~1 범위)

### 구성 지표 및 가중치

| 지표 | 가중치 | 데이터 출처 | 의미 |
|------|--------|-------------|------|
| K-뷰티 점유율 | 0.30 | `MarketResearch.kbeauty_share.share` | 시장 수용성 |
| 한국 화장품 수출 성장률 | 0.30 | `MarketStat.amount` (연도별 YoY) | 실제 판매 증거 |
| 시장 성장률(CAGR) | 0.20 | `MarketResearch.market_size.cagr` | 진입 타이밍 |
| K-뷰티 광고 활동량 | 0.10 | `MetaAdSummary.total_ads` (채널 합산) | 브랜드 투자 활동 증거 |
| 시장 규모 | 0.10 | `MarketResearch.market_size.value` | 절대적 기회 크기 |

### 계산 방법

**1. 각 지표 파싱**
- 시장 규모: `"$18.4B"` → `18.4` (단위: 십억 달러), T는 ×1000, M은 ÷1000
- 시장 성장률: `"6.96%"` → `0.0696`
- K-뷰티 점유율: `"15.8%"` → `0.158`
- 수출 성장률: 최근 3개 연도 기준 2개 YoY 평균
  ```
  YoY_1 = (2023년 수출액 - 2022년 수출액) / 2022년 수출액
  YoY_2 = (2024년 수출액 - 2023년 수출액) / 2023년 수출액
  수출 성장률 = (YoY_1 + YoY_2) / 2
  ```
- 광고 활동량: 국가별 채널(US: ulta+sephora, JP: qoo10+rakuten) `total_ads` 합산

**2. 독립 범위 정규화 (고정 상한/하한 기준)**

각 지표를 실측 데이터 기반 고정 범위로 0~1 정규화 (국가 간 상대 비교 아님)

```python
METRIC_RANGES = {
    "size":          (0.0,   30.0),   # 십억 달러 기준
    "growth":        (0.0,    0.15),  # CAGR 최대 15%
    "kbeauty":       (0.0,    0.50),  # K-뷰티 점유율 최대 50%
    "ad_activity":   (0.0, 5000.0),  # 채널 합산 광고수
    "export_growth": (-0.30,  0.50),  # 수출 성장률 -30%~+50%
}

정규화값 = max(0, min(1, (원값 - 하한) / (상한 - 하한)))
```

**3. 가중 합산**
```
시장 점수 = K뷰티점유율(0.30) + 수출성장률(0.30) + 성장률(0.20) + 광고활동(0.10) + 시장규모(0.10)
```

### 예외 처리

| 상황 | 처리 방법 |
|------|----------|
| 데이터 파싱 실패 | 해당 지표 0.5 적용 (중립값) |
| 수출 성장률 음수 | 그대로 반영 (불리한 시장으로 처리) |
| 연도 데이터 1개만 있음 | YoY 1개로 대체 |
| 연도 데이터 없음 | 0.0 반환 |
| MetaAdSummary 데이터 없음 | 0.0 반환 |

---

## 2. 리뷰 유사도 (35%) — `calc_review_score()`

### 개요
국가별 Top10 상품 리뷰 데이터를 기반으로, 해당 국가 소비자의 관심 카테고리와 사용자 제품의 효능이 얼마나 맞는지 계산 (모델 없이 순수 계산)

### 카테고리 체계 (v1 vs v2)

리뷰 카테고리는 두 버전이 공존하며 용도가 다름

| 버전 | 필드 | 용도 | 카테고리 예시 |
|------|------|------|---------------|
| v1 | `primary_category`, `categories` | 대시보드 표시 | `효과_성분`, `사용감_텍스처` |
| v2 | `primary_category_v2`, `categories_v2` | **점수산출 (본 문서)** | `보습_수분`, `미백_브라이트닝`, `주름_노화`, `진정_장벽`, `모공_각질` |

v2는 v1의 `효과_성분`을 효능별로 세분화한 버전. v1은 v2에서 매핑으로 자동 파생

```python
V2_TO_V1 = {
    "보습_수분":       "효과_성분",
    "미백_브라이트닝": "효과_성분",
    "모공_각질":       "효과_성분",
    "주름_노화":       "효과_성분",
    "진정_장벽":       "효과_성분",
}
```

### 사용 데이터

| 구분 | 데이터 | 출처 |
|------|--------|------|
| 국가 카테고리 성향 | Top10 상품의 `category_scores_v2` (리뷰 수 가중 평균) | `ReviewAnalysisCache` |
| 사용자 측 | 주요 성분, 핵심 효능 | 사용자 입력 |

### 계산 방법 상세

**Step 1. 국가별 카테고리 점수 집계 — `_get_country_review_data()`**

```python
# 플랫폼별 Top10 상품 순회 (US: Ulta+Sephora, JP: Qoo10+Rakuten → 각 최대 20개)
for each product:
    weight = review_count  # ReviewAnalysisCache.result["review_count"]
    # category_scores_v2 우선, 없으면 category_scores 폴백
    for each category_score in cache.result.get("category_scores_v2", category_scores):
        score_sum  += score * weight
        weight_sum += weight

avg_cat_scores[category] = score_sum / weight_sum  # 리뷰 수 가중 평균
```

**Step 2. 사용자 입력 → 관련 카테고리 추출 — `_user_to_categories()`**

입력 전체를 하나의 문자열로 합쳐 KEYWORD_CATEGORY_MAP에서 **부분 문자열 매칭**

```python
combined = f"{ingredients} {effects}".lower()

for keyword, categories in KEYWORD_CATEGORY_MAP.items():
    if keyword in combined:          # 부분 문자열 매칭
        matched.update(categories)
```

KEYWORD_CATEGORY_MAP (v2 세분류 기준):

| 입력 키워드 | 매핑 카테고리 |
|-------------|--------------|
| 보습, 수분, 촉촉, 히알루론산, 글리세린, 세라마이드, 판테놀 | `보습 / 수분` |
| 미백, 브라이트닝, 광채, 알부틴, 트라넥삼산, 나이아신아마이드, 비타민 c | `미백 / 브라이트닝` |
| 각질, 모공, 피지, 결 개선, AHA, BHA | `모공 / 각질` |
| 주름, 탄력, 항산화, 재생, 리프팅, 레티놀, 바쿠치올, 펩타이드, 아데노신 | `주름 / 노화` |
| 진정, 장벽, 시카, 병풀추출물, 마데카소사이드, 발효추출물, PDRN, 스피큘 | `진정 / 장벽` |
| AHA, BHA, 레티놀, 스피큘 | `피부 자극` (추가 매핑) |
| 발림, 흡수, 텍스처, 가벼, 끈적, 도포 | `발림성` |
| 향, 냄새, 아로마 | `향` |
| 자극, 민감, 트러블, 저자극, 예민 | `피부 자극` |
| 지속, 밀착, 유지 | `지속력` |
| 가성비, 가격, 합리 | `가격 적절성` |
| 커버, 색상, 발색 | `커버력 / 색상` |
| 재구매, 추천 | `재구매 / 추천` |

**Step 3. 최종 점수 산출**

```python
relevant = [avg_cat_scores[c] for c in user_categories if c in avg_cat_scores]
score = avg(relevant) / 5.0   # category_scores 척도: 0~5점 → 0~1 정규화
```

### 입력 예시 추적: "수분, 미백, 기능성, 주름 개선, 결 개선"

```
combined = "수분 미백 기능성 주름 개선 결 개선"

매칭 과정:
  "수분"   in combined → True  → 보습 / 수분
  "미백"   in combined → True  → 미백 / 브라이트닝
  "기능성" in combined → True  → 효과 / 성분
  "주름"   in "주름 개선" → True → 주름 / 노화
  "결 개선" in combined → True  → 모공 / 각질

user_categories = ["보습 / 수분", "미백 / 브라이트닝", "효과 / 성분", "주름 / 노화", "모공 / 각질"]
```

```
국가별 해당 카테고리 평균 별점 조회 후:

US: 매칭된 카테고리 별점 평균 / 5.0 → review_score
JP: 매칭된 카테고리 별점 평균 / 5.0 → review_score
```

> 주의: "주름 개선"은 띄어쓰기로 분리되어 `"주름"` 부분만 매칭됨. `"개선"` 단독으로는 매핑 없음.

### 예외 처리

| 상황 | 처리 방법 |
|------|----------|
| ReviewAnalysisCache 없음 | 0.5 중립값 적용 |
| 매핑된 카테고리가 국가 데이터에 없음 | 해당 카테고리 제외 후 나머지로 평균 |
| 사용자 입력이 맵에 전혀 없음 | `효과 / 성분` 카테고리로 폴백 |
| review_count 없거나 0 | 가중치 1로 대체 |
| `category_scores_v2` 없음 | `category_scores` (v1) 폴백 |

---

## 3. 트렌드 적합도 (15%) — `calc_trend_score()`

### 개요
사용자 제품의 성분·효능이 해당 국가의 시장 트렌드와 얼마나 부합하는지 측정.
GPT는 0-10 점수를 직접 채점하지 않고 **매칭 키워드 목록만 추출**, 점수는 코드에서 √ 스케일로 산출

### 사용 데이터

| 구분 | 데이터 | 출처 |
|------|--------|------|
| 사용자 측 | 주요 성분, 핵심 효능 | 사용자 입력 |
| 국가 측 | trends.ingredients, trends.functions, trends.details | `MarketResearch.trends` |

### 계산 방법 상세

**Step 1. 사용자 입력 토큰화**

```python
# 공백/쉼표로 분리
user_inputs = [k.strip() for k in re.split(r"[,\s]+", f"{ingredients} {effects}") if k.strip()]

# 예시: "수분 미백 기능성 주름 개선 결 개선"
# → ["수분", "미백", "기능성", "주름", "개선", "결", "개선"]
```

**Step 2. GPT 매칭 (temperature=0)**

```
입력: 사용자 성분/효능  vs  국가 트렌드 목록 (ingredients + functions)
요청: 의미적으로 일치하는 항목 추출 (한국어·영어 무관)
출력 JSON:
{
  "matched_keywords": ["Moisturizing", "Brightening"],
  "reasoning": "수분은 Moisturizing, 미백은 Brightening과 대응..."
}
```

**Step 3. 출력 검증 (환각 방지)**

```python
actual = set(ing_list + fn_list)  # 실제 트렌드 목록
verified = [k for k in gpt_result["matched_keywords"] if k in actual]
# GPT가 없는 항목을 날조해도 교차 검증으로 제거
```

**Step 4. 제곱근 스케일 점수**

```python
max_possible = min(len(user_inputs), len(ing_list + fn_list))
ratio = len(verified) / max_possible  # 0.0 ~ 1.0
score = ratio ** 0.5  # sqrt: 1개 매칭도 의미있는 점수 부여
```

제곱근을 사용하는 이유: 0개 매칭과 1개 매칭의 차이를 크게, 이후 증가는 완만하게

| 매칭 수 (max=6 기준) | 선형 ratio | √ratio (실제 점수) |
|---|---|---|
| 0개 | 0.00 | **0.00** |
| 1개 | 0.17 | **0.41** |
| 2개 | 0.33 | **0.58** |
| 3개 | 0.50 | **0.71** |
| 6개 | 1.00 | **1.00** |

→ 매칭 1개만 있어도 0.41점으로 의미있는 점수 부여, 매칭 0개는 0.0 (불이익)

**Step 5. 입력 예시 추적: "수분, 미백, 기능성, 주름 개선, 결 개선"**

```
user_inputs = ["수분", "미백", "기능성", "주름", "개선", "결", "개선"]  # len=7

US 트렌드 예시:
  ingredients = ["Hyaluronic Acid", "Niacinamide", "Retinol"]
  functions   = ["Moisturizing", "Anti-aging", "Brightening"]

GPT 매칭: ["Moisturizing", "Brightening"]  # "수분"→Moisturizing, "미백"→Brightening
검증 후 verified = 2개

max_possible = min(7, 6) = 6
score = sqrt(2/6) = 0.577

JP 트렌드 예시:
  ingredients = ["CICA", "Ferment", "Niacinamide"]
  functions   = ["Whitening", "Pore care", "Moisturizing"]

GPT 매칭: ["Whitening", "Pore care", "Moisturizing"]  # 3개 매칭
verified = 3개

score = sqrt(3/6) = 0.707
```

### 예외 처리

| 상황 | 처리 방법 |
|------|----------|
| trends 데이터 없음 | 0.5 중립값 적용 |
| GPT 응답 파싱 실패 | 0.5 중립값 적용 |
| 검증 후 매칭 0개 | 0.0 (불리하게 반영) |

### 부산물
- `reasoning` 텍스트 → 최종 선정 근거(`rationale`) 생성 시 재활용

---

## 4. 최종 합산 및 출력 — `recommend_countries()`

```python
ai_score = (trend_score * 0.15 + market_score * 0.50 + review_score * 0.35) * 100
```

### 입력 예시 최종 계산

```
"수분, 미백, 기능성, 주름 개선, 결 개선" 입력 시 (가상 수치):

US:
  트렌드 = sqrt(2/6) = 0.577
  시장   = 0.72  (K뷰티 점유율 낮지만 시장 규모 큼)
  리뷰   = avg([4.3, 4.1, 4.0]) / 5.0 = 0.827  (보습/주름/효과 카테고리)
  → ai_score = (0.577×0.15 + 0.72×0.50 + 0.827×0.35) × 100 = 74.4점

JP:
  트렌드 = sqrt(3/6) = 0.707
  시장   = 0.65
  리뷰   = avg([4.1, 4.4, 4.0, 4.2, 3.9]) / 5.0 = 0.824
  → ai_score = (0.707×0.15 + 0.65×0.50 + 0.824×0.35) × 100 = 73.2점

→ 추천 국가: US (74.4점)
```

### 반환 구조

```json
{
  "recommended_countries": [
    {
      "country": "US",
      "score": 74.4,
      "score_detail": { "total": 74.4, "trend": 57.7, "market": 72.0, "review": 82.7 },
      "trend_matched": ["Moisturizing", "Brightening"],
      "trend_reasoning": "수분은 Moisturizing...",
      "similar_brands": [...],
      "channels": {...},
      "market_research": {...}
    },
    { "country": "JP", ... }
  ],
  "top_country": { ... },
  "rationale": "미국 시장은 K-뷰티 보습 제품에 대한 소비자 만족도가 높으며..."
}
```

---

## 5. 데이터 파이프라인 구조

```
[크롤링]
  qoo10/rakuten/ulta/sephora *_reviews_master.jsonl
        ↓ pipeline_steps.py (번역 → KeyBERT → GPT 분류)
  *_final_categorized_v2.jsonl
    ├─ primary_category    (v1, 대시보드용)
    ├─ categories          (v1, 대시보드용)
    ├─ primary_category_v2 (v2, 점수산출용)
    └─ categories_v2       (v2, 점수산출용)
        ↓ manage.py load_review_data
[DB]
  ProductReview (primary_category, categories, primary_category_v2, categories_v2)
        ↓ build_analysis_cache()
  ReviewAnalysisCache.result
    ├─ category_scores     (v1, 대시보드 표시)
    └─ category_scores_v2  (v2, 점수산출)
        ↓ calc_review_score()
  리뷰 유사도 점수 (0~1)
```

### GPT 분류 파이프라인 (v2 기준 1회 실행)

```python
# pipeline_steps.py
# GPT는 CATEGORIES_V2로 1회만 분류
primary_category_v2 = GPT 분류 결과
categories_v2       = GPT 분류 결과

# V2_TO_V1 매핑으로 v1 자동 파생 (추가 API 호출 없음)
primary_category = V2_TO_V1.get(primary_category_v2, primary_category_v2)
categories       = [V2_TO_V1.get(c, c) for c in categories_v2]  # 중복 제거
```

---

## 6. 관련 파일 구조

| 파일 | 역할 |
|------|------|
| `market_api/services/country_recommender.py` | 점수 산출 메인 로직 |
| `market_api/services/review_analysis.py` | ReviewAnalysisCache 생성 로직 |
| `market_api/management/commands/load_review_data.py` | DB 적재 커맨드 |
| `crawling/pipeline_steps.py` | 리뷰 분류 파이프라인 |
| `market_api/models.py` | ProductReview, ReviewAnalysisCache 모델 |
| `docs/scoring_design.md` | 본 문서 |
