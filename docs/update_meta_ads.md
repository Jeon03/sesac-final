# 메타 광고 데이터 업데이트 파이프라인 기술 명세

`market_api/management/commands/update_meta_ads.py` + `crawling/crawl_meta.py`

---

## 개요

채널별(Ulta / Sephora / Qoo10 / Rakuten) Top10 브랜드의 Meta 광고 라이브러리를
Playwright로 크롤링하여 최근 90일 광고 통계를 집계하고 `MetaAdSummary` DB를 갱신한다.

전체 흐름은 **2단계**로 구성된다:
1. `find_page_ids.py` — 신규 브랜드의 Facebook page_id 수집 (사전 준비, Human-in-the-Loop)
2. `update_meta_ads.py` — page_id 기반 광고 크롤링 + DB 갱신 (정기 실행)

> LLM 미사용 — Selenium GraphQL 인터셉트 + Playwright 브라우저 자동화 크롤링 파이프라인

```
python find_page_ids.py --channel ulta       # 사전 준비 (랭킹 변동 시)
python manage.py update_meta_ads --channel ulta
python manage.py update_meta_ads --channel all
```

---

## 기술 플로우

### 1단계 — 브랜드 page_id 수집 (`find_page_ids.py`)

```
랭킹 파일에서 Top10 브랜드 목록 추출
        ↓
brand_page_ids_all.json에서 기등록 브랜드 확인
(--force 없으면 기등록 브랜드 skip)
        ↓
신규 브랜드별 반복
        ↓
Selenium Chromium 실행 (headless)
Meta 광고 라이브러리 검색 URL 접속
검색창 클릭 → GraphQL typeahead_suggestions 요청 유도
        ↓
네트워크 로그 인터셉트 (CDP: Network.getResponseBody)
GraphQL 응답에서 page_id · ig_followers · likes 파싱
IG 팔로워 내림차순 정렬
        ↓
터미널에 후보 목록 출력
관리자 선택 (번호 입력 / s=skip / q=종료) → Human-in-the-Loop
        ↓
brand_page_ids_all.json 저장
```

### 2단계 — 광고 크롤링 + DB 갱신 (`update_meta_ads.py`)

```
[1] 랭킹 파일 로드 (rankings_current.jsonl)
채널별 Top10 브랜드 목록 추출
        ↓
[2] brand_page_ids_all.json 로드
브랜드명 → Meta 페이지 ID 매핑
JP 채널: 공백·대소문자 정규화 후 매칭
        ↓
[3] Playwright Chromium 실행 (headless=False)
automation 감지 우회 설정 적용
        ↓
브랜드별 반복
        ↓
[4] Meta 광고 라이브러리 URL 접속
https://www.facebook.com/ads/library/?view_all_page_id={page_id}
        ↓
[5] 페이지 스크롤 (최대 40회, 2.2초 간격)
광고 카드 로드 대기
        ↓
[6] 광고 카드 파싱
library_id / media_type(image·video) / start_date / ad_text 추출
중복 제거 (library_id 기준), 브랜드당 최대 200개
        ↓
[7] CSV 저장
{channel}_meta.csv (전체)
{channel}_meta_90.csv (최근 90일)
{channel}_meta_summary.csv (집계)
        ↓
[8] 통계 집계 (_summarize)
브랜드별: total_ads / image_ads / video_ads / image_ratio / video_ratio
         latest_ad_date / recent_30d_ads
        ↓
[9] MetaAdSummary DB 갱신
현재 Top10 이탈 브랜드 삭제
최신 집계 데이터 update_or_create
        ↓
완료
```

---

## 데이터 입출력 파이프라인

**1단계 입력**: 랭킹 파일 (`*_rankings_current.jsonl`) → 신규 브랜드만 처리

**1단계 파이프라인**

랭킹 파일 → Top10 브랜드 추출 → 기등록 여부 확인 → Selenium Meta 검색 → GraphQL 인터셉트(CDP) → IG 팔로워 정렬 후 후보 출력 → 관리자 선택 → `brand_page_ids_all.json` 저장

**2단계 입력**: `python manage.py update_meta_ads --channel ulta|sephora|qoo10|rakuten|all`

**2단계 파이프라인**

실행 커맨드 → 랭킹 파일에서 브랜드 목록 추출 → page_id 매핑 로드 → Playwright Chromium 실행 → 브랜드별 Meta 광고 라이브러리 접속 → 스크롤로 광고 카드 로드 → 카드 inner_text 파싱(날짜·텍스트·media_type) → CSV 저장 → 90일 필터 + 집계 → MetaAdSummary DB update_or_create → 완료

**출력**

```json
{
  "channel": "ulta",
  "brand": "CeraVe",
  "total_ads": 142,
  "image_ads": 98,
  "video_ads": 44,
  "image_ratio": 0.690,
  "video_ratio": 0.310,
  "latest_ad_date": "2024-11-28",
  "recent_30d_ads": 12,
  "latest_ad_text": "Developed with dermatologists"
}
```

---

## 채널별 처리 차이

| 채널 | 시장 | 브랜드명 필드 | page_id 매칭 방식 |
|------|------|---------------|-------------------|
| Ulta | US | `brand` | 정확 일치 |
| Sephora | US | `brand` | 정확 일치 |
| Qoo10 | JP | `shop_name` | 공백·대소문자 제거 후 정규화 매칭 |
| Rakuten | JP | `shop_name` | 공백·대소문자 제거 후 정규화 매칭 |

---

## 광고 카드 파싱 규칙

**날짜 추출** (`_extract_date`): 4가지 날짜 패턴 정규식 순차 시도
- `2024.11.28` / `2024-11-28` / `2024/11/28` / `2024年11月28日`

**텍스트 추출** (`_extract_text`): inner_text에서 광고 본문 추출
- 20자 초과 라인만 대상
- 시스템 문구 제외: "라이브러리 ID", "게재 시작", "광고 상세 정보 보기", "플랫폼" 등

**media_type**: inner_text에 "video" 또는 "동영상" 포함 여부로 판별

---

## 설계 의도

**① 랭킹 변동 시에만 page_id 수집 실행**
`find_page_ids.py`는 신규 브랜드가 Top10에 진입했을 때만 수동 실행
→ 기등록 브랜드는 skip하여 불필요한 Selenium 실행 방지
→ 관리자가 후보 목록에서 직접 선택 (Human-in-the-Loop) — 자동 매칭 오류 방지

**② automation 감지 우회**
`navigator.webdriver = undefined` 스크립트 주입 + 일반 User-Agent 설정
→ Meta 광고 라이브러리의 봇 차단 회피

**② Top10 이탈 브랜드 삭제**
현재 채널 Top10에 없는 브랜드는 MetaAdSummary에서 제거
→ 오래된 경쟁사 데이터가 광고 전략 분석에 혼입되지 않도록 방지

**③ 광고 0개 브랜드도 집계 포함**
Meta 광고가 없는 브랜드도 더미 행으로 추가
→ 광고 집행 여부 자체가 경쟁사 분석 데이터로 활용 가능

**④ 전체/90일/집계 CSV 3종 저장**
원본 데이터 보존 + 분석용 필터 데이터 별도 저장
→ 추후 기간 변경 분석 시 재크롤링 없이 raw CSV 재처리 가능
