# 데이터 업데이트 가이드

> 최종 업데이트: 2026-03-30

---

## 전체 업데이트 순서

```
[1] migrate → [2] update_pipeline → [3] find_page_ids → [4] update_meta_ads → [5] ingest_research
```

각 단계는 이전 단계의 결과에 의존하므로 **순서대로 실행**해야 합니다.

---

## Step 1. 마이그레이션 적용

```bash
python manage.py migrate
```

- 새로운 모델/필드 변경사항을 DB에 반영
- 새 환경에서 처음 실행하거나, 코드 업데이트 후 반드시 실행

---

## Step 2. 채널별 크롤링 + 리뷰 분석

```bash
python manage.py update_pipeline --channel all
```

**개별 채널 실행:**
```bash
python manage.py update_pipeline --channel ulta
python manage.py update_pipeline --channel sephora
python manage.py update_pipeline --channel qoo10
python manage.py update_pipeline --channel rakuten
```

**파이프라인 내부 동작:**

| 순서 | 동작 | 결과물 |
|------|------|--------|
| ① | Top10 상품 크롤링 | `{channel}_rankings_current.jsonl` |
| ② | Rankings DB 업데이트 | `ProductRanking` 테이블 |
| ③ | Top10 상품 리뷰 크롤링 (기존 리뷰 만나면 중단) | `{channel}_reviews.jsonl` |
| ④ | 신규 리뷰 번역 + KeyBERT + GPT 분류 | 리뷰에 키워드·카테고리 부여 |
| ⑤ | Reviews DB 적재 | `ProductReview` 테이블 |
| ⑥ | 신규 리뷰 있는 상품 분석 캐시 재계산 | `ReviewAnalysisCache` 테이블 |

**소요 시간:** 채널당 10~30분 (리뷰 수에 따라 다름)

---

## Step 3. Meta 광고 페이지 ID 수집

```bash
python crawling/find_page_ids.py --channel ulta
python crawling/find_page_ids.py --channel sephora
python crawling/find_page_ids.py --channel qoo10
python crawling/find_page_ids.py --channel rakuten
```

**옵션:**
```bash
--force   # 이미 등록된 브랜드도 재검색
```

**동작:**
- Step 2에서 갱신된 Top10 브랜드 목록 기반
- Meta 광고 라이브러리에서 각 브랜드의 Facebook page_id 탐색
- 결과 저장: `crawling/brand_page_ids_all.json`

**주의:** Selenium(Chrome) 사용, 브라우저가 열리며 자동 검색

---

## Step 4. Meta 광고 크롤링 + DB 업데이트

```bash
python manage.py update_meta_ads --channel all
```

**개별 채널:**
```bash
python manage.py update_meta_ads --channel ulta
python manage.py update_meta_ads --channel sephora
python manage.py update_meta_ads --channel qoo10
python manage.py update_meta_ads --channel rakuten
```

**파이프라인 내부 동작:**

| 순서 | 동작 | 결과물 |
|------|------|--------|
| ① | `brand_page_ids_all.json` 기반 Meta 광고 크롤링 | CSV 파일 (`meta_crawling_result/`) |
| ② | Summary 집계 | `{channel}_meta_summary.csv` |
| ③ | DB 업데이트 | `MetaAdSummary` + `MetaAd` 테이블 |

**주의:** Playwright(Chromium) 사용, `HEADLESS=False`로 브라우저가 열림

---

## Step 5. 시장 리서치 데이터 갱신

```bash
python manage.py ingest_research --section-crawl
```

**동작:**
- 웹 크롤링으로 시장 데이터 수집
- LLM(GPT)으로 구조화 (시장 규모, CAGR, K-뷰티 점유율, 트렌드 등)
- 결과 저장: `MarketResearch` 테이블

---

## 기존 데이터만 DB에 로드 (크롤링 없이)

이미 크롤링된 파일이 있을 때, DB에만 넣고 싶은 경우:

```bash
# 랭킹 + 리뷰 + 분석캐시 (JSONL → DB)
python manage.py load_review_data

# Meta 광고 (CSV → DB)
python manage.py load_meta_ads
```

**개별 실행:**
```bash
python manage.py load_review_data --only rankings   # 랭킹만
python manage.py load_review_data --only reviews     # 리뷰만
python manage.py load_review_data --only cache       # 분석캐시만
```

---

## 의존성 관계도

```
update_pipeline (Step 2)
  └─ rankings_current.jsonl 생성
       │
       ▼
find_page_ids (Step 3)
  └─ brand_page_ids_all.json 생성
       │
       ▼
update_meta_ads (Step 4)
  └─ MetaAdSummary + MetaAd DB 저장
       │
       ▼
ingest_research (Step 5)
  └─ MarketResearch DB 저장
```

---

## 필요 파일 위치

| 파일 | 경로 | 생성 시점 |
|------|------|----------|
| 랭킹 JSONL | `crawling/{channel}_rankings_current.jsonl` | Step 2 |
| 리뷰 JSONL | `crawling/{channel}_reviews.jsonl` | Step 2 |
| 페이지 ID | `crawling/brand_page_ids_all.json` | Step 3 |
| Meta 광고 CSV | `crawling/meta_crawling_result/{channel}_meta.csv` | Step 4 |
| Meta 요약 CSV | `crawling/meta_crawling_result/{channel}_meta_summary.csv` | Step 4 |
