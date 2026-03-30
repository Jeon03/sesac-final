# Meta 광고 라이브러리 수집 및 업데이트 기술서

> 최종 업데이트: 2026-03-30
> 대상 파일: `crawling/find_page_ids.py`, `crawling/crawl_meta.py`, `market_api/management/commands/load_meta_ads.py`

---

## 전체 파이프라인

```
[Step 1] find_page_ids.py
  → 브랜드명으로 Meta 광고 라이브러리 검색
  → Facebook page_id 수동 확인 후 저장
  → brand_page_ids_all.json

        │
        ▼

[Step 2] crawl_meta.py (crawl(channel))
  → page_id 기반 광고 라이브러리 페이지 접근
  → Playwright로 스크롤 + 광고 카드 파싱
  → {channel}_meta.csv / _meta_90.csv / _meta_summary.csv

        │
        ▼

[Step 3] manage.py load_meta_ads
  → CSV → MetaAdSummary (집계) + MetaAd (개별) 테이블 저장
```

---

## Step 1. 브랜드 Page ID 수집 — `find_page_ids.py`

### 목적

Meta 광고 라이브러리는 page_id 기반으로 브랜드 광고를 조회한다.
브랜드명만으로는 직접 접근이 불가능하므로, 사전에 브랜드명 → page_id 매핑을 구축한다.

### 수집 대상

`{channel}_rankings_current.jsonl` 기반으로 Top10 브랜드 목록을 자동 추출.

| 채널 | 시장 | 브랜드 필드 |
|------|------|------------|
| ulta | US | `brand` |
| sephora | US | `brand` |
| qoo10 | JP | `shop_name` |
| rakuten | JP | `shop_name` |

### 수집 방식 — GraphQL typeahead 인터셉트

Meta 광고 라이브러리의 검색창 클릭 시 발생하는 GraphQL 자동완성 응답(`typeahead_suggestions`)을 Selenium Performance 로그로 가로채 page_id를 추출한다.

```
1. Selenium headless Chrome으로 Meta 광고 라이브러리 접근
2. 검색창 클릭 → 자동완성 GraphQL 요청 유도
3. Chrome DevTools Protocol(CDP) 네트워크 로그 파싱
4. facebook.com/api/graphql/ 응답에서 typeahead_suggestions 추출
   - page_results / exact_page_results / filtered_page_results
5. IG 팔로워 수 기준 내림차순 정렬 후 터미널에 후보 목록 출력
```

### 운영자 수동 확인

자동 수집 후 반드시 운영자가 확인하고 선택한다.

```
  번호  이름                           Page ID              IG 팔로워  카테고리
  ────────────────────────────────────────────────────────────────────────
  0     CeraVe                         123456789012345      2,450,000  Beauty
  1     CeraVe Korea                   987654321098765      12,000     Beauty

  선택 (0-1, s=skip, q=전체종료): 0
  → 저장 완료: CeraVe (123456789012345)
```

### 출력 파일

`crawling/brand_page_ids_all.json`

```json
{
  "ulta": {
    "market": "US",
    "brands": {
      "CeraVe": { "page_id": "123456789012345" },
      "Neutrogena": { "page_id": "234567890123456" }
    }
  },
  "qoo10": {
    "market": "JP",
    "brands": {
      "COSRX": { "page_id": "345678901234567" }
    }
  }
}
```

### 실행 방법

```bash
python crawling/find_page_ids.py --channel ulta
python crawling/find_page_ids.py --channel sephora
python crawling/find_page_ids.py --channel qoo10
python crawling/find_page_ids.py --channel rakuten

# 이미 등록된 브랜드도 재검색
python crawling/find_page_ids.py --channel ulta --force
```

---

## Step 2. 광고 수집 — `crawl_meta.py`

### 목적

page_id 기반으로 Meta 광고 라이브러리 페이지에 접근해 브랜드별 광고 카드를 전수 수집한다.

### 수집 방식 — Playwright 자동화

```
1. Chromium 브라우저 실행 (HEADLESS=False, 자동화 탐지 우회)
2. brand_page_ids_all.json에서 채널별 브랜드 × page_id 로드
3. 브랜드별로 광고 라이브러리 URL 접근
   https://www.facebook.com/ads/library/?...&view_all_page_id={page_id}
4. 스크롤 반복 (최대 40회, 2.2초 간격) → 광고 카드 로드
5. [data-testid="ad-library-dynamic-content-container"] 기준 광고 카드 파싱
6. 브랜드당 최대 200개 수집
```

### 광고 카드 파싱 필드

```python
{
    "brand":       브랜드명,
    "page_id":     Facebook 페이지 ID,
    "market":      "US" | "JP",
    "retailer":    채널명 (ulta / sephora / qoo10 / rakuten),
    "library_id":  광고 라이브러리 ID (10자리 이상 숫자),
    "media_type":  "image" | "video",
    "start_date":  "YYYY-MM-DD" (게재 시작일),
    "ad_text":     광고 문구 (20자 이상 첫 번째 라인),
}
```

날짜 파싱은 4가지 패턴 지원: `YYYY.MM.DD`, `YYYY-MM-DD`, `YYYY/MM/DD`, `YYYY年MM月DD日`

### 집계 (90일 기준)

수집 완료 후 90일 필터 + 브랜드별 집계:

```python
summary = {
    "brand":          브랜드명,
    "total_ads":      90일 내 총 광고 수,
    "image_ads":      이미지 광고 수,
    "video_ads":      영상 광고 수,
    "image_ratio":    이미지 비율 (0~1),
    "video_ratio":    영상 비율 (0~1),
    "latest_ad_date": 가장 최근 광고 게재일,
    "recent_30d_ads": 최근 30일 광고 수,
}
```

### 출력 파일

| 파일 | 내용 |
|------|------|
| `{channel}_meta.csv` | 전체 수집 원본 |
| `{channel}_meta_90.csv` | 90일 필터 적용본 |
| `{channel}_meta_summary.csv` | 브랜드별 집계 요약 |

### Windows 호환

asyncio ProactorEventLoop를 별도 스레드에서 실행 (Windows 기본 이벤트 루프 호환):

```python
def _thread():
    loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(loop)
    result["ads"] = loop.run_until_complete(_crawl_async(channel))

t = threading.Thread(target=_thread)
t.start(); t.join()
```

### 실행 방법

Django 관리 커맨드를 통해 호출:

```bash
python manage.py update_meta_ads --channel all
python manage.py update_meta_ads --channel ulta
python manage.py update_meta_ads --channel sephora
python manage.py update_meta_ads --channel qoo10
python manage.py update_meta_ads --channel rakuten
```

---

## Step 3. DB 적재 — `load_meta_ads.py`

### 목적

CSV 파일을 읽어 `MetaAdSummary`(브랜드 집계)와 `MetaAd`(개별 광고) 테이블에 저장한다.

### 처리 흐름

```
{channel}_meta_summary.csv → MetaAdSummary (update_or_create by channel+brand)
{channel}_meta_90.csv      → MetaAd        (update_or_create by channel+library_id)
```

### MetaAdSummary 저장 필드

| 필드 | 출처 |
|------|------|
| total_ads, image_ads, video_ads | summary CSV |
| image_ratio, video_ratio | summary CSV |
| latest_ad_date, recent_30d_ads | summary CSV |
| latest_ad_text | raw CSV에서 가장 최근 광고 문구 추출 |
| page_id | brand_page_ids_all.json 매핑 |

### MetaAd 저장 필드

`library_id`가 있는 레코드만 저장 (빈 더미 행 제외).

| 필드 | 출처 |
|------|------|
| brand, media_type, start_date | raw CSV |
| ad_text, page_id, market | raw CSV |

### 실행 방법

```bash
python manage.py load_meta_ads
```

---

## DB 스키마

### MetaAdSummary — 브랜드별 90일 집계

| 컬럼 | 타입 | 설명 |
|------|------|------|
| channel | CharField(20) | ulta / sephora / qoo10 / rakuten |
| brand | CharField(200) | 브랜드명 |
| total_ads | IntegerField | 90일 내 총 광고 수 |
| image_ads / video_ads | IntegerField | 유형별 광고 수 |
| image_ratio / video_ratio | FloatField | 유형별 비율 |
| latest_ad_date | DateField | 가장 최근 광고 게재일 |
| recent_30d_ads | IntegerField | 최근 30일 광고 수 |
| latest_ad_text | TextField | 가장 최근 광고 문구 |
| page_id | CharField(50) | Facebook 페이지 ID |

**유니크:** `(channel, brand)`

### MetaAd — 개별 광고 레코드

| 컬럼 | 타입 | 설명 |
|------|------|------|
| channel | CharField(20) | 플랫폼 채널 |
| library_id | CharField(50) | Meta 광고 라이브러리 ID |
| brand | CharField(200) | 브랜드명 |
| media_type | CharField(10) | image / video |
| start_date | DateField | 광고 게재 시작일 |
| ad_text | TextField | 광고 문구 |
| page_id | CharField(50) | Facebook 페이지 ID |
| market | CharField(2) | US / JP |

**유니크:** `(channel, library_id)`

---

## 활용

수집된 데이터는 두 가지 서비스에서 사용된다.

| 서비스 | 사용 테이블 | 용도 |
|--------|------------|------|
| `country_recommender.py` | MetaAdSummary | 광고 활동량 지표 → 시장 규모 점수(10%) |
| `ad_strategy.py` | MetaAd | 경쟁사 광고 문구 분석 → GPT 전략 생성 |

---

## 관련 문서

| 문서 | 내용 |
|------|------|
| [update_guide.md](update_guide.md) | 전체 업데이트 순서 (Step 3, 4) |
| [ad_strategy_design.md](ad_strategy_design.md) | 광고 전략 생성 설계 |
| [scoring_design.md](scoring_design.md) | 광고 활동량이 점수에 반영되는 방식 |
