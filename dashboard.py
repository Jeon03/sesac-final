import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import re

st.set_page_config(
    page_title="Global Beauty Insight",
    page_icon="G",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* 배경 · 레이아웃 */
[data-testid="stAppViewContainer"], [data-testid="stMain"] { background: var(--secondary-background-color) !important; }
[data-testid="stHeader"] { background: transparent !important; }
.main .block-container { padding-top: 0.5rem; padding-bottom: 2rem; max-width: 1280px; }

/* 섹션 제목 */
.section-header { font-size: 16px; font-weight: 700; color: var(--text-color); padding-left: 12px; border-left: 4px solid #1d4ed8; margin-bottom: 16px; }

/* KPI 카드 */
.kpi-card { background: var(--background-color); border: 1px solid rgba(128,128,128,0.2); border-radius: 14px; padding: 20px 22px; box-shadow: 0 1px 4px rgba(0,0,0,.06); }
.kpi-label { font-size: 12px; color: #9ca3af; font-weight: 600; margin-bottom: 8px; }
.kpi-value { font-size: 28px; font-weight: 700; color: var(--text-color); line-height: 1.2; }
.kpi-sub { font-size: 12px; color: #9ca3af; margin-top: 4px; }
.kpi-delta-pos { font-size: 12px; color: #10b981; font-weight: 600; margin-top: 4px; }
.kpi-channel { font-size: 24px; font-weight: 700; color: #0ea5e9; }

/* 태그 */
.tag-us { display: inline-block; background: rgba(29,78,216,0.12); color: #3b82f6; border-radius: 6px; padding: 3px 10px; font-size: 12px; font-weight: 600; margin: 3px 3px 3px 0; }
.tag-jp { display: inline-block; background: rgba(219,39,119,0.12); color: #ec4899; border-radius: 6px; padding: 3px 10px; font-size: 12px; font-weight: 600; margin: 3px 3px 3px 0; }
.tag-label { font-size: 10px; font-weight: 700; letter-spacing: 0.1em; color: #9ca3af; margin-top: 10px; margin-bottom: 4px; }

/* 순위 리스트 */
.rank-row { display: flex; align-items: flex-start; padding: 10px 0; border-bottom: 1px solid rgba(128,128,128,0.15); }
.rank-num { font-size: 18px; font-weight: 700; color: rgba(156,163,175,0.8); width: 28px; flex-shrink: 0; margin-right: 12px; line-height: 1.4; }
.rank-num.top { color: #1d4ed8; }
.rank-name { font-size: 14px; font-weight: 600; color: var(--text-color); }
.rank-desc { font-size: 12px; color: #9ca3af; margin-top: 2px; }

/* Top5 테이블 */
.top5-wrap { border-radius: 12px; overflow: hidden; }
.top5-table { width: 100%; border-collapse: collapse; }
.top5-table th { font-size: 10px; font-weight: 700; letter-spacing: .08em; color: #9ca3af; padding: 8px 12px; text-align: left; border-bottom: 1px solid rgba(128,128,128,0.15); background: var(--background-color); }
.top5-table td { padding: 9px 12px; font-size: 13px; color: var(--text-color); border-bottom: 1px solid rgba(128,128,128,0.1); vertical-align: middle; background: var(--background-color); }
.top5-name { font-weight: 600; }
.top5-brand { color: #9ca3af; font-size: 12px; }

/* 리뷰 분석 패널 헤더 */
.panel-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }
.panel-title { font-size: 20px; font-weight: 700; color: var(--text-color); }
.panel-platform { font-size: 14px; font-weight: 600; color: #3b82f6; }
.panel-sub { font-size: 12px; color: #9ca3af; margin-top: 2px; }
.panel-label { font-size: 12px; font-weight: 700; color: #9ca3af; letter-spacing: .05em; margin-bottom: 8px; }
.rating-badge { background: rgba(59,130,246,0.1); border-radius: 12px; padding: 10px 18px; text-align: center; flex-shrink: 0; margin-left: 16px; }
.rating-badge-label { font-size: 11px; color: #9ca3af; font-weight: 600; }
.rating-badge-value { font-size: 30px; font-weight: 800; color: #1d4ed8; }
.rating-badge-denom { font-size: 14px; color: #9ca3af; }

/* 카테고리 바 */
.score-bar-wrap { margin-bottom: 8px; }
.score-bar-label { font-size: 13px; color: var(--text-color); margin-bottom: 3px; display: flex; justify-content: space-between; }
.score-bar-bg { background: rgba(128,128,128,0.2); border-radius: 6px; height: 8px; }
.score-bar-fill { background: #3b82f6; border-radius: 6px; height: 8px; }

/* 키워드 태그 */
.kw-tag { display: inline-block; background: rgba(29,78,216,0.12); color: #3b82f6; border-radius: 20px; padding: 4px 12px; font-size: 12px; font-weight: 600; margin: 3px 4px 3px 0; }
.kw-tag-gray { display: inline-block; background: rgba(107,114,128,0.12); color: #9ca3af; border-radius: 20px; padding: 4px 12px; font-size: 12px; font-weight: 600; margin: 3px 4px 3px 0; }

/* 리뷰 요약 박스 */
.review-label { font-size: 12px; font-weight: 700; margin-bottom: 6px; }
.review-label.pos { color: #10b981; }
.review-label.neg { color: #ef4444; }
.review-box { background: rgba(128,128,128,0.08); border-radius: 10px; padding: 14px 16px; font-size: 13px; color: var(--text-color); line-height: 1.6; border-left: 3px solid rgba(128,128,128,0.3); }
.review-box.pos { border-left-color: #10b981; background: rgba(16,185,129,0.08); }
.review-box.neg { border-left-color: #ef4444; background: rgba(239,68,68,0.08); }

/* 불만사항 · 시장기회 */
.section-title-red   { font-size: 13px; font-weight: 700; color: #ef4444; margin-bottom: 8px; }
.section-title-green { font-size: 13px; font-weight: 700; color: #10b981; margin-bottom: 8px; }
.complaint-bar-wrap { margin-bottom: 6px; display: flex; align-items: center; gap: 10px; }
.complaint-label { font-size: 13px; color: var(--text-color); width: 120px; flex-shrink: 0; }
.complaint-bar-bg { flex: 1; background: rgba(239,68,68,0.15); border-radius: 6px; height: 8px; }
.complaint-bar-fill { background: #ef4444; border-radius: 6px; height: 8px; }
.complaint-pct { font-size: 12px; color: #ef4444; font-weight: 700; width: 36px; text-align: right; }
.opp-item { font-size: 12px; color: var(--text-color); margin-bottom: 6px; }

/* Meta 광고 카드 */
.meta-card { background: var(--background-color); border: 1px solid rgba(128,128,128,0.2); border-radius: 14px; padding: 18px 20px; box-shadow: 0 1px 4px rgba(0,0,0,.06); }
.meta-brand { font-size: 15px; font-weight: 700; color: var(--text-color); margin-bottom: 2px; }
.meta-channel { font-size: 11px; font-weight: 600; color: #9ca3af; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 12px; }
.meta-count-label { font-size: 11px; color: #9ca3af; font-weight: 600; margin-bottom: 4px; }
.meta-count-value { font-size: 24px; font-weight: 700; color: var(--text-color); margin-bottom: 8px; }
.meta-bar-wrap { display: flex; height: 6px; border-radius: 4px; overflow: hidden; margin-bottom: 6px; background: rgba(128,128,128,0.15); }
.meta-bar-image { background: #3b82f6; }
.meta-bar-video { background: #8b5cf6; }
.meta-ratio-row { display: flex; justify-content: space-between; font-size: 11px; color: #9ca3af; margin-bottom: 12px; }
.meta-ratio-image { color: #3b82f6; font-weight: 600; }
.meta-ratio-video { color: #8b5cf6; font-weight: 600; }
.meta-copy-label { font-size: 11px; font-weight: 700; color: #9ca3af; letter-spacing: .05em; margin-bottom: 4px; }
.meta-copy-text { font-size: 12px; color: var(--text-color); line-height: 1.5; font-style: italic; background: rgba(128,128,128,0.06); border-radius: 8px; padding: 8px 10px; border-left: 3px solid rgba(59,130,246,0.4); }
.meta-updated { font-size: 10px; color: #9ca3af; margin-top: 10px; text-align: right; }

/* AI 마케팅 전략 제안 섹션 */
.ad-strategy-wrap { background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 60%, #3b82f6 100%); border-radius: 18px; padding: 32px 36px; color: #fff; position: relative; overflow: hidden; }
.ad-strategy-wrap::before { content: ''; position: absolute; top: -60px; right: -60px; width: 200px; height: 200px; background: rgba(255,255,255,0.05); border-radius: 50%; }
.ad-strategy-badge { display: inline-block; background: rgba(255,255,255,0.15); border-radius: 20px; padding: 4px 14px; font-size: 12px; font-weight: 600; color: rgba(255,255,255,0.9); margin-bottom: 14px; backdrop-filter: blur(4px); }
.ad-strategy-title { font-size: 22px; font-weight: 800; color: #fff; margin-bottom: 20px; }
.ad-strategy-label { font-size: 11px; font-weight: 700; letter-spacing: .06em; color: rgba(255,255,255,0.6); margin-bottom: 6px; }
.ad-strategy-concept { font-size: 18px; font-weight: 700; color: #fff; margin-bottom: 6px; line-height: 1.4; }
.ad-strategy-reasoning { font-size: 13px; color: rgba(255,255,255,0.8); line-height: 1.6; margin-bottom: 16px; }
.ad-strategy-msg { font-size: 13px; color: rgba(255,255,255,0.9); line-height: 1.5; margin-bottom: 6px; padding-left: 12px; border-left: 2px solid rgba(255,255,255,0.3); }
.ad-copy-box { background: rgba(255,255,255,0.1); border-radius: 12px; padding: 20px 22px; backdrop-filter: blur(4px); }
.ad-copy-field-label { font-size: 11px; font-weight: 700; color: rgba(255,255,255,0.5); letter-spacing: .05em; margin-bottom: 4px; margin-top: 14px; }
.ad-copy-field-label:first-child { margin-top: 0; }
.ad-copy-headline { font-size: 16px; font-weight: 700; color: #fff; line-height: 1.4; }
.ad-copy-body { font-size: 13px; color: rgba(255,255,255,0.85); line-height: 1.6; }
.ad-insight-box { background: rgba(255,255,255,0.08); border-radius: 12px; padding: 16px 18px; margin-top: 16px; }
.ad-insight-label { font-size: 12px; font-weight: 700; color: rgba(255,255,255,0.5); margin-bottom: 6px; }
.ad-insight-text { font-size: 13px; color: rgba(255,255,255,0.85); line-height: 1.7; }

/* st.container(border=True) 통일 */
[data-testid="stVerticalBlockBorderWrapper"] > div:first-child {
    background: var(--background-color) !important;
    border-radius: 14px !important;
    border-color: rgba(128,128,128,0.2) !important;
    box-shadow: 0 1px 4px rgba(0,0,0,.06) !important;
}

/* ─── Top10 순위 리스트 버튼 (탭 내부 버튼만 적용) ─────────────────── */
[data-testid="stTabs"] [data-testid="stButton"] > button {
    text-align: left !important;
    border-radius: 10px !important;
    padding: 10px 16px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    border: 1px solid rgba(128,128,128,0.2) !important;
    background: var(--background-color) !important;
    color: var(--text-color) !important;
    box-shadow: none !important;
    transition: border-color 0.15s, background 0.15s !important;
    line-height: 1.5 !important;
}
[data-testid="stTabs"] [data-testid="stButton"] > button:hover {
    border-color: rgba(239,68,68,0.45) !important;
    background: rgba(239,68,68,0.04) !important;
    color: var(--text-color) !important;
}
[data-testid="stTabs"] [data-testid="stButton"] > button[kind="primary"] {
    background: #ef4444 !important;
    color: #fff !important;
    border-color: #ef4444 !important;
    font-weight: 700 !important;
    box-shadow: 0 2px 8px rgba(239,68,68,0.25) !important;
}
[data-testid="stTabs"] [data-testid="stButton"] > button[kind="primary"]:hover {
    background: #dc2626 !important;
    border-color: #dc2626 !important;
}
/* 버튼 사이 간격 줄이기 */
[data-testid="stTabs"] [data-testid="stButton"] {
    margin-bottom: -4px !important;
}
</style>
""", unsafe_allow_html=True)

API_BASE = "http://127.0.0.1:8000/api"

CATEGORY_LIST = ["스킨케어"]

# ── 사이드바 ─────────────────────────────────────────────────────────────────

# ── 제품 정보 입력 폼 ─────────────────────────────────────────────────────────
st.markdown('<div class="section-header">제품 정보 입력</div>', unsafe_allow_html=True)

with st.container():
    c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 1.5])
    with c1:
        selected_category = st.selectbox("카테고리", CATEGORY_LIST, label_visibility="visible")
    with c2:
        product_name = st.text_input("제품명", placeholder="제품명을 입력하세요")
    with c3:
        ingredients = st.text_input("주요 성분", placeholder="병풀 추출물, 판테놀 등")
    with c4:
        effects = st.text_input("핵심 효능", placeholder="장벽 강화, 진정")
    with c5:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        submit_btn = st.button("분석 시작하기", type="primary", use_container_width=True)

st.markdown("---")

# ── 헬퍼 ─────────────────────────────────────────────────────────────────────
COUNTRY_KO = {"US": "미국 (USA)", "JP": "일본 (Japan)"}
COUNTRY_SHORT = {"US": "미국", "JP": "일본"}
OTHER = {"US": "JP", "JP": "US"}


def _parse_channel_list(ch_list):
    result = []
    for item in ch_list:
        if isinstance(item, dict) and item.get("name"):
            result.append({"name": item["name"], "description": item.get("description", "")})
        elif isinstance(item, str) and item:
            result.append({"name": item, "description": ""})
    return result


def _tags_html(items: list, cls: str) -> str:
    """아이템 리스트를 태그 뱃지 HTML로 변환"""
    if not items:
        return ""
    return " ".join(f'<span class="{cls}">{item}</span>' for item in items)


def _score_to_label(score: float, labels=("낮음", "보통", "높음"), thresholds=(40, 60)):
    """점수(0~100) → 정성 라벨 + 색상 (색상은 낮음/중간/높음 순서로 고정)"""
    palette = ("#ef4444", "#f59e0b", "#10b981")  # 낮음, 보통, 높음
    if score >= thresholds[1]:
        idx = 2
    elif score >= thresholds[0]:
        idx = 1
    else:
        idx = 0
    return labels[idx], palette[idx]


def render_country_recommendation(result: dict):
    """AI 최적 진출 국가 추천 섹션 (목업 레이아웃)"""
    if not result or "error" in result:
        st.warning(result.get("error", "추천 결과를 생성할 수 없습니다."))
        return

    top       = result.get("top_country", {})
    rationale = result.get("rationale", "")
    countries = result.get("recommended_countries", [])
    if not top:
        return

    top_country  = top["country"]
    country_name = {"US": "미국 (USA)", "JP": "일본 (Japan)"}.get(top_country, top_country)
    score        = top["score"]
    detail       = top.get("score_detail", {})
    score_color  = "#10b981" if score >= 60 else "#f59e0b" if score >= 40 else "#ef4444"

    # 정성 라벨
    trend_label,  trend_color  = _score_to_label(detail.get("trend",  0))
    market_label, market_color = _score_to_label(detail.get("market", 0))
    review_label, review_color = _score_to_label(
        detail.get("review", 0),
        labels=("부정적", "중립", "긍정적"),
    )

    col_left, col_right = st.columns([3, 2])

    with col_left:
        with st.container(border=True):
            # 헤더: 국가명 + AI Score
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px">
                <div>
                    <div style="font-size:11px;font-weight:700;color:#9ca3af;letter-spacing:.06em;margin-bottom:6px">
                        최적 시장 추천
                    </div>
                    <div style="font-size:26px;font-weight:800;color:var(--text-color);line-height:1.2">
                        {country_name}
                    </div>
                </div>
                <div style="text-align:right">
                    <div style="font-size:42px;font-weight:800;color:{score_color};line-height:1">
                        {score}
                    </div>
                    <div style="font-size:11px;color:#9ca3af;font-weight:600">/100 &nbsp;AI SCORE</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # 선정 근거 (한 줄 요약)
            if rationale:
                short = rationale.split(".")[0] + "." if "." in rationale else rationale[:80]
                st.markdown(
                    f'<div style="font-size:13px;color:#6b7280;margin-bottom:16px;line-height:1.5">{short}</div>',
                    unsafe_allow_html=True,
                )

            # KPI 3개 카드
            k1, k2, k3 = st.columns(3)
            for col, label, val, color, title in [
                (k1, trend_label,  detail.get("trend",  0), trend_color,  "성분 적합도"),
                (k2, market_label, detail.get("market", 0), market_color, "시장 성장성"),
                (k3, review_label, detail.get("review", 0), review_color, "소비자 반응"),
            ]:
                with col:
                    st.markdown(f"""
                    <div style="background:rgba(128,128,128,0.06);border-radius:10px;padding:12px 14px;text-align:center">
                        <div style="font-size:10px;color:#9ca3af;font-weight:700;margin-bottom:6px">{title}</div>
                        <div style="font-size:16px;font-weight:800;color:{color}">{label}</div>
                        <div style="font-size:10px;color:#9ca3af;margin-top:2px">{val:.0f}점</div>
                    </div>
                    """, unsafe_allow_html=True)

            # 트렌드 매칭 키워드
            matched = top.get("trend_matched", [])
            if matched:
                tag_cls = "tag-us" if top_country == "US" else "tag-jp"
                tags = " ".join(f'<span class="{tag_cls}">{k}</span>' for k in matched)
                st.markdown(
                    f'<div class="tag-label" style="margin-top:14px">트렌드 매칭</div>{tags}',
                    unsafe_allow_html=True,
                )

    with col_right:
        with st.container(border=True):
            st.markdown(
                '<div class="panel-label">국가별 적합도 순위</div>',
                unsafe_allow_html=True,
            )
            for i, c in enumerate(countries, 1):
                c_flag    = "🇺🇸" if c["country"] == "US" else "🇯🇵"
                c_name    = {"US": "미국 (USA)", "JP": "일본 (Japan)"}.get(c["country"], c["country"])
                c_score   = c["score"]
                c_color   = "#10b981" if c_score >= 60 else "#f59e0b" if c_score >= 40 else "#ef4444"
                reasoning = (c.get("trend_reasoning") or "")[:40]
                is_top    = c["country"] == top_country
                bg        = "rgba(16,185,129,0.06)" if is_top else "transparent"
                border    = "1px solid rgba(16,185,129,0.3)" if is_top else "1px solid transparent"
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:12px;padding:12px 10px;
                            border-radius:10px;margin-bottom:8px;background:{bg};border:{border}">
                    <div style="font-size:18px;font-weight:800;color:#d1d5db;width:20px">{i}</div>
                    <div style="font-size:22px">{c_flag}</div>
                    <div style="flex:1;min-width:0">
                        <div style="font-size:14px;font-weight:700;color:var(--text-color)">{c_name}</div>
                        <div style="font-size:11px;color:#9ca3af;margin-top:2px;white-space:nowrap;
                                    overflow:hidden;text-overflow:ellipsis">{reasoning}</div>
                    </div>
                    <div style="font-size:22px;font-weight:800;color:{c_color};flex-shrink:0">
                        {c_score}<span style="font-size:11px;color:#9ca3af">점</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # 선정 근거 전문
            if rationale:
                with st.expander("선정 근거 전문 보기"):
                    st.markdown(
                        f'<div class="review-box" style="font-size:13px">{rationale}</div>',
                        unsafe_allow_html=True,
                    )


def render_trade_and_channels(category: str, country: str, r: dict):
    """수출량 추이 바차트 + 주요 채널 Top 3"""
    st.markdown('<div class="section-header">수출 현황 · 주요 채널</div>', unsafe_allow_html=True)
    CHART_H = 280

    col1, col2 = st.columns(2)

    with col1:
        with st.container(border=True):
            st.markdown(f"**대{COUNTRY_SHORT[country]} 수출량 추이 (USD)**")
            try:
                resp = requests.get(
                    f"{API_BASE}/trade-stats/",
                    params={"category": category, "country": country},
                    timeout=30,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    stats = data.get("stats", [])
                    hs_code = data.get("hs_code", "")
                    if stats:
                        df = pd.DataFrame(stats)
                        df["amount_M"] = (df["amount"] / 1_000_000).round(1)
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=df["year"],
                            y=df["amount_M"],
                            mode="lines+markers+text",
                            line=dict(color="#1d4ed8", width=2.5),
                            marker=dict(color="#1d4ed8", size=8),
                            text=df["amount_M"].apply(lambda v: f"${v}M"),
                            textposition="top center",
                            textfont=dict(size=11, color="#1d4ed8"),
                        ))
                        fig.update_layout(
                            margin=dict(t=30, b=10, l=0, r=10),
                            height=CHART_H,
                            yaxis_title="백만 달러 (USD M)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            paper_bgcolor="rgba(0,0,0,0)",
                            yaxis=dict(gridcolor="rgba(128,128,128,0.2)", zeroline=False),
                            xaxis=dict(type="category", tickmode="array", tickvals=df["year"].tolist()),
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        if hs_code:
                            st.caption(f"HS Code: {hs_code}")
                    else:
                        st.caption("수출 통계 데이터 없음")
                else:
                    st.caption("수출 데이터를 불러올 수 없습니다.")
            except Exception as e:
                st.caption(f"수출 데이터 오류: {e}")

    with col2:
        with st.container(border=True):
            st.markdown("**주요 채널 Top 3**")
            st.markdown(
                '<div style="flex:1;display:flex;flex-direction:column;justify-content:space-around;padding:8px 0;min-height:220px">',
                unsafe_allow_html=True,
            )
            ch = r.get("channels", {})
            online = _parse_channel_list(ch.get("online", []))
            offline = _parse_channel_list(ch.get("offline", []))
            combined = online + offline
            top3 = combined[:3]
            if top3:
                html = ""
                for i, c in enumerate(top3, 1):
                    rank_cls = "top" if i == 1 else ""
                    html += f"""<div class="rank-row">
                        <div class="rank-num {rank_cls}">{i}</div>
                        <div>
                            <div class="rank-name">{c['name']}</div>
                            <div class="rank-desc">{c['description'][:60] if c['description'] else ''}</div>
                        </div></div>"""
                st.markdown(html, unsafe_allow_html=True)
            else:
                st.caption("채널 데이터 없음")
            st.markdown("</div>", unsafe_allow_html=True)


def render_kpi_row(r: dict, country: str):
    """시장 규모 / CAGR / 주요 채널 3개 카드"""
    ms = r.get("market_size", {})
    ch = r.get("channels", {})

    value  = ms.get("value") or "N/A"
    cagr   = ms.get("cagr") or ms.get("growth_rate") or "N/A"
    f_year = ms.get("forecast_year") or ""
    f_start = "2024"
    _online_first = ch.get("online", [None])[0] if ch.get("online") else None
    key_platform = ch.get("key_platform") or (
        (_online_first.get("name") if isinstance(_online_first, dict) else str(_online_first))
        if _online_first else "N/A"
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">시장 규모 ({COUNTRY_SHORT[country]})</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-delta-pos">▲ 전년 대비 성장</div>
        </div>""", unsafe_allow_html=True)

    with c2:
        forecast_label = f"{f_start} - {f_year} 예측" if f_year else "연평균 성장률"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">연평균 성장률 (CAGR)</div>
            <div class="kpi-value">{cagr}</div>
            <div class="kpi-sub">{forecast_label}</div>
        </div>""", unsafe_allow_html=True)

    with c3:
        channel_detail = ch.get("details") or "온라인 판매 비중 급증"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">주요 채널</div>
            <div class="kpi-channel">{key_platform}</div>
            <div class="kpi-sub">{channel_detail[:30]}</div>
        </div>""", unsafe_allow_html=True)


def render_trends_section(r: dict, country: str):
    st.markdown('<div class="section-header">성분 · 기능 트렌드</div>', unsafe_allow_html=True)
    tr = r.get("trends", {})
    tag_cls = "tag-us" if country == "US" else "tag-jp"

    col1, col2 = st.columns(2)

    with col1:
        with st.container(border=True):
            st.markdown("**성분 트렌드 (Ingredient Trends)**")
            ingredients = tr.get("ingredients", [])
            html = _tags_html(ingredients[:7], tag_cls)
            if html:
                st.markdown(html, unsafe_allow_html=True)
            else:
                st.caption("데이터 없음")
            rising = tr.get("rising_keywords", [])
            if rising:
                st.markdown('<div class="tag-label" style="margin-top:12px">부상 트렌드</div>',
                            unsafe_allow_html=True)
                rising_html = " ".join(
                    f'<span style="display:inline-block;background:rgba(128,128,128,0.1);color:var(--text-color);'
                    f'border-radius:6px;padding:3px 10px;font-size:12px;margin:3px 3px 3px 0">'
                    f'{kw}</span>' for kw in rising
                )
                st.markdown(rising_html, unsafe_allow_html=True)

    with col2:
        with st.container(border=True):
            st.markdown("**기능성 트렌드 (Functional Trends)**")
            functions = tr.get("functions", [])
            html = _tags_html(functions[:7], tag_cls)
            if html:
                st.markdown(html, unsafe_allow_html=True)
            else:
                st.caption("데이터 없음")

    consumer_needs = tr.get("consumer_needs", "")
    if consumer_needs:
        st.caption(f"소비자 핵심 니즈: {consumer_needs}")



def render_competitors_section(r: dict, country: str):
    st.markdown(f'<div class="section-header">주요 경쟁 브랜드 ({COUNTRY_KO[country]})</div>',
                unsafe_allow_html=True)
    comp = r.get("competitors", {})
    brands = comp.get("brands", [])
    kbeauty = comp.get("kbeauty_brands", [])

    col1, col2 = st.columns([3, 2])
    with col1:
        with st.container(border=True):
            st.markdown("**경쟁 브랜드 순위**")
            if brands:
                html = ""
                for i, b in enumerate(brands[:6], 1):
                    rank_cls = "top" if i == 1 else ""
                    share = b.get("market_share", "")
                    share_txt = f" · {share}" if share else ""
                    html += f"""<div class="rank-row">
                        <div class="rank-num {rank_cls}">{i}</div>
                        <div>
                            <div class="rank-name">{b.get('name', '')}
                                <span style="font-size:11px;color:#9ca3af;font-weight:400">
                                    {b.get('origin','')}{share_txt}
                                </span>
                            </div>
                            <div class="rank-desc">{b.get('description', '')[:80]}</div>
                        </div></div>"""
                st.markdown(html, unsafe_allow_html=True)
            else:
                st.caption("데이터 없음")

    with col2:
        with st.container(border=True):
            st.markdown("**언급된 K-뷰티 브랜드**")
            if kbeauty:
                tags = " ".join(
                    f'<span class="{"tag-us" if country == "US" else "tag-jp"}">{b}</span>'
                    for b in kbeauty[:8]
                )
                st.markdown(tags, unsafe_allow_html=True)
            else:
                st.caption("데이터 없음")

            leader = comp.get("market_leader", "")
            leader_share = comp.get("market_leader_share", "")
            if leader:
                st.markdown("---")
                st.markdown(f"**시장 1위:** {leader}" + (f" ({leader_share})" if leader_share else ""))



def render_kbeauty_share_section(r: dict, country: str):
    ks = r.get("kbeauty_share", {})
    if not ks:
        return

    share = ks.get("share", "")
    rank = ks.get("rank", "")
    export_val = ks.get("export_value", "")
    yoy = ks.get("yoy_growth", "")
    competing = ks.get("competing_countries", [])
    details = ks.get("details", "")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">K-뷰티 점유율 ({COUNTRY_SHORT[country]})</div>
            <div class="kpi-value" style="color:#1d4ed8">{share or 'N/A'}</div>
            <div class="kpi-sub">{rank}</div>
        </div>""", unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">한국 화장품 수출액</div>
            <div class="kpi-value" style="font-size:20px">{export_val or 'N/A'}</div>
            <div class="kpi-delta-pos">{yoy}</div>
        </div>""", unsafe_allow_html=True)

    with c3:
        comp_txt = ", ".join(competing[:3]) if competing else "—"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">주요 경쟁국</div>
            <div class="kpi-value" style="font-size:18px">{comp_txt}</div>
            <div class="kpi-sub">{details[:40] if details else ''}</div>
        </div>""", unsafe_allow_html=True)



def render_top5_rankings(country: str):
    """국가별 플랫폼 Top5 랭킹 테이블"""
    try:
        resp = requests.get(f"{API_BASE}/rankings/", params={"country": country}, timeout=10)
        if resp.status_code != 200:
            st.caption("랭킹 데이터를 불러올 수 없습니다.")
            return
        data = resp.json().get("rankings", {})
    except Exception:
        st.caption("랭킹 서버 연결 실패.")
        return

    # (platform, title, header_bg, title_color, accent_color)
    if country == "US":
        platforms = [
            ("Ulta",    "Ulta Beauty Top 5", "rgba(251,146,60,0.12)",  "#ea580c", "#fb923c"),
            ("Sephora", "Sephora Top 5",      "rgba(59,130,246,0.12)", "#1d4ed8", "#3b82f6"),
        ]
    else:
        platforms = [
            ("Qoo10",   "Qoo10 Top 5",   "rgba(251,146,60,0.12)",  "#ea580c", "#fb923c"),
            ("Rakuten", "Rakuten Top 5", "rgba(59,130,246,0.12)", "#1d4ed8", "#3b82f6"),
        ]

    col1, col2 = st.columns(2)
    for col, (platform, title, header_bg, title_color, accent) in zip([col1, col2], platforms):
        rows = data.get(platform, [])[:5]
        with col:
            rows_html = ""
            for r in rows:
                num = r.get("rank", "")
                name = r.get("title", "")[:55]
                brand = r.get("brand", "") or ""
                url = r.get("url", "")
                name_html = (
                    f'<a href="{url}" target="_blank" style="color:var(--text-color);text-decoration:none;font-weight:600"'
                    f' onmouseover="this.style.textDecoration=\'underline\'" onmouseout="this.style.textDecoration=\'none\'">'
                    f'{name}</a>'
                    if url else f'<span class="top5-name">{name}</span>'
                )
                rows_html += f"""
                <tr>
                  <td><span style="font-size:15px;font-weight:700;color:{accent}">{num:02d}</span></td>
                  <td>{name_html}</td>
                  <td><span class="top5-brand">{brand}</span></td>
                </tr>"""

            st.markdown(f"""
            <div class="top5-wrap" style="border:2px solid {accent}">
              <div style="background:{header_bg};padding:12px 18px 10px;border-bottom:2px solid {accent}">
                <span style="font-size:15px;font-weight:700;color:{title_color}">{title}</span>
              </div>
              <table class="top5-table">
                <thead><tr>
                  <th>RANK</th>
                  <th>PRODUCT NAME</th>
                  <th>BRAND</th>
                </tr></thead>
                <tbody>{rows_html}</tbody>
              </table>
            </div>""", unsafe_allow_html=True)


def render_review_analysis(platform: str, item: dict):
    """선택된 상품의 리뷰 분석 패널"""
    item_id = item.get("platform_item_id", "")
    title = item.get("title", "")
    rank = item.get("rank", "")

    try:
        resp = requests.get(
            f"{API_BASE}/review-analysis/",
            params={"platform": platform, "item_id": item_id},
            timeout=15,
        )
        if resp.status_code == 404:
            st.caption("해당 상품의 리뷰 분석 데이터가 없습니다.")
            return
        if resp.status_code != 200:
            st.caption(f"분석 데이터 오류 ({resp.status_code})")
            return
        d = resp.json()
    except Exception as e:
        st.caption(f"연결 오류: {e}")
        return

    total_rating = d.get("total_rating")
    review_count = d.get("review_count", 0)
    platform_reviews_count = d.get("platform_reviews_count")
    sentiment = d.get("sentiment", {})
    category_scores = d.get("category_scores", [])
    top_keywords = d.get("top_keywords", [])
    sample_reviews = d.get("sample_reviews", {})
    complaints = d.get("complaints", [])
    opportunities = d.get("opportunities", [])

    review_sub = f"최근 2년 기준 {review_count:,}건"

    # 헤더
    st.markdown(f"""
    <div class="panel-header">
        <div>
            <div style="font-size:11px;color:#9ca3af;font-weight:600;margin-bottom:4px">선택 제품 리뷰 분석</div>
            <div class="panel-title">{title}&nbsp;&nbsp;<span class="panel-platform">({platform} #{rank})</span></div>
            <div class="panel-sub">{review_sub}</div>
        </div>
        <div class="rating-badge">
            <div class="rating-badge-label">전체 만족도</div>
            <div><span class="rating-badge-value">{total_rating}</span><span class="rating-badge-denom"> / 5.0</span></div>
        </div>
    </div>""", unsafe_allow_html=True)

    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown('<div class="panel-label">카테고리별 만족도 (CATEGORY SATISFACTION)</div>', unsafe_allow_html=True)
        for cs in category_scores[:6]:
            score = cs["score"]
            count = cs.get("count", "")
            fill_pct = int(score / 5 * 100)
            st.markdown(f"""
            <div class="score-bar-wrap">
                <div class="score-bar-label">
                    <span>{cs['category']}</span>
                    <span style="font-weight:700;color:#1d4ed8">{score}&nbsp;<span style="font-size:11px;color:#9ca3af;font-weight:400">({count}건)</span></span>
                </div>
                <div class="score-bar-bg"><div class="score-bar-fill" style="width:{fill_pct}%"></div></div>
            </div>""", unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="panel-label">긍부정 감성 비율 (SENTIMENT RATIO)</div>', unsafe_allow_html=True)
        pos_pct = sentiment.get("positive", 0)
        neg_pct = sentiment.get("negative", 0)
        fig = go.Figure(go.Pie(
            values=[pos_pct, neg_pct],
            labels=["긍정", "부정"],
            hole=0.65,
            marker_colors=["#3b82f6", "#e5e7eb"],
            textinfo="none",
            hoverinfo="label+percent",
        ))
        fig.update_layout(
            margin=dict(t=0, b=0, l=0, r=0),
            height=140,
            showlegend=False,
            annotations=[dict(
                text=f"<b>{pos_pct}%</b><br><span style='font-size:10px'>POSITIVE</span>",
                x=0.5, y=0.5, font_size=16, showarrow=False,
            )],
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(f"""
        <div style="text-align:center;font-size:12px;margin-top:-10px">
            <span style="color:#3b82f6;font-weight:600">● 긍정 {pos_pct}%</span>&nbsp;&nbsp;
            <span style="color:#9ca3af">◎ 부정 {neg_pct}%</span>
        </div>""", unsafe_allow_html=True)

    # 핵심 키워드
    if top_keywords:
        st.markdown('<div class="panel-label" style="margin-top:8px">핵심 키워드 (KEY KEYWORDS)</div>', unsafe_allow_html=True)
        tags_html = " ".join(
            f'<span class="kw-tag">{kw}</span>' if i < 4 else f'<span class="kw-tag-gray">{kw}</span>'
            for i, kw in enumerate(top_keywords)
        )
        st.markdown(tags_html, unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # 대표 리뷰
    col_p, col_neg = st.columns(2)
    with col_p:
        st.markdown('<div class="review-label pos">👍 긍정 리뷰 요약 (Positive)</div>', unsafe_allow_html=True)
        txt = sample_reviews.get("positive") or "데이터 없음"
        st.markdown(f'<div class="review-box pos">{txt}</div>', unsafe_allow_html=True)
    with col_neg:
        st.markdown('<div class="review-label neg">👎 부정 리뷰 요약 (Negative)</div>', unsafe_allow_html=True)
        txt = sample_reviews.get("negative") or "데이터 없음"
        st.markdown(f'<div class="review-box neg">{txt}</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # 주요 불만 사항 + 시장 기회
    if complaints or opportunities:
        col_c, col_o = st.columns(2)
        with col_c:
            if complaints:
                st.markdown('<div class="section-title-red">COMPLAINTS (주요 불만 사항)</div>', unsafe_allow_html=True)
                for c in complaints:
                    st.markdown(f"""
                    <div class="complaint-bar-wrap">
                        <span class="complaint-label">{c['label']}</span>
                        <div class="complaint-bar-bg"><div class="complaint-bar-fill" style="width:{c['pct']}%"></div></div>
                        <span class="complaint-pct">{c['pct']}%</span>
                    </div>""", unsafe_allow_html=True)
        with col_o:
            if opportunities:
                st.markdown('<div class="section-title-green">OPPORTUNITIES (시장 기회)</div>', unsafe_allow_html=True)
                for op in opportunities:
                    title = op.get('title', '')
                    desc = op.get('description', '') or op.get('summary', '')
                    st.markdown(
                        f'<div class="opp-item">✓ <b style="color:#10b981">{title}</b>: {desc}</div>',
                        unsafe_allow_html=True)


def render_ad_strategy(result: dict):
    """AI 마케팅 전략 제안 섹션 (파란 그라데이션 배경)"""
    if not result or "error" in result:
        st.info(result.get("error", "마케팅 전략 데이터를 생성할 수 없습니다."))
        return

    country = result.get("country", "US")
    country_label = {"US": "미국 시장용", "JP": "일본 시장용"}.get(country, country)
    concept = result.get("brand_concept", "")
    reasoning = result.get("concept_reasoning", "")
    messages = result.get("key_messages", [])
    headline = result.get("headline", "")
    body_text = result.get("body_text", "")
    insight = result.get("detailed_insight", "")

    # 핵심 메시징 HTML
    msgs_html = "".join(
        f'<div class="ad-strategy-msg">{m}</div>' for m in messages
    )

    html = (
        f'<div class="ad-strategy-wrap">'
        f'<div class="ad-strategy-badge">✦ AI 마케팅 전략 제안 ({country_label})</div>'
        f'<div style="display:flex;gap:30px;flex-wrap:wrap">'
        f'<div style="flex:1;min-width:300px">'
        f'<div class="ad-strategy-label">추천 브랜드 컨셉</div>'
        f'<div class="ad-strategy-concept">&ldquo;{concept}&rdquo;</div>'
        f'<div class="ad-strategy-reasoning">{reasoning}</div>'
        f'<div class="ad-strategy-label">핵심 메시징</div>'
        f'{msgs_html}'
        f'</div>'
        f'<div style="flex:1;min-width:300px">'
        f'<div class="ad-copy-box">'
        f'<div class="ad-strategy-label" style="color:rgba(255,255,255,0.6)">추천 광고 카피 (Suggested Copy)</div>'
        f'<div class="ad-copy-field-label">Headline</div>'
        f'<div class="ad-copy-headline">&ldquo;{headline}&rdquo;</div>'
        f'<div class="ad-copy-field-label">Body Text</div>'
        f'<div class="ad-copy-body">{body_text}</div>'
        f'</div>'
        f'<div class="ad-insight-box">'
        f'<div class="ad-insight-label">Detailed Insight</div>'
        f'<div class="ad-insight-text">{insight}</div>'
        f'</div>'
        f'</div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_meta_ads_section(country: str):
    try:
        resp = requests.get(f"{API_BASE}/meta-ads/", params={"country": country}, timeout=5)
        if resp.status_code != 200:
            st.warning("Meta 광고 데이터를 불러올 수 없습니다.")
            return
        ads = resp.json().get("ads", [])
        if not ads:
            st.info("Meta 광고 데이터가 없습니다. `python manage.py load_meta_ads` 를 실행하세요.")
            return

        cols = st.columns(len(ads))
        for col, ad in zip(cols, ads):
            image_pct = round(ad["image_ratio"] * 100)
            video_pct = round(ad["video_ratio"] * 100)
            updated = str(ad.get("updated_at", ""))[:10]
            copy_text = ad.get("latest_ad_text", "") or "—"
            if len(copy_text) > 80:
                copy_text = copy_text[:80] + "..."

            with col:
                st.markdown(f"""
                <div class="meta-card">
                  <div class="meta-brand">{ad['brand']}</div>
                  <div class="meta-channel">{ad['channel']}</div>
                  <div class="meta-count-label">최근 90일 광고</div>
                  <div class="meta-count-value">{ad['total_ads']}개</div>
                  <div class="meta-copy-label">최근 광고 카피</div>
                  <div class="meta-copy-text">"{copy_text}"</div>
                  <div class="meta-updated">업데이트: {updated}</div>
                </div>
                """, unsafe_allow_html=True)
                page_id = ad.get("page_id", "")
                market = "US" if ad["channel"] in ("ulta", "sephora") else "JP"
                if page_id:
                    ad_url = (
                        f"https://www.facebook.com/ads/library/"
                        f"?active_status=active&ad_type=all&country={market}"
                        f"&media_type=all&search_type=page&view_all_page_id={page_id}"
                    )
                    st.link_button("Meta 광고 보기 →", ad_url, use_container_width=True)
    except Exception as e:
        st.error(f"Meta 광고 섹션 오류: {e}")


@st.fragment
def render_top10_rankings(country: str):
    """국가별 플랫폼 Top10 랭킹 — 클릭 시 우측에 리뷰 분석 패널 표시 (fragment: 스크롤 유지)"""
    try:
        resp = requests.get(
            f"{API_BASE}/rankings/",
            params={"country": country},
            timeout=10,
        )
        if resp.status_code != 200:
            st.caption("랭킹 데이터를 불러올 수 없습니다.")
            return
        data = resp.json().get("rankings", {})
    except Exception:
        st.caption("랭킹 서버 연결 실패.")
        return

    if country == "US":
        platforms = [("Ulta", "Ulta Beauty Top 10"), ("Sephora", "Sephora Top 10")]
    else:
        platforms = [("Qoo10", "Qoo10 Top 10"), ("Rakuten", "Rakuten Top 10")]

    # 국가별로 session_state 키를 분리하여 탭 간 충돌 방지
    sk_platform = f"ri_platform_{country}"
    sk_item     = f"ri_item_{country}"
    sk_item_id  = f"ri_item_id_{country}"
    for k in [sk_platform, sk_item, sk_item_id]:
        if k not in st.session_state:
            st.session_state[k] = None

    def _select(platform, row, item_id):
        st.session_state[sk_platform] = platform
        st.session_state[sk_item]     = row
        st.session_state[sk_item_id]  = item_id

    tab_labels = [title for _, title in platforms]
    tabs = st.tabs(tab_labels)

    for tab, (platform, title) in zip(tabs, platforms):
        rows = data.get(platform, [])
        with tab:
            col_list, col_detail = st.columns([5, 8])

            with col_list:
                st.markdown(
                    '<div class="panel-label" style="margin-bottom:10px">TOP 10 베스트셀러</div>',
                    unsafe_allow_html=True,
                )
                for row in rows:
                    num     = row.get("rank", 0)
                    name    = row.get("title", "")
                    brand   = row.get("brand", "") or ""
                    item_id = row.get("platform_item_id", "")
                    is_selected = (
                        st.session_state[sk_platform] == platform
                        and st.session_state[sk_item_id] == item_id
                    )
                    brand_short = f"  ·  {brand[:18]}" if brand else ""
                    btn_label   = f"{num:02d}  {name[:28]}{brand_short}"
                    st.button(
                        btn_label,
                        key=f"ri_{country}_{platform}_{item_id}",
                        use_container_width=True,
                        type="primary" if is_selected else "secondary",
                        on_click=_select,
                        args=(platform, row, item_id),
                    )

            with col_detail:
                if st.session_state[sk_platform] == platform and st.session_state[sk_item]:
                    with st.container(border=True):
                        render_review_analysis(platform, st.session_state[sk_item])
                else:
                    st.markdown("""
                    <div style='text-align:center;min-height:520px;display:flex;flex-direction:column;
                                align-items:center;justify-content:center;color:#9ca3af'>
                        <div style='font-size:40px'>📊</div>
                        <div style='font-size:14px;margin-top:14px;line-height:1.7'>
                            왼쪽 상품을 클릭하면<br>리뷰 분석 결과를 확인할 수 있습니다
                        </div>
                    </div>""", unsafe_allow_html=True)


# ── 메인 ─────────────────────────────────────────────────────────────────────
if not submit_btn:
    st.markdown("""
    <div style='text-align:center;padding:80px 0;color:#9ca3af'>
        <div style='font-size:48px'>G</div>
        <div style='font-size:20px;font-weight:700;color:#1d4ed8;margin-top:16px'>
            GLOBAL BEAUTY INSIGHT
        </div>
        <div style='font-size:14px;margin-top:8px;color:#6b7280'>
            카테고리와 제품 정보를 입력하고 분석을 시작하세요
        </div>
    </div>
    """, unsafe_allow_html=True)

else:
    product_info = f"제품명: {product_name}, 주요 성분: {ingredients}, 핵심 효능: {effects}"

    # ── AI 최적 국가 추천 ──────────────────────────────────────────────
    with st.spinner("AI 최적 진출 국가 분석 중..."):
        try:
            rec_resp = requests.post(
                f"{API_BASE}/country-recommend/",
                json={
                    "product_name": product_name,
                    "category":     selected_category,
                    "ingredients":  ingredients,
                    "effects":      effects,
                },
                timeout=120,
            )
            if rec_resp.status_code == 200:
                rec_data = rec_resp.json()
                render_country_recommendation(rec_data)
                top_country = rec_data.get("top_country", {}).get("country", "US")
            else:
                st.warning("국가 추천 데이터를 불러올 수 없습니다.")
                top_country = "US"
        except Exception as e:
            st.warning(f"국가 추천 서비스 오류: {e}")
            top_country = "US"

    st.markdown("---")

    # ── 국가별 시장 분석 (탭) ─────────────────────────────────────────
    with st.spinner(f"'{selected_category}' 시장 데이터 로딩 중..."):
        try:
            resp = requests.post(
                f"{API_BASE}/match/",
                json={"category": selected_category, "product_info": product_info},
                timeout=120,
            )
            if resp.status_code != 200:
                st.error(f"서버 오류 ({resp.status_code})")
                st.stop()

            result   = resp.json()
            research = result.get("research", {})

            if not research:
                st.warning("시장 리서치 데이터가 없습니다. `python manage.py ingest_research --section-crawl` 을 먼저 실행하세요.")
                st.stop()

        except requests.exceptions.ConnectionError:
            st.error("Django 서버가 실행 중이 아닙니다. `python manage.py runserver` 확인")
            st.stop()
        except Exception as e:
            st.error(f"오류 발생: {e}")
            st.stop()

    st.markdown('<div class="section-header">국가별 시장 분석</div>', unsafe_allow_html=True)
    tab_us, tab_jp = st.tabs(["🇺🇸 미국 (USA)", "🇯🇵 일본 (Japan)"])

    for tab, country in [(tab_us, "US"), (tab_jp, "JP")]:
        r = research.get(country, {})
        with tab:
            if not r:
                st.warning(f"{COUNTRY_KO[country]} 데이터가 없습니다.")
                continue

            # ── KPI 3개 카드 ──────────────────────────────────────
            render_kpi_row(r, country)
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

            # ── K-뷰티 점유율 ─────────────────────────────────────
            st.markdown(f'<div class="section-header">K-뷰티 시장 점유율 ({COUNTRY_KO[country]})</div>',
                        unsafe_allow_html=True)
            render_kbeauty_share_section(r, country)
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

            # ── 수출 현황 · 주요 채널 ─────────────────────────────
            render_trade_and_channels(selected_category, country, r)
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

            # ── 트렌드 ────────────────────────────────────────────
            render_trends_section(r, country)
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

            # ── Top5 랭킹 ─────────────────────────────────────────
            st.markdown('<div class="section-header">채널별 베스트셀러 Top 5</div>', unsafe_allow_html=True)
            render_top5_rankings(country)
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

            # ── 리뷰 인사이트 (Top10 클릭형) ──────────────────────
            st.markdown('<div class="section-header">리뷰 인사이트 & 채널 분석</div>', unsafe_allow_html=True)
            render_top10_rankings(country)
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

            # ── Meta 광고 현황 ────────────────────────────────────
            st.markdown('<div class="section-header">Top10 브랜드 Meta 광고 현황</div>',
                        unsafe_allow_html=True)
            render_meta_ads_section(country)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── AI 마케팅 전략 제안 (맨 하단) ─────────────────────────────────
    with st.spinner("AI 마케팅 전략 생성 중..."):
        try:
            strategy_resp = requests.post(
                f"{API_BASE}/ad-strategy/",
                json={
                    "product_name": product_name,
                    "category":     selected_category,
                    "ingredients":  ingredients,
                    "effects":      effects,
                    "country":      top_country,
                },
                timeout=120,
            )
            if strategy_resp.status_code == 200:
                render_ad_strategy(strategy_resp.json())
            else:
                st.info("광고 전략 데이터를 생성할 수 없습니다. Meta 광고 데이터를 먼저 로드하세요.")
        except Exception as e:
            st.info(f"마케팅 전략 서비스 오류: {e}")
