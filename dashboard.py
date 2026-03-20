import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import re

st.set_page_config(
    page_title="Global Beauty Insight",
    page_icon="G",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* 전체 배경 */
[data-testid="stAppViewContainer"],
[data-testid="stMain"] {
    background: #f3f4f6 !important;
}
[data-testid="stHeader"] { background: transparent !important; }

/* 본문 여백 */
.main .block-container {
    padding-top: 0.5rem;
    padding-bottom: 2rem;
    max-width: 1280px;
}

/* ── 헤더 ── */
.gbi-header {
    background: #fff;
    border-bottom: 1px solid #e5e7eb;
    padding: 14px 28px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 24px;
    border-radius: 0 0 0 0;
}
.gbi-logo {
    display: flex;
    align-items: center;
    gap: 10px;
}
.gbi-logo-icon {
    width: 36px; height: 36px;
    background: #1d4ed8;
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px; font-weight: 700; color: #fff;
}
.gbi-logo-text {
    font-size: 18px; font-weight: 700;
    color: #1d4ed8; letter-spacing: 0.04em;
}
.gbi-user {
    display: flex; align-items: center; gap: 8px;
    font-size: 14px; color: #374151; font-weight: 500;
}

/* ── 카드 ── */
.card {
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    padding: 20px 24px;
    margin-bottom: 16px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.card-title {
    font-size: 12px; font-weight: 700;
    color: #6b7280; text-transform: uppercase;
    letter-spacing: 0.06em; margin-bottom: 6px;
}

/* ── 섹션 제목 ── */
.section-header {
    font-size: 16px; font-weight: 700;
    color: #111827;
    padding-left: 12px;
    border-left: 4px solid #1d4ed8;
    margin-bottom: 16px;
}

/* ── KPI 메트릭 카드 ── */
.kpi-card {
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    padding: 20px 22px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.kpi-label { font-size: 12px; color: #6b7280; font-weight: 600; margin-bottom: 8px; }
.kpi-value { font-size: 28px; font-weight: 700; color: #111827; line-height: 1.2; }
.kpi-sub   { font-size: 12px; color: #6b7280; margin-top: 4px; }
.kpi-delta-pos { font-size: 12px; color: #10b981; font-weight: 600; margin-top: 4px; }
.kpi-channel { font-size: 24px; font-weight: 700; color: #0ea5e9; }

/* ── 태그 ── */
.tag-us {
    display: inline-block; background: #eff6ff; color: #1d4ed8;
    border-radius: 6px; padding: 3px 10px; font-size: 12px; font-weight: 600;
    margin: 3px 3px 3px 0;
}
.tag-jp {
    display: inline-block; background: #fdf2f8; color: #db2777;
    border-radius: 6px; padding: 3px 10px; font-size: 12px; font-weight: 600;
    margin: 3px 3px 3px 0;
}
.tag-label {
    font-size: 10px; font-weight: 700; letter-spacing: 0.1em;
    color: #9ca3af; margin-top: 10px; margin-bottom: 4px;
}

/* ── 채널/브랜드 순위 ── */
.rank-row {
    display: flex; align-items: flex-start;
    padding: 10px 0; border-bottom: 1px solid #f3f4f6;
}
.rank-num {
    font-size: 18px; font-weight: 700;
    color: #d1d5db; width: 28px; flex-shrink: 0;
    margin-right: 12px; line-height: 1.4;
}
.rank-num.top { color: #1d4ed8; }
.rank-name { font-size: 14px; font-weight: 600; color: #111827; }
.rank-desc { font-size: 12px; color: #9ca3af; margin-top: 2px; }

/* ── 비교 테이블 ── */
.compare-table { width: 100%; border-collapse: collapse; }
.compare-table th {
    background: #f9fafb; padding: 10px 14px; font-size: 12px;
    font-weight: 700; color: #374151; text-align: left;
    border-bottom: 2px solid #e5e7eb;
}
.compare-table td {
    padding: 9px 14px; font-size: 13px; color: #374151;
    border-bottom: 1px solid #f3f4f6; vertical-align: top;
}
.compare-table .label-col { color: #9ca3af; font-weight: 600; width: 110px; }
.us-col { color: #1d4ed8; }
.jp-col { color: #db2777; }

/* ── Top5 랭킹 테이블 ── */
.top5-wrap {
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid #e5e7eb;
}
.top5-header-light {
    background: #fff8f0;
    padding: 12px 18px 10px;
    border-bottom: 2px solid #fb923c;
}
.top5-header-dark {
    background: #1a1a2e;
    padding: 12px 18px 10px;
    border-bottom: 2px solid #6366f1;
}
.top5-title-light {
    font-size: 15px; font-weight: 700; color: #ea580c;
}
.top5-title-dark {
    font-size: 15px; font-weight: 700; color: #fff;
}
.top5-table { width: 100%; border-collapse: collapse; }
.top5-table th {
    font-size: 10px; font-weight: 700; letter-spacing: 0.08em;
    color: #9ca3af; padding: 8px 12px; text-align: left;
    border-bottom: 1px solid #f3f4f6; background: #fafafa;
}
.top5-table th.dark { background: #16213e; color: #6b7280; border-bottom: 1px solid #2d3748; }
.top5-table td {
    padding: 9px 12px; font-size: 13px; color: #374151;
    border-bottom: 1px solid #f3f4f6; vertical-align: middle;
}
.top5-table td.dark {
    color: #e2e8f0; border-bottom: 1px solid #2d3748; background: #1a1a2e;
}
.top5-rank-light {
    font-size: 15px; font-weight: 700; color: #fb923c; width: 36px;
}
.top5-rank-dark {
    font-size: 15px; font-weight: 700; color: #818cf8; width: 36px;
}
.top5-name { font-weight: 600; }
.top5-brand { color: #6b7280; font-size: 12px; }
.top5-brand.dark { color: #94a3b8; }

/* st.container(border) 통일 */
[data-testid="stVerticalBlockBorderWrapper"] > div:first-child {
    background: #fff !important;
    border-radius: 14px !important;
    border-color: #e5e7eb !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06) !important;
}

/* 수출현황·주요채널 섹션 컬럼 등높이 */
[data-testid="stHorizontalBlock"]:has([data-testid="stVerticalBlockBorderWrapper"]) {
    align-items: stretch;
}
[data-testid="stHorizontalBlock"]:has([data-testid="stVerticalBlockBorderWrapper"])
    > [data-testid="column"]
    > [data-testid="stVerticalBlock"] {
    height: 100%;
}
[data-testid="stHorizontalBlock"]:has([data-testid="stVerticalBlockBorderWrapper"])
    > [data-testid="column"]
    > [data-testid="stVerticalBlock"]
    > [data-testid="stVerticalBlockBorderWrapper"] {
    height: 100%;
    display: flex;
    flex-direction: column;
}
[data-testid="stHorizontalBlock"]:has([data-testid="stVerticalBlockBorderWrapper"])
    > [data-testid="column"]
    > [data-testid="stVerticalBlock"]
    > [data-testid="stVerticalBlockBorderWrapper"]
    > div:first-child {
    flex: 1;
    display: flex !important;
    flex-direction: column;
}
</style>
""", unsafe_allow_html=True)

API_BASE = "http://127.0.0.1:8000/api"

CATEGORY_LIST = ["스킨케어"]

# ── 사이드바 ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Global Beauty Insight")
    st.markdown("---")

    selected_country = st.radio(
        "분석 국가",
        options=["US", "JP"],
        format_func=lambda x: "미국 (USA)" if x == "US" else "일본 (Japan)",
    )
    st.markdown("---")
    st.caption("국가를 선택하면 해당 국가의 시장 데이터를 확인할 수 있습니다.")

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
                            plot_bgcolor="#fff",
                            paper_bgcolor="#fff",
                            yaxis=dict(gridcolor="#f3f4f6", zeroline=False),
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
                    f'<span style="display:inline-block;background:#f3f4f6;color:#374151;'
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
    """국가별 플랫폼 Top5 랭킹 테이블 (항상 표시)"""
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
        platforms = [("Ulta", "Ulta Beauty Top 5", "light"), ("Sephora", "Sephora Top 5", "dark")]
    else:
        platforms = [("Qoo10", "Qoo10 Top 5", "light"), ("Rakuten", "Rakuten Top 5", "dark")]

    col1, col2 = st.columns(2)
    for col, (platform, title, theme) in zip([col1, col2], platforms):
        rows = data.get(platform, [])
        with col:
            header_cls = f"top5-header-{theme}"
            title_cls = f"top5-title-{theme}"
            rank_cls = f"top5-rank-{theme}"
            dark = theme == "dark"
            th_cls = " class='dark'" if dark else ""
            td_cls = " class='dark'" if dark else ""

            rows_html = ""
            link_color = "#e2e8f0" if dark else "#111827"
            for r in rows:
                num = r.get("rank", "")
                name = r.get("title", "")[:55]
                brand = r.get("brand", "") or ""
                url = r.get("url", "")
                name_html = (
                    f'<a href="{url}" target="_blank" style="color:{link_color};text-decoration:none;font-weight:600"'
                    f' onmouseover="this.style.textDecoration=\'underline\'" onmouseout="this.style.textDecoration=\'none\'">'
                    f'{name}</a>'
                    if url else f'<span class="top5-name">{name}</span>'
                )
                rows_html += f"""
                <tr>
                  <td{td_cls}><span class="{rank_cls}">{num:02d}</span></td>
                  <td{td_cls}>{name_html}</td>
                  <td{td_cls}><span class="top5-brand{' dark' if dark else ''}">{brand}</span></td>
                </tr>"""

            bg = "#1a1a2e" if dark else "#fff"
            html = f"""
            <div class="top5-wrap" style="background:{bg}">
              <div class="{header_cls}">
                <span class="{title_cls}">{title}</span>
              </div>
              <table class="top5-table">
                <thead>
                  <tr>
                    <th{th_cls}>RANK</th>
                    <th{th_cls}>PRODUCT NAME</th>
                    <th{th_cls}>BRAND</th>
                  </tr>
                </thead>
                <tbody>{rows_html}</tbody>
              </table>
            </div>"""
            st.markdown(html, unsafe_allow_html=True)


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

    with st.spinner(f"'{selected_category}' {COUNTRY_KO[selected_country]} 시장 분석 중..."):
        try:
            resp = requests.post(
                f"{API_BASE}/match/",
                json={"category": selected_category, "product_info": product_info},
                timeout=120,
            )
            if resp.status_code != 200:
                st.error(f"서버 오류 ({resp.status_code})")
                st.stop()

            result = resp.json()
            research = result.get("research", {})

            if not research:
                st.warning("시장 리서치 데이터가 없습니다. `python manage.py ingest_research --section-crawl` 을 먼저 실행하세요.")
                st.stop()

            r = research.get(selected_country, {})
            if not r:
                st.warning(f"{COUNTRY_KO[selected_country]} 데이터가 없습니다.")
                st.stop()

            # ── KPI 3개 카드 ──────────────────────────────────────
            render_kpi_row(r, selected_country)

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

            # ── K-뷰티 점유율 ─────────────────────────────────────
            st.markdown(f'<div class="section-header">K-뷰티 시장 점유율 ({COUNTRY_KO[selected_country]})</div>',
                        unsafe_allow_html=True)
            render_kbeauty_share_section(r, selected_country)

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

            # ── 수출 현황 · 주요 채널 ─────────────────────────────
            render_trade_and_channels(selected_category, selected_country, r)

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

            # ── 트렌드 (선택 국가) ────────────────────────────────
            render_trends_section(r, selected_country)

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

            # ── Top5 랭킹 ─────────────────────────────────────────
            st.markdown('<div class="section-header">채널별 베스트셀러 Top 5</div>', unsafe_allow_html=True)
            render_top5_rankings(selected_country)

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

            # ── 경쟁 브랜드 ───────────────────────────────────────
            # render_competitors_section(r, selected_country)

            # ── 출처 ─────────────────────────────────────────────
            # sources = r.get("sources", [])
            # if sources:
            #     with st.expander("데이터 출처"):
            #         for s in sources:
            #             if s:
            #                 st.markdown(f"- {s}")

        except requests.exceptions.ConnectionError:
            st.error("Django 서버가 실행 중이 아닙니다. `python manage.py runserver` 확인")
        except Exception as e:
            st.error(f"오류 발생: {e}")
            st.exception(e)
