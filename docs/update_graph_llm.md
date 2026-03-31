# 시장 데이터 업데이트 워크플로우 — LangGraph 활용

`market_api/services/update_graph.py`

---

## 개요

시장 조사 데이터(시장 규모, K-뷰티 점유율, 트렌드, 유통 채널, 경쟁사)를
최신 정보로 갱신할 때 사용하는 LangGraph 기반 Human-in-the-Loop 파이프라인이다.

관리자가 검색 결과를 직접 검토하고 승인한 데이터만 DB에 저장되도록 설계했다.

---

## 기술 플로우

```
python manage.py update_section market_size --country US
        ↓
DB에서 현재 섹션 데이터 로드 (diff 비교용)
        ↓
LangGraph 실행 시작
        ↓
[Node 1] tavily_search
Tavily API 웹 검색 → 원문 + 출처 URL 수집
        ↓
[Node 2] gpt_extract
section_extractor.extract_section() 호출
→ GPT-4o로 원문 구조화 JSON 추출
        ↓
[Node 3] human_review
터미널에 기존값 / 새값 diff 출력
→ 관리자 입력 대기 (y / r / q)
        ↓
[조건부 라우팅]
y (승인) → [Node 4] save_to_db → END
r (재검색) → [Node 1] tavily_search (루프)
q (종료) → END
```

---

## LangGraph 그래프 구조

**노드 구성**

| 노드 | 역할 |
|------|------|
| `tavily_search` | Tavily API로 최신 시장 데이터 웹 검색 |
| `gpt_extract` | GPT-4o로 검색 원문을 구조화된 JSON으로 추출 |
| `human_review` | 터미널에 기존값/새값 diff 출력 → 관리자 승인 대기 |
| `save_to_db` | 승인된 데이터를 MarketResearch DB에 저장 |

**엣지 구성**

```
tavily_search → gpt_extract → human_review
                                    │
               ┌────────────────────┤
               │                    │                    │
           [y] 승인             [r] 재검색            [q] 종료
               ↓                    ↓                    ↓
          save_to_db          tavily_search             END
               ↓
              END
```

조건부 라우팅(`add_conditional_edges`)으로 human_review의 결정에 따라
재검색 루프, DB 저장, 종료 세 가지 경로로 분기한다.

---

## 데이터 입출력 파이프라인

**입력**

`python manage.py update_section market_size --country US`

**파이프라인**

실행 커맨드 → DB에서 현재 데이터 로드 → LangGraph 시작 → Tavily 웹 검색 → 원문 수집 → GPT-4o 구조화 추출 → 터미널 diff 출력 → 관리자 승인/재검색/종료 → (승인 시) DB 저장

**출력**

MarketResearch DB의 해당 섹션 필드 업데이트

---

## State 구조

LangGraph의 각 노드는 `UpdateState`를 공유 상태로 사용한다.

```python
class UpdateState(TypedDict):
    section: str        # 업데이트할 섹션 (market_size 등)
    country: str        # 국가 코드 (US / JP)
    category: str       # 화장품 카테고리
    month: str          # 조사 월
    current_data: dict  # DB 현재값 (diff 비교용)
    raw_text: str       # Tavily 검색 결과 원문
    sources: list[str]  # Tavily 출처 URL들
    new_data: dict      # GPT 구조화 결과
    decision: str       # "approved" / "retry" / "exit"
```

---

## 설계 의도

**① Human-in-the-Loop**
GPT 추출 결과를 자동 저장하지 않고 관리자가 기존값과 새값의 diff를 확인 후
승인/재검색/종료를 선택 → LLM 오류가 DB에 반영되는 것을 방지

**② 재검색 루프**
승인 거부 시 `tavily_search` 노드로 되돌아가 재검색 후 재추출
→ 동일 워크플로우 내에서 반복 실행 가능

**③ 섹션 단위 업데이트**
5개 섹션 중 하나만 선택해 업데이트 가능
→ 나머지 4개 섹션 데이터는 그대로 유지
