"""
LangGraph 기반 섹션 업데이트 워크플로우.

Tavily 검색 → GPT 구조화 → 터미널 diff 확인 → 승인/재검색/종료 → DB 저장.

run_update(section, country, category, month) 로 실행.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import TypedDict, Literal

from langgraph.graph import StateGraph, END

from market_api.services.tavily_searcher import search_section
from market_api.services.section_extractor import extract_section
from market_api.services.section_crawler import SECTION_LABELS


# ── State 정의 ───────────────────────────────────────────────────────────────

class UpdateState(TypedDict):
    section: str            # "market_size"
    country: str            # "US"
    category: str           # "스킨케어"
    month: str              # "2026-03"
    current_data: dict      # DB 현재값
    raw_text: str           # Tavily 검색 결과 원문
    sources: list[str]      # Tavily 출처 URL들
    new_data: dict          # GPT 구조화 새 값
    decision: str           # "approved" / "retry" / "exit"


# ── Node 1: Tavily 검색 ─────────────────────────────────────────────────────

def tavily_search(state: UpdateState) -> dict:
    section = state["section"]
    country = state["country"]
    label = SECTION_LABELS.get(section, section)

    print(f"\n🔍 [{label}] {country} Tavily 검색 중...")

    raw_text, sources = search_section(section, country)

    if not raw_text:
        print("   ⚠️  검색 결과 없음")
    else:
        print(f"   ✅ {len(sources)}개 출처에서 {len(raw_text):,}자 수집")
        for i, url in enumerate(sources, 1):
            print(f"      {i}. {url}")

    return {"raw_text": raw_text, "sources": sources}


# ── Node 2: GPT 구조화 ──────────────────────────────────────────────────────

def gpt_extract(state: UpdateState) -> dict:
    section = state["section"]
    country = state["country"]
    raw_text = state["raw_text"]
    sources = state["sources"]

    if not raw_text:
        print("   ⚠️  원문 없음 — GPT 추출 건너뜀")
        return {"new_data": {}}

    label = SECTION_LABELS.get(section, section)
    print(f"\n🤖 [{label}] {country} GPT 구조화 중...")

    # 메인 출처 URL (첫 번째)
    source_url = sources[0] if sources else ""

    new_data = extract_section(section, country, raw_text, source_url)
    # Tavily 전체 출처 URL 저장
    new_data["tavily_sources"] = sources

    print("   ✅ 구조화 완료")
    # GPT 추출 결과 주요 필드 출력
    keys = ["value", "growth_rate", "cagr", "year", "share", "yoy_growth", "export_value"]
    for k in keys:
        if k in new_data:
            print(f"      {k}: {new_data[k]!r}")

    return {"new_data": new_data}


# ── Node 3: 터미널 diff + 승인 ──────────────────────────────────────────────

# diff에 표시할 주요 필드 (섹션별)
_DIFF_KEYS: dict[str, list[str]] = {
    "market_size":   ["value", "growth_rate", "cagr", "year", "forecast_year", "forecast_value"],
    "kbeauty_share": ["share", "rank", "export_value", "yoy_growth"],
    "trends":        ["ingredients", "formulations", "functions", "rising_keywords"],
    "channels":      ["channels", "key_platform", "online_ratio"],
    "competitors":   ["market_leader", "market_leader_share", "kbeauty_brands"],
}


def _format_value(val) -> str:
    """값을 터미널 출력용 문자열로 변환."""
    if isinstance(val, list):
        if not val:
            return "[]"
        # 리스트 항목이 dict이면 name만 추출
        items = []
        for v in val:
            if isinstance(v, dict):
                items.append(v.get("name", str(v)))
            else:
                items.append(str(v))
        return ", ".join(items)
    if val == "" or val is None:
        return "(없음)"
    return str(val)


def human_review(state: UpdateState) -> dict:
    section = state["section"]
    country = state["country"]
    current = state["current_data"]
    new = state["new_data"]
    sources = state["sources"]
    label = SECTION_LABELS.get(section, section)

    if not new:
        print("\n   ⚠️  새 데이터가 없습니다.")
        return {"decision": "retry"}

    # ── diff 출력 ──
    sep = "━" * 55
    print(f"\n{sep}")
    print(f"  [{label}] {country} 업데이트 검토")
    print(sep)

    # 출처
    if sources:
        print("  Tavily 출처:")
        for i, url in enumerate(sources, 1):
            print(f"    {i}. {url}")
        print()

    # 필드별 비교
    keys = _DIFF_KEYS.get(section, list(new.keys()))
    max_key_len = max((len(k) for k in keys), default=10)

    print(f"  {'필드':<{max_key_len}}   {'현재값':<25}  →  새 값")
    print(f"  {'─' * max_key_len}   {'─' * 25}     {'─' * 25}")

    for key in keys:
        cur_val = _format_value(current.get(key))
        new_val = _format_value(new.get(key))
        changed = " ◀" if cur_val != new_val else ""
        print(f"  {key:<{max_key_len}}   {cur_val:<25}  →  {new_val}{changed}")

    # description
    desc = new.get("description", "")
    if desc:
        print(f"\n  description (새):")
        print(f"    {desc}")

    # source_quote
    quote = new.get("source_quote", "")
    if quote:
        print(f"\n  source_quote:")
        print(f"    {quote[:200]}{'...' if len(quote) > 200 else ''}")

    print(sep)

    # ── 승인 입력 ──
    while True:
        choice = input("  [y] 승인  [r] 재검색  [o] 출처 브라우저 열기  [q] 종료: ").strip().lower()
        if choice == "o":
            import webbrowser
            for url in sources:
                webbrowser.open(url)
            print(f"  🌐 {len(sources)}개 출처를 브라우저에서 열었습니다.")
            continue
        if choice in ("y", "r", "q"):
            break
        print("  → y / r / o / q 중 하나를 입력하세요.")

    decision_map = {"y": "approved", "r": "retry", "q": "exit"}
    decision = decision_map[choice]

    if decision == "approved":
        print("  ✅ 승인됨 — DB 업데이트 진행")
    elif decision == "retry":
        print("  🔄 재검색 진행")
    else:
        print("  ❌ 종료 — 업데이트 취소")

    return {"decision": decision}


# ── Node 4: DB 저장 ──────────────────────────────────────────────────────────

def save_to_db(state: UpdateState) -> dict:
    from market_api.models import MarketResearch

    section = state["section"]
    country = state["country"]
    category = state["category"]
    month = state["month"]
    new_data = state["new_data"]
    label = SECTION_LABELS.get(section, section)

    print(f"\n💾 [{label}] {country} DB 저장 중...")

    obj, created = MarketResearch.objects.update_or_create(
        category=category,
        country=country,
        research_month=month,
        defaults={},
    )

    # 해당 섹션 필드만 업데이트 (나머지 4개 유지)
    setattr(obj, section, new_data)

    # sources 필드에 tavily_sources 추가
    existing_sources = obj.sources or []
    tavily_sources = new_data.get("tavily_sources", [])
    merged_sources = list(set(existing_sources + tavily_sources))
    obj.sources = merged_sources

    obj.save()

    action = "신규 생성" if created else "업데이트"
    print(f"   ✅ DB {action} 완료: {category}-{country} ({month}) [{label}]")

    return {}


# ── 조건부 라우팅 ────────────────────────────────────────────────────────────

def route_decision(state: UpdateState) -> Literal["save_to_db", "tavily_search", "__end__"]:
    decision = state.get("decision", "exit")
    if decision == "approved":
        return "save_to_db"
    elif decision == "retry":
        print("  🔄 Tavily 재검색 시작...")
        return "tavily_search"
    else:
        return "__end__"


# ── 그래프 빌드 ──────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(UpdateState)

    graph.add_node("tavily_search", tavily_search)
    graph.add_node("gpt_extract", gpt_extract)
    graph.add_node("human_review", human_review)
    graph.add_node("save_to_db", save_to_db)

    graph.set_entry_point("tavily_search")
    graph.add_edge("tavily_search", "gpt_extract")
    graph.add_edge("gpt_extract", "human_review")
    graph.add_conditional_edges(
        "human_review",
        route_decision,
        {
            "save_to_db": "save_to_db",
            "tavily_search": "tavily_search",
            "__end__": END,
        },
    )
    graph.add_edge("save_to_db", END)

    return graph.compile()


# ── 공개 인터페이스 ──────────────────────────────────────────────────────────

def run_update(
    section: str,
    country: str,
    category: str = "스킨케어",
    month: str | None = None,
) -> None:
    """
    단일 섹션의 Tavily 업데이트 워크플로우 실행.

    Args:
        section: market_size / kbeauty_share / trends / channels / competitors
        country: US / JP
        category: 화장품 카테고리
        month: 조사 월 (기본: 현재 월)
    """
    from market_api.models import MarketResearch

    if not month:
        month = datetime.now().strftime("%Y-%m")

    label = SECTION_LABELS.get(section, section)
    print(f"\n{'═' * 55}")
    print(f"  섹션 업데이트: [{label}] {country} ({category}, {month})")
    print(f"{'═' * 55}")

    # 현재 DB 데이터 로드
    current_data = {}
    try:
        obj = MarketResearch.objects.get(
            category=category,
            country=country,
            research_month=month,
        )
        current_data = getattr(obj, section, {}) or {}
    except MarketResearch.DoesNotExist:
        print("  ℹ️  기존 데이터 없음 (신규 생성)")

    # LangGraph 실행
    app = build_graph()
    app.invoke({
        "section": section,
        "country": country,
        "category": category,
        "month": month,
        "current_data": current_data,
        "raw_text": "",
        "sources": [],
        "new_data": {},
        "decision": "",
    })
