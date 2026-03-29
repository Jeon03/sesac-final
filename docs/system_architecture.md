# 시스템 아키텍처 — K-Beauty 글로벌 진출 분석 플랫폼

> 작성일: 2026-03-29

---

## 전체 구성도

```
┌─────────────────────────────────────────────────────────────────┐
│                        Streamlit Dashboard                      │
│  시장분석 | 랭킹 | 리뷰 | Meta광고 | 국가추천 | 광고전략 | 리포트  │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP
┌────────────────────────────▼────────────────────────────────────┐
│                      Django REST API                            │
│  /api/match/  /api/country-recommend/  /api/ad-strategy/        │
│  /api/research/  /api/rankings/  /api/review-analysis/          │
│  /api/meta-ads/  /api/trade-stats/  /api/ad-image/              │
└──┬──────────┬──────────┬──────────┬──────────┬─────────────────┘
   │          │          │          │          │
   ▼          ▼          ▼          ▼          ▼
[시장리서치] [국가추천] [광고전략] [리뷰분석] [광고이미지]
   │          │          │          │          │
   ▼          ▼          ▼          ▼          ▼
┌─────────────────────────────────────────────────────────────────┐
│                         MySQL DB                                │
│  MarketResearch │ ProductRanking │ ProductReview                │
│  MarketStat     │ MetaAdSummary  │ ReviewAnalysisCache          │
│  HsClassification               │ MetaAd                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 서비스 레이어 상세

```
market_api/services/
│
├── 시장 리서치
│   ├── research_engine.py     GPT-4o로 원문 → 구조화 JSON
│   ├── section_extractor.py   섹션별 전용 프롬프트 (5종)
│   ├── section_crawler.py     고정 URL 크롤링 (BS4 + Selenium)
│   ├── tavily_searcher.py     Tavily 동적 웹검색
│   └── update_graph.py        LangGraph 업데이트 워크플로우
│
├── 점수 & 추천
│   └── country_recommender.py AI Score = 시장(50) + 리뷰(35) + 트렌드(15)
│
├── 광고 전략
│   ├── ad_strategy.py         경쟁사 Meta 광고 분석 → 전략 생성
│   └── ad_image.py            Gemini로 광고 이미지 2종 생성
│
├── 리뷰 분석
│   └── review_analysis.py     감성분류 + 카테고리 점수 + 기회 발굴
│
└── 무역 데이터
    ├── trass_service.py        관세청 TRASS API 수출통계
    └── hs_map.py               카테고리 → HS 코드 매핑
```

---

## 데이터 수집 파이프라인

```
[크롤링]
  Ulta / Sephora / Qoo10 / Rakuten
  Meta Ad Library
        │
        ▼ (JSONL 파일)
[ETL 커맨드]
  update_pipeline   → 랭킹 + 리뷰 크롤링 → 번역 → KeyBERT → GPT 분류
  load_review_data  → JSONL → ProductReview + ReviewAnalysisCache
  load_meta_ads     → CSV  → MetaAdSummary + MetaAd
  ingest_research   → LangGraph + Tavily → MarketResearch
```

---

## 외부 API

| 서비스 | 용도 |
|--------|------|
| OpenAI GPT-4o | 시장리서치 구조화, 국가추천 근거, 광고전략 |
| Google Gemini | 광고 이미지 생성 (2종 병렬) |
| Tavily | 웹 검색 (시장규모, 트렌드, 점유율 등) |
| 관세청 TRASS | 한국 화장품 수출 통계 |
| Meta Ad Library | 경쟁 브랜드 90일 광고 데이터 |

---

## 데이터 모델 관계

```
ProductRanking (platform × country × rank)
      │ 1:N
      ▼
ProductReview (리뷰 원문, 번역, 키워드, 카테고리)
      │ aggregated
      ▼
ReviewAnalysisCache (감성 점수, category_scores_v2)
      │ used by
      ▼
country_recommender → 리뷰 유사도 점수 (35%)

MarketResearch (market_size, kbeauty_share, trends, channels, competitors)
      │ used by
      ├─ country_recommender → 시장 규모 점수 (50%)
      └─ ad_strategy → 트렌드 기반 전략 생성

MarketStat (연도별 수출액)
      │ used by
      └─ country_recommender → 수출 성장률 (시장점수 내 30%)

MetaAdSummary (채널별 90일 광고량)
      │ used by
      ├─ country_recommender → 광고 활동량 (시장점수 내 10%)
      └─ ad_strategy → 경쟁사 광고 분석
```

---

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| Backend | Django 4 + DRF |
| Frontend | Streamlit + Plotly |
| DB | MySQL |
| LLM Orchestration | LangGraph, LangChain |
| 크롤링 | BeautifulSoup, Selenium, Playwright |
| NLP | KeyBERT, spaCy |
| 인프라 | Docker Compose |

---

## 관련 문서

| 문서 | 내용 |
|------|------|
| [scoring_design.md](scoring_design.md) | AI Score 점수 산출 알고리즘 상세 |
| [market_update_graph.md](market_update_graph.md) | LangGraph + Tavily 시장 업데이트 워크플로우 |
| [update_guide.md](update_guide.md) | 데이터 업데이트 실행 가이드 |
| [ad_strategy_design.md](ad_strategy_design.md) | 광고 전략 생성 설계 |
