# 리뷰 데이터 업데이트 파이프라인 기술 명세

`market_api/management/commands/update_pipeline.py` + `crawling/pipeline_steps.py`

---

## 개요

채널별(Ulta / Sephora / Qoo10 / Rakuten) Top10 상품 랭킹과 리뷰를 크롤링하여
번역·KeyBERT 키워드 추출·GPT 분류를 거쳐 DB에 적재하고,
신규 리뷰가 있는 상품의 ReviewAnalysisCache를 자동 재계산한다.

```
python manage.py update_pipeline --channel ulta
python manage.py update_pipeline --channel all
```

---

## 기술 플로우

```
[1] Top10 크롤링 (Playwright / requests)
채널별 랭킹 + 신규 리뷰 수집
        ↓
[2] Rankings DB 저장
기존 랭킹 전체 삭제 → 최신 Top10으로 교체
        ↓
신규 리뷰 없음? → 파이프라인 종료
        ↓ (신규 리뷰 있을 때)
[3] 번역 (Google Translate)
US(EN→KO) / JP(JA→EN→KO) 2단계
ThreadPoolExecutor(max_workers=4) 병렬, CHUNK_SIZE=5
        ↓
[4] KeyBERT 키워드 추출
영어 본문 → top 5 키워드 추출
키워드 룰 매칭 → 1차 카테고리 분류
        ↓
[4-b] 신규 키워드 번역 (GPT-4o-mini)
keyword_ko_map.json 미등록 키워드 → GPT 번역 → 파일 갱신
        ↓
[5] GPT 2차 분류 (GPT-4o-mini)
1차 분류에서 '미분류'인 리뷰만 30건 배치 GPT 재분류
v2 세분류 저장 → v1 통합 카테고리 파생
        ↓
[6] Reviews DB 저장
신규 리뷰 upsert, 영향받은 platform_item_id 집합 반환
        ↓
[7] ReviewAnalysisCache 재계산
신규 리뷰가 생긴 상품만 compute_review_analysis() 재실행
GPT 리뷰 요약(2호출) + 시장 기회 생성(1호출)
        ↓
완료
```

---

## 데이터 입출력 파이프라인

**입력**

`python manage.py update_pipeline --channel ulta|sephora|qoo10|rakuten|all`

**파이프라인**

실행 커맨드 → 기존 review_id 집합 로드 → 채널별 크롤러 호출 → Rankings DB 교체 → 신규 리뷰 번역(Google Translate) → KeyBERT 키워드 추출 + 1차 룰 분류 → 신규 키워드 GPT 번역 → GPT 2차 분류(미분류만) → Reviews DB upsert → 영향받은 상품 ReviewAnalysisCache 재계산(GPT 3호출) → 완료

**출력**

- `ProductRanking` DB: 채널별 Top10 갱신
- `ProductReview` DB: 신규 리뷰 적재 (번역·키워드·카테고리 포함)
- `ReviewAnalysisCache` DB: 신규 리뷰 상품의 분석 결과 갱신

---

## 채널별 처리 차이

| 채널 | 언어 | 번역 경로 | review_id 중단 조건 |
|------|------|-----------|---------------------|
| Ulta | EN | EN→KO | known review_id 만나면 중단 |
| Sephora | EN | EN→KO | known review_id 만나면 중단 |
| Qoo10 | JA | JA→EN→KO | 전체 재수집 후 DB upsert |
| Rakuten | JA | JA→EN→KO | known (shop_id, item_id) 기준 최신 날짜 비교 |

---

## LLM 활용 지점

### [4-b] 신규 키워드 번역 (`translate_new_keywords`)

KeyBERT가 추출한 영어 키워드 중 `keyword_ko_map.json`에 없는 것을 번역.
빈도 상위 30개만 대상으로 한정 (대시보드 top8 표시 커버용).

| 항목 | 내용 |
|------|------|
| 모델 | GPT-4o-mini |
| temperature | 0 |
| response_format | json_object (강제) |
| 배치 크기 | 80개 |

**System 프롬프트**:
```
You are a cosmetics/beauty product review keyword translator.
Translate English keywords to natural Korean.
Return ONLY a JSON object: {"original": "번역"}.
Keep brand/product names as-is. Use common Korean cosmetics terminology.
```

**User 프롬프트**:
```
Translate these keywords:
["moisturizing", "spf 50", "ceramide", ...]
```

**출력**:
```json
{"moisturizing": "보습", "spf 50": "자외선차단 50", "ceramide": "세라마이드"}
```

---

### [5] GPT 2차 분류 (`classify_reviews`)

KeyBERT 1차 분류에서 `미분류`로 남은 리뷰를 30건 배치로 GPT 재분류.
→ `review_analysis_llm.md` 1번 호출 항목 참조

---

### [7] ReviewAnalysisCache 재계산 (`compute_review_analysis`)

신규 리뷰가 생긴 상품에 대해 GPT 3호출 실행:
- 긍정 리뷰 요약 (GPT-4o-mini)
- 부정 리뷰 요약 (GPT-4o-mini)
- 시장 기회 3가지 생성 (GPT-4o-mini)
→ `review_analysis_llm.md` 2번·3번 호출 항목 참조

---

## 설계 의도

**① 증분 업데이트**
기존 review_id 집합을 사전 로드 후 크롤링 시 중복 판단
→ 이미 수집된 리뷰는 건너뛰고 신규만 처리해 비용·시간 절감

**② 미분류만 GPT 호출**
KeyBERT 룰 기반 분류 성공 시 GPT 호출 없음
→ GPT 호출 비용 최소화 (분류 가능한 것은 코드로 처리)

**③ 영향받은 상품만 재계산**
신규 리뷰가 없는 상품은 ReviewAnalysisCache 건드리지 않음
→ 불필요한 GPT 호출 방지, 변경 없는 분석 결과 보존
