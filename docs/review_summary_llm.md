# 리뷰 통합 요약 — LLM 활용

`market_api/views.py` → `ReviewSummaryView`

---

## 개요

국가별 플랫폼 Top10 베스트셀러 상품들의 리뷰 요약을 GPT-4o-mini로 통합 요약한다.
플랫폼별로 1번씩 호출하며, US는 Ulta·Sephora 2회, JP는 Qoo10·Rakuten 2회 호출된다.

> `review_analysis_llm.md`의 리뷰 요약(상품 단위)과 다름.
> 이 기능은 **플랫폼 전체 Top10을 하나로 묶어** 통합 요약한다.

---

## 기술 플로우

```
GET /api/review-summary/?country=US
        ↓
플랫폼 목록 결정
US → [Ulta, Sephora] / JP → [Qoo10, Rakuten]
        ↓
플랫폼별 반복
        ↓
ProductRanking DB → Top10 상품 목록 조회
        ↓
상품별 ReviewAnalysisCache 조회
sample_reviews.positive / negative 수집
→ "[브랜드명] 요약문" 형태로 조립
        ↓
User 프롬프트 조립
(긍정 리뷰 목록 + 부정 리뷰 목록)
        ↓
GPT-4o-mini 호출 (temperature=0.3)
        ↓
응답 라인 파싱
"긍정:" → positive_summary
"부정:" → negative_summary
        ↓
플랫폼별 결과 반환
{top_products, positive_summary, negative_summary}
```

---

## 데이터 입출력 파이프라인

**입력**
- 쿼리 파라미터: `country` (US / JP)
- DB 데이터: `ProductRanking` → 플랫폼별 Top10 상품 목록
- DB 데이터: `ReviewAnalysisCache` → 상품별 `sample_reviews.positive` / `sample_reviews.negative`

**파이프라인**

`GET /api/review-summary/?country=US` → 플랫폼 목록 결정 (US: Ulta·Sephora) → 플랫폼별 Top10 상품 조회 → 상품별 긍정/부정 요약 수집 → `[브랜드명] 요약문` 형태로 조립 → GPT-4o-mini 호출 → 긍정/부정 파싱 → 결과 반환

**출력**
```json
{
  "country": "US",
  "platforms": {
    "Ulta": {
      "top_products": [{"rank": 1, "brand": "CeraVe", "title": "...", "rating": 4.7}, ...],
      "positive_summary": "세라마이드와 히알루론산 성분이 강점인 제품들이 보습 효과로 높은 만족도를 보이며...",
      "negative_summary": "일부 제품에서 향이 강하거나 무거운 텍스처에 대한 불만이 나타났습니다."
    },
    "Sephora": { ... }
  }
}
```

---

## 프롬프트 원문

시스템 프롬프트 없이 **user 메시지 단일 구성**.

```
다음은 Ulta Top 10 베스트셀러 스킨케어 상품들의 소비자 리뷰 요약입니다.

[긍정 리뷰]
[CeraVe] 세라마이드와 히알루론산 성분이 피부 장벽을 효과적으로 강화해 깊은 수분감을 제공합니다.
[La Roche-Posay] 민감한 피부에도 자극 없이 촉촉함이 오래 지속됩니다.
...

[부정 리뷰]
[CeraVe] 일부 소비자에게 향이 강하게 느껴져 민감한 피부에는 주의가 필요합니다.
[Neutrogena] 건성 피부에는 보습력이 다소 부족하다는 의견이 있습니다.
...

위 리뷰들을 종합하여 아래 형식으로 각각 2~3문장씩 통합 요약하세요.
긍정: ...
부정: ...

한국어로 작성하세요.
```

**Context 구성**:
- `ReviewAnalysisCache.sample_reviews.positive/negative` (상품 단위 1문장 요약)
- 각 항목에 `[브랜드명]` 레이블 붙여 어떤 브랜드 리뷰인지 구분

| 항목 | 내용 |
|------|------|
| 모델 | GPT-4o-mini |
| temperature | 0.3 |
| max_tokens | 400 |
| 출력 파싱 | `긍정:` / `부정:` 접두사로 라인 분리 |

---

## 프롬프트 엔지니어링 설계 의도

**① 상품 단위 요약을 재활용**
`review_analysis_llm.md`에서 생성된 상품별 1문장 요약을 그대로 context로 사용
→ 원본 리뷰 수천 건을 다시 처리하지 않고 이미 정제된 요약만 GPT에 전달

**② `[브랜드명]` 레이블 구조화**
각 요약 앞에 브랜드명을 붙여 입력
→ GPT가 어떤 브랜드의 반응인지 구분하며 통합 요약 가능

**③ 출력 형식 고정**
`긍정: ...` / `부정: ...` 접두사 지정
→ 코드에서 라인 파싱으로 두 항목을 분리 추출 가능
