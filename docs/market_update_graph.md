# 시장 리서치 자동 업데이트 — LangGraph + Tavily 기술 설계서

> 최종 업데이트: 2026-03-30
> 대상 파일: `market_api/services/update_graph.py`, `tavily_searcher.py`, `section_extractor.py`

---

## 1. 개요

시장 리서치 데이터(시장 규모, K-뷰티 점유율, 트렌드 등)를 자동으로 수집·구조화·저장하는 워크플로우.
Tavily 웹 검색으로 최신 리포트를 수집하고, GPT-4o로 JSON 구조화한 뒤, 운영자가 터미널에서 승인하면 DB에 반영된다.

```
Tavily 검색 → GPT 구조화 → 터미널 diff 검토 → DB 저장
                               ↑         |
                               └─ 재검색 ←┘ (reject 시 루프)
```

---

## 2. 그래프 구조

LangGraph `StateGraph`로 구성된 4-노드 단방향 그래프. `human_review` 이후에만 조건부 분기가 존재한다.

```
[Entry]
  tavily_search
      │
      ▼
  gpt_extract
      │
      ▼
  human_review ──[approved]──▶ save_to_db ──▶ END
      │
      ├──[retry]──▶ tavily_search  (루프)
      │
      └──[exit]──▶ END
```

### 그래프 빌드 코드

```python
graph = StateGraph(UpdateState)
graph.add_node("tavily_search", tavily_search)
graph.add_node("gpt_extract",   gpt_extract)
graph.add_node("human_review",  human_review)
graph.add_node("save_to_db",    save_to_db)

graph.set_entry_point("tavily_search")
graph.add_edge("tavily_search", "gpt_extract")
graph.add_edge("gpt_extract",   "human_review")
graph.add_conditional_edges(
    "human_review",
    route_decision,
    {"save_to_db": "save_to_db", "tavily_search": "tavily_search", "__end__": END},
)
graph.add_edge("save_to_db", END)
```

---

## 3. 상태 스키마 (UpdateState)

```python
class UpdateState(TypedDict):
    section:      str        # "market_size" | "kbeauty_share" | "trends" | "channels" | "competitors"
    country:      str        # "US" | "JP"
    category:     str        # 화장품 카테고리 (예: "스킨케어")
    month:        str        # "YYYY-MM" (기본: 현재 월)
    current_data: dict       # DB에 저장된 현재값 (diff 비교용)
    raw_text:     str        # Tavily 검색 원문 합산
    sources:      list[str]  # Tavily 출처 URL 목록
    new_data:     dict       # GPT 구조화 결과
    decision:     str        # "approved" | "retry" | "exit"
```

노드 간 데이터 흐름은 각 노드가 `dict`를 반환하면 LangGraph가 상태에 병합한다. 노드는 자신이 변경하는 키만 반환하면 된다.

---

## 4. 노드 상세

### Node 1 — `tavily_search`

`tavily_searcher.search_section(section, country)` 호출.

**반환:** `{"raw_text": str, "sources": list[str]}`

#### Tavily 호출 방식

```python
client.search(
    query=query,
    max_results=3,
    search_depth="advanced",
    include_raw_content=(section == "market_size"),  # market_size만 본문 포함
    include_domains=preferred_domains,               # 선택적 도메인 고정
)
```

#### 섹션별 검색 쿼리

| 섹션 | 국가 | 쿼리 전략 |
|------|------|-----------|
| market_size | US | `"United States domestic skincare market size {prev_year} revenue billion USD CAGR forecast NOT global"` |
| market_size | JP | `"Japan domestic skincare cosmetics market size {prev_year} billion yen revenue CAGR forecast NOT global"` + 한국어 쿼리 병행 |
| kbeauty_share | US | `"Korea cosmetics United States import market share ranking {prev_year} statistics percent"` + HS코드 쿼리 |
| kbeauty_share | JP | 한국어 + 관세청/KOTRA 타겟 쿼리 |
| trends | US/JP | KOTRA 리포트 + 영문 소비자 트렌드 리포트 |
| channels | US/JP | K-beauty 유통 채널 온·오프라인 비중 쿼리 |
| competitors | US/JP | 브랜드 시장 점유율 순위 통계 쿼리 |

#### 도메인 고정 (market_size)

```python
MARKET_SIZE_DOMAINS = {
    "US": ["zionmarketresearch.com"],
    "JP": ["menafn.com"],
}
```

market_size는 신뢰 도메인을 우선 검색하고, 결과가 없으면 도메인 제한 없이 재시도한다.

---

### Node 2 — `gpt_extract`

`section_extractor.extract_section(section, country, raw_text, source_url)` 호출.

**반환:** `{"new_data": dict}`

GPT-4o (temperature=0) 사용. 텍스트는 최대 20,000자로 잘라 전달.
추출 후 `new_data["tavily_sources"] = sources` 로 출처 URL 목록을 함께 저장.

#### 섹션별 추출 필드

| 섹션 | 추출 필드 |
|------|-----------|
| market_size | `value`, `cagr`, `year`, `forecast_year`, `forecast_value`, `description`, `source_quote` |
| kbeauty_share | `share`, `rank`, `export_value`, `yoy_growth`, `growth_trend`, `competing_countries`, `description`, `source_quote` |
| trends | `ingredients`, `formulations`, `functions`, `rising_keywords`, `consumer_needs`, `details`, `description`, `source_quote` |
| channels | `channels[]`, `online_ratio`, `key_platform`, `details`, `description`, `source_quote` |
| competitors | `brands[]`, `kbeauty_brands`, `market_leader`, `market_leader_share`, `details`, `description`, `source_quote` |

`source_quote`는 원문 인용구 그대로 저장 (번역 없음).

---

### Node 3 — `human_review` (Human-in-the-Loop)

터미널에 현재값 vs 새 값 diff를 출력하고 운영자 입력을 받는다.

#### diff 표시 예시

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [시장 규모·성장률] US 업데이트 검토
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Tavily 출처:
    1. https://www.zionmarketresearch.com/...

  필드           현재값                    →  새 값
  ─────────────  ─────────────────────────    ─────────────────────────
  value          $18.4B                    →  $25.04B ◀
  cagr           5.2%                      →  6.96% ◀
  year           2023                      →  2024 ◀
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [y] 승인  [r] 재검색  [o] 출처 브라우저 열기  [q] 종료:
```

#### 입력 선택지

| 입력 | 동작 | 다음 노드 |
|------|------|-----------|
| `y` | 승인 | `save_to_db` |
| `r` | 재검색 | `tavily_search` (루프) |
| `o` | 출처 URL 브라우저에서 열기 | 재입력 대기 |
| `q` | 취소 종료 | `END` |

---

### Node 4 — `save_to_db`

`MarketResearch` 테이블에 해당 섹션 필드만 덮어쓴다. 나머지 4개 섹션은 건드리지 않는다.

```python
obj, created = MarketResearch.objects.update_or_create(
    category=category, country=country, research_month=month,
    defaults={},
)
setattr(obj, section, new_data)           # 해당 섹션만 업데이트
obj.sources = list(set(existing + tavily_sources))  # 출처 URL 병합
obj.save()
```

---

## 5. 조건부 라우팅

```python
def route_decision(state) -> str:
    decision = state.get("decision", "exit")
    if decision == "approved": return "save_to_db"
    elif decision == "retry":  return "tavily_search"
    else:                      return "__end__"
```

`retry` 선택 시 `raw_text` / `sources` / `new_data`는 다음 `tavily_search` 실행 결과로 덮어씌워진다.

---

## 6. 공개 인터페이스

```python
from market_api.services.update_graph import run_update

run_update(
    section  = "market_size",   # 업데이트할 섹션
    country  = "US",            # US | JP
    category = "스킨케어",       # 기본값
    month    = "2026-03",       # 기본값: 현재 월
)
```

Django 관리 커맨드에서 호출:

```bash
python manage.py ingest_research --section-crawl
python manage.py ingest_research --section-crawl --country JP
python manage.py ingest_research --section-crawl --force
```

---

## 7. 관련 파일

| 파일 | 역할 |
|------|------|
| `market_api/services/update_graph.py` | LangGraph 그래프 정의, 4개 노드, 라우팅 |
| `market_api/services/tavily_searcher.py` | Tavily API 호출, 섹션별 쿼리 템플릿 |
| `market_api/services/section_extractor.py` | GPT-4o 섹션별 구조화 프롬프트 |
| `market_api/services/section_crawler.py` | 섹션 레이블, URL 매핑 |
| `market_api/management/commands/ingest_research.py` | 관리 커맨드 진입점 |
| `market_api/models.py` | `MarketResearch` 모델 |

---

## 8. 의존성

```
langgraph
langchain-openai   # ChatOpenAI (GPT-4o)
tavily-python      # TavilyClient
```

환경 변수:
- `OPENAI_API_KEY`
- `TAVILY_API_KEY`
