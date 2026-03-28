# LLM 추출기 검증 정리

## 1. 초기 세팅 검증 — 시장 데이터 추출기

### 검증 대상
`section_extractor.py` — 크롤링된 원문에서 시장 데이터를 구조화된 JSON으로 추출하는 LLM

### 검증 방식
- `section_crawler.py`의 고정 URL로 원문 크롤링 (US/JP 각 섹션별)
- 동일 원문에 temperature=0.8로 30회 반복 추출
- 필드별 일관성 분석: 빈값을 제외하고 **값이 들어왔을 때 동일한 값이 나오는 비율**로 측정
- AI(gpt-5.4)가 accuracy / consistency / hallucination_free / overall 4개 지표를 5점 만점으로 채점

### 결과

| 섹션 | 국가 | overall | accuracy | consistency | hall_free |
|------|------|---------|----------|-------------|-----------|
| market_size | US | 4.90 | 4.90 | 4.90 | 5.00 |
| market_size | JP | 4.90 | 4.90 | 4.80 | 4.90 |
| kbeauty_share | US | 5.00 | 5.00 | 5.00 | 4.90 |
| kbeauty_share | JP | 4.80 | 4.80 | 4.60 | 4.90 |
| trends | US | 4.50 | 4.40 | 4.60 | 4.70 |
| trends | JP | 3.20 | 3.70 | 2.80 | 3.10 |
| channels | US | 5.00 | 5.00 | 5.00 | 5.00 |
| channels | JP | 4.10 | 4.00 | 4.40 | 3.80 |
| competitors | US | 5.00 | 4.90 | 5.00 | 5.00 |
| competitors | JP | 4.90 | 4.80 | 5.00 | 5.00 |

### 결론
- **수치 추출 필드(market_size, kbeauty_share)는 4.8~5.0으로 신뢰도 높음** → 핵심 목적 달성
- trends JP가 3.2로 낮은 이유: 리스트형 필드 특성상 원문에 후보가 많아 temperature=0.8에서 매번 다른 조합이 선택됨. 단, production은 temperature=0이므로 실제 운영에서는 문제 없음
- trends JP 소스 URL(sourceready.com)은 영어 마케팅 보고서로, 동의어 표현이 다양해 변동폭이 큰 것도 원인

---

## 2. 업데이트 검증 — Tavily 기반 갱신

### 검증 방식
자동화 검증 불가 (매번 다른 URL, 다른 원문) → **사람이 직접 검토**

`update_graph.py`의 human_review 단계에서:
- 기존값 vs 새값 diff 터미널 출력
- source_quote로 원문 발췌 확인
- `o` 입력 시 출처 URL 브라우저 직접 열기
- `y` 승인 / `r` 재검색 / `q` 취소

### 결론
Tavily 업데이트는 이미 human_review가 내장된 구조로, 이것이 검증 역할을 함

---

## 3. 광고 문구 생성 검증

### 검증 대상
`ad_strategy.py` — Meta 광고 데이터 + 시장 트렌드를 기반으로 광고 카피 생성

### 검증 방식
고정 샘플 제품으로 N회 반복 실행 후 3가지 지표 측정:

| 지표 | 설명 |
|------|------|
| format | JSON 필드 누락 없이 정상 반환되는 비율 |
| language | US→영어, JP→일본어로 올바르게 생성되는 비율 |
| relevance | 제품 성분·효능이 카피에 실제로 반영된 정도 (AI 5점 채점) |

추가로 핵심 메시지 빈출 키워드 분석으로 어떤 소구점이 일관되게 나오는지 확인

### 결론
- format/language는 100% 기대 (구조적 문제)
- relevance는 4.0 이상이면 양호
- 창작물 특성상 매번 다른 카피가 나오는 건 정상 동작
