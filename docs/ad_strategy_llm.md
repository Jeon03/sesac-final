# 광고 전략 생성 — LLM 활용

`market_api/services/ad_strategy.py` → `generate_ad_strategy()`

---

## 개요

경쟁 브랜드 Meta 광고 데이터 + 시장 트렌드 + 소비자 리뷰 분석을 종합해
GPT-4o가 타겟 국가에 최적화된 광고 전략을 생성한다. GPT 호출은 1회 발생한다.

---

## 기술 플로우

```
사용자 입력
(product_name, category, ingredients, effects, country)
        ↓
[DB 수집 - 3종]
MetaAd DB              MarketResearch DB       ReviewAnalysisCache DB
최근 90일               트렌드                   채널별 Top10 상품
경쟁 브랜드 광고 문구    (성분·기능)              긍정/부정 요약·불만
        ↓                    ↓                        ↓
        └────────────────────┴────────────────────────┘
                             ↓
             [코드] 트렌드 매칭 교집합 계산
             사용자 성분·효능 ∩ 시장 트렌드 목록
                             ↓
              System / User 프롬프트 조립
                             ↓
                     GPT-4o 호출
                    (temperature=0.3)
                             ↓
                      JSON 파싱
                             ↓
                        API 응답
     (brand_concept, key_messages, ad_copies, detailed_insight)
```

---

## 데이터 입출력 파이프라인

**입력**
- 사용자 입력: `product_name`, `category`, `ingredients`, `effects`, `country`
- DB 데이터:
  - `MetaAd` → 최근 90일 경쟁 브랜드 광고 문구·매체 비율
  - `MarketResearch.trends` → 인기 성분·기능 트렌드
  - `ReviewAnalysisCache` → 채널별 Top10 상품 긍정/부정 요약·불만 카테고리

**파이프라인**

사용자 입력 → Meta 광고 데이터 수집 → 트렌드 조회 → 리뷰 요약 수집 → 트렌드 매칭 교집합 계산 (코드) → System/User 프롬프트 조립 → GPT-4o 호출 (temperature=0.3) → JSON 파싱 → 결과 반환

**출력**
```json
{
  "brand_concept": "Skin That Speaks for Itself",
  "concept_reasoning": "CICA·세라마이드 성분이 미국 시장 트렌드와 정확히 일치하며...",
  "key_messages": ["장벽을 채우는 깊은 수분", "자극 없이 맑아지는 피부", "하루 종일 촉촉한 피부 장벽"],
  "ad_copies": [
    {"headline": "Your Skin, Restored.", "body_text": "CICA and Ceramide work together..."},
    {"headline": "Calm. Hydrate. Glow.", "body_text": "Feel the difference from the first drop..."}
  ],
  "detailed_insight": "미국 시장에서 CICA 성분은 최근 2년간 검색량이 급증했으며..."
}
```

---

## 프롬프트 원문

**System 프롬프트**:
```
당신은 K-뷰티 브랜드의 해외 진출을 돕는 마케팅 전략 전문가입니다.
미국 시장의 경쟁 브랜드 Meta 광고 데이터를 분석하고,
사용자의 제품에 최적화된 광고 전략과 카피를 제안해주세요.

중요: 광고 카피(brand_concept, ad_copies)는 반드시 영문(English)으로 작성하세요.

중요: key_messages(핵심 소구점) 작성 규칙
1. 반드시 사용자가 입력한 성분·효능으로 실제 뒷받침 가능한 내용만 작성하세요.
   - 제품 성분·효능에 없는 기능은 소구점으로 절대 사용하지 마세요.
   - 소비자 부정 리뷰 패턴이 있다면, 그 불만을 이 제품의 성분·효능이
     실제로 해결할 수 있는 경우에만 극복 소구점으로 활용하세요.
2. 화장품·뷰티 마케팅 언어로 작성하세요.
   - 고객이 느끼는 감각·감정·결과 중심
     ("피부가 촉촉하게 살아납니다", "자연스럽게 빛나는 피부톤" 등)
   - 기능/기술 설명 문체 금지
     ("멀티태스킹 기능", "효율적 루틴", "시간 절약" 같은 개발·비즈니스 용어 금지)
   - 짧고 감성적인 문장으로, 뷰티 브랜드 광고 카피처럼 작성

반드시 아래 JSON 형식으로만 응답하세요:
{
  "brand_concept": "추천 브랜드 포지셔닝 컨셉 (영문, 한 문장)",
  "concept_reasoning": "브랜드 컨셉 선정 이유 (한국어, 2~3문장)",
  "key_messages": ["핵심 소구점 1 (한국어)", "핵심 소구점 2 (한국어)", "핵심 소구점 3 (한국어)"],
  "ad_copies": [
    {"headline": "광고 헤드라인 A (영문)", "body_text": "광고 본문 A (영문, 2~3문장)"},
    {"headline": "광고 헤드라인 B (영문)", "body_text": "광고 본문 B (영문, 2~3문장)"}
  ],
  "detailed_insight": "상세 마케팅 인사이트 (한국어, 3~4문장)"
}
```

**User 프롬프트**:
```
## 사용자 제품 정보
- 제품명: {product_name}
- 카테고리: {category}
- 주요 성분: {ingredients}
- 핵심 효능: {effects}

## 타겟 시장: 미국

## 미국 시장 트렌드
- 인기 성분: {trend_ingredients}
- 기능 트렌드: {trend_functions}
- 상세: {trend_details}

## 제품-시장 트렌드 매칭 분석
- 제품 성분 중 시장 트렌드와 일치: {matched_ingredients}
- 제품 효능 중 시장 트렌드와 일치: {matched_functions}
→ 위 매칭 포인트가 있다면 이를 광고 전략과 핵심 소구점의 중심으로 활용하세요.

## 경쟁 브랜드 Meta 광고 분석 (최근 90일)
- 전체 광고 수: {total_ads}건
- 이미지 비율: {image_ratio}% / 영상 비율: {video_ratio}%
- 광고 문구 내 빈출 키워드: {top_keywords}

### 브랜드별 광고 데이터
**CeraVe** (총 142건, 이미지 98건, 영상 44건)
  - "Developed with dermatologists"
  - "Ceramide-rich formula for lasting hydration"
  ...

## 미국 채널별 인기 상품 리뷰 요약
### ULTA 인기 상품 리뷰 요약
  #1 {product_title}
    - 긍정: {positive_summary}
    - 주요 불만: {complaint_labels}
...

## 소비자 부정 리뷰 패턴 (화장품 관련만)
  - {negative_summary_1}
  - {negative_summary_2}
  ...
→ 위 부정 리뷰 패턴 중, 사용자 제품의 성분·효능으로 실제 해결 가능한
  불만에 한해서만 극복 소구점을 key_messages에 포함하세요.
```

**Context 구성**:
- 사용자 입력: 제품명·카테고리·성분·효능
- 코드 계산 결과: 성분·효능과 트렌드 목록의 교집합 (`matched_ingredients`, `matched_functions`)
- DB 데이터: 경쟁 브랜드별 광고 문구 (상위 4개 브랜드 × 최대 30개 문구), 빈출 키워드 15개
- DB 데이터: 채널별 Top10 상품 긍정 요약·불만 카테고리
- DB 데이터: 부정 리뷰 요약 최대 20개 (포장/배송·고객서비스·제품불량 제외)

---

## 프롬프트 엔지니어링 설계 의도

**① 트렌드 매칭 교집합 사전 계산**
사용자 성분·효능과 시장 트렌드 목록의 교집합을 코드에서 직접 계산해 프롬프트에 명시
→ GPT가 임의로 강점을 추정하지 않고 실제 데이터 기반 소구점 생성 유도

**② 불만 사항 필터링 규칙 명시**
포장·배송·고객서비스·제품불량 관련 불만은 DB 수집 단계에서 제외 후 전달
System 프롬프트에 "성분·효능으로 해결 가능한 불만만 소구점 활용" 명시
→ 제품과 무관한 불만이 마케팅 전략에 섞이는 것을 방지

**③ 언어·어조 제어**
국가별 카피 언어 분기 (US → 영문, JP → 일본어)
"개발·비즈니스 용어 금지" 명시 → 감성 마케팅 언어 강제

**④ 출력 필드 역할 분리**
- `brand_concept`: 국가 언어 (US=영문, JP=일본어)
- `key_messages`: 한국어 (내부 검토용)
- `ad_copies`: 국가 언어 (실제 광고 집행용)
- `detailed_insight`: 한국어 (전략 보고서용)
