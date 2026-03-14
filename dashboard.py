import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="K-Beauty 시장 인텔리전스",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── 전체 배경: 회색으로 변경 ──
   라이트: 메인=회색(secondary), 카드=흰색(background)
   다크:   메인=검정(background), 카드=진회색(secondary)  → Streamlit 기본과 동일
*/
.main .block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1300px; }

[data-testid="stAppViewContainer"] { background: var(--secondary-background-color) !important; }
[data-testid="stMain"]             { background: var(--secondary-background-color) !important; }
[data-testid="stHeader"]           { background: transparent !important; }

/* ── 카드: 배경을 페이지보다 한 단계 밝게 ──
   라이트: --background-color = #ffffff (흰색)
   다크:   --background-color = #0e1117 (매우 어두움 → 카드에 border 강조)
*/
.card {
    background: var(--background-color);
    border: 1px solid rgba(128,128,128,0.15);
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 16px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

/* 카드 사이 수직 간격 통일 */
[data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] {
    gap: 16px;
}
.card-title {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-color);
    opacity: 0.65;
    margin-bottom: 4px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
/* st.container(border=True) 스타일을 .card와 통일 */
[data-testid="stVerticalBlockBorderWrapper"] > div:first-child {
    background: var(--background-color) !important;
    border-radius: 12px !important;
    border-color: rgba(128,128,128,0.15) !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
}

/* 3열 레이아웃 등높이: 비교표 | 바차트 | 도넛 */
div[data-testid="stHorizontalBlock"]:has(.compare-table) {
    align-items: stretch;
}
div[data-testid="stHorizontalBlock"]:has(.compare-table) > div[data-testid="stColumn"] {
    display: flex;
    flex-direction: column;
}
div[data-testid="stHorizontalBlock"]:has(.compare-table) > div[data-testid="stColumn"] > div {
    flex: 1;
}
div[data-testid="stHorizontalBlock"]:has(.compare-table) .card {
    height: 100%;
    box-sizing: border-box;
}
div[data-testid="stHorizontalBlock"]:has(.compare-table) [data-testid="stVerticalBlockBorderWrapper"] {
    height: 100%;
}
div[data-testid="stHorizontalBlock"]:has(.compare-table) [data-testid="stVerticalBlockBorderWrapper"] > div:first-child {
    height: 100%;
    box-sizing: border-box;
}

.metric-value {
    font-size: 28px;
    font-weight: 700;
    color: var(--text-color);
    line-height: 1.2;
}
.metric-delta-pos { font-size: 13px; color: #10b981; font-weight: 600; }
.metric-delta-neg { font-size: 13px; color: #ef4444; font-weight: 600; }
.metric-badge {
    display: inline-block;
    font-size: 10px;
    padding: 2px 7px;
    border-radius: 10px;
    background: rgba(59,130,246,0.15);
    color: #3b82f6;
    font-weight: 600;
    margin-left: 6px;
}

/* 트렌드 태그 */
.tag-us {
    display: inline-block;
    background: rgba(59,130,246,0.15);
    color: #3b82f6;
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 12px;
    font-weight: 600;
    margin: 3px 3px 3px 0;
}
.tag-jp {
    display: inline-block;
    background: rgba(236,72,153,0.15);
    color: #ec4899;
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 12px;
    font-weight: 600;
    margin: 3px 3px 3px 0;
}
.tag-label {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.1em;
    color: var(--text-color);
    opacity: 0.5;
    margin-top: 10px;
    margin-bottom: 4px;
}

/* 채널 랭킹 */
.rank-row {
    display: flex;
    align-items: flex-start;
    padding: 10px 0;
    border-bottom: 1px solid rgba(128,128,128,0.15);
}
.rank-num {
    font-size: 18px;
    font-weight: 700;
    color: var(--text-color);
    opacity: 0.3;
    width: 28px;
    flex-shrink: 0;
    margin-right: 12px;
    line-height: 1.4;
}
.rank-num.top { color: #3b82f6; opacity: 1; }
.rank-name { font-size: 14px; font-weight: 600; color: var(--text-color); }
.rank-desc { font-size: 12px; color: var(--text-color); opacity: 0.55; margin-top: 2px; }

/* 섹션 구분선 */
.section-divider {
    height: 1px;
    background: rgba(128,128,128,0.15);
    margin: 20px 0;
}

/* AI 추정/검증 배지 */
.badge-estimated {
    display: inline-block;
    font-size: 10px;
    padding: 2px 8px;
    border-radius: 10px;
    background: rgba(251,191,36,0.2);
    color: #d97706;
    font-weight: 600;
    margin-left: 6px;
}
.badge-verified {
    display: inline-block;
    font-size: 10px;
    padding: 2px 8px;
    border-radius: 10px;
    background: rgba(16,185,129,0.15);
    color: #059669;
    font-weight: 600;
    margin-left: 6px;
}

/* 비교 테이블 */
.compare-table { width: 100%; border-collapse: collapse; }
.compare-table th {
    background: rgba(128,128,128,0.08);
    padding: 10px 14px;
    font-size: 12px;
    font-weight: 700;
    color: var(--text-color);
    text-align: left;
    border-bottom: 2px solid rgba(128,128,128,0.2);
}
.compare-table td {
    padding: 9px 14px;
    font-size: 13px;
    color: var(--text-color);
    border-bottom: 1px solid rgba(128,128,128,0.1);
    vertical-align: top;
}
.compare-table .label-col { opacity: 0.6; font-weight: 600; width: 110px; }
.us-col { color: #3b82f6; }
.jp-col { color: #ec4899; }
</style>
""", unsafe_allow_html=True)

API_BASE = "http://127.0.0.1:8000/api"

CATEGORY_LIST = [
    "기초화장품",
    "마스크팩",
    "메이크업",
    "입술화장품",
    "눈화장품",
    "샴푸",
    "헤어케어",
    "매니큐어",
]

COUNTRY_LABELS = {"US": "🇺🇸 미국 (USA)", "JP": "🇯🇵 일본 (JPN)"}
COUNTRY_SHORT  = {"US": "미국", "JP": "일본"}

# ── 사이드바 ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📊 K-Beauty Intelligence")
    st.markdown("---")

    page = st.radio(
        "메뉴",
        ["시장 & 트렌드", "국가 수출 & 마케팅 전략"],
        label_visibility="collapsed",
    )

    st.markdown("---")

    if page == "시장 & 트렌드":
        st.markdown("**카테고리 선택**")
        selected_category = st.selectbox(
            "카테고리",
            options=CATEGORY_LIST,
            label_visibility="collapsed",
        )

        st.markdown("**제품 정보 입력** (선택)")
        product_info = st.text_area(
            "제품 정보",
            placeholder="분석하고자 하는 제품의 주요 성분, 기능, 타겟층을 입력하세요\n(예: 비타민C 함유 미백 세럼)",
            height=100,
            label_visibility="collapsed",
        )

        st.markdown("")
        submit_btn = st.button("🔍 분석 실행", use_container_width=True, type="primary")

        st.markdown("---")
        st.caption("💡 동일 카테고리 재검색 시 DB 캐시로 빠르게 로드됩니다.")
    else:
        st.info("🚧 준비 중인 페이지입니다.")
        submit_btn = False
        selected_category = CATEGORY_LIST[0]
        product_info = ""


# ============================================================
# 렌더링 헬퍼
# ============================================================
def _badge(data_source: str) -> str:
    if data_source == "estimated":
        return '<span class="badge-estimated">AI 추정</span>'
    elif data_source == "verified":
        return '<span class="badge-verified">검증됨</span>'
    return ""


def _source_expander(quote: str, label: str = "📄 원문 근거"):
    """source_quote가 있으면 expander로 표시, 없으면 경고."""
    if quote and quote.strip():
        with st.expander(label, expanded=False):
            st.markdown(
                f'<div style="font-size:12px;color:var(--text-color);'
                f'background:var(--secondary-background-color);'
                f'padding:10px 12px;border-left:3px solid #3b82f6;border-radius:4px">'
                f'{quote}</div>',
                unsafe_allow_html=True,
            )
    else:
        st.caption("⚠️ 원문 근거 없음 — 수치 신뢰도 낮음")


def render_metric_cards(research: dict):
    """상단 4개 KPI 카드"""
    cols = st.columns(4)
    order = [("US", 0), ("JP", 2)]
    for code, base_idx in order:
        r = research.get(code, {})
        if not r:
            continue
        ms = r.get("market_size", {})
        ks = r.get("kbeauty_share", {})
        badge = _badge(r.get("data_source", ""))
        country = COUNTRY_SHORT[code]

        # 시장 규모
        value = ms.get("value") or "N/A"
        delta = ms.get("growth_rate") or ms.get("cagr") or ""
        delta_html = f'<span class="metric-delta-pos">▲ {delta}</span>' if delta else ""
        no_data_hint = '<div style="font-size:11px;color:#d1d5db;margin-top:6px">딥리서치 필요</div>' if value == "N/A" else ""

        with cols[base_idx]:
            st.markdown(f"""
            <div class="card">
                <div class="card-title">{country} 시장 규모 {badge}</div>
                <div class="metric-value">{value}</div>
                {delta_html}{no_data_hint}
            </div>""", unsafe_allow_html=True)
            _source_expander(ms.get("source_quote", ""), "📄 시장 규모 원문 근거")

        # K-뷰티 점유율/성장률
        kshare = ks.get("share") or ms.get("cagr") or "N/A"
        kdesc = (ks.get("details") or "")[:30]
        no_data_hint2 = '<div style="font-size:11px;color:#d1d5db;margin-top:6px">딥리서치 필요</div>' if kshare == "N/A" else ""
        with cols[base_idx + 1]:
            st.markdown(f"""
            <div class="card">
                <div class="card-title">{country} K-뷰티 성장률 {badge}</div>
                <div class="metric-value" style="color:{'#10b981' if kshare != 'N/A' else '#d1d5db'}">{kshare}</div>
                <span style="font-size:11px;color:#6b7280">{kdesc}</span>{no_data_hint2}
            </div>""", unsafe_allow_html=True)
            _source_expander(ks.get("source_quote", ""), "📄 K-뷰티 성장률 원문 근거")


def render_comparison_table_html(research: dict) -> str:
    us = research.get("US", {})
    jp = research.get("JP", {})

    def _v(r, keys, default="—"):
        for k in keys:
            v = r.get(k)
            if isinstance(v, dict):
                for sk in ["share", "value", "details"]:
                    if v.get(sk):
                        return str(v[sk])[:60]
            if isinstance(v, list) and v:
                return ", ".join(str(x) for x in v[:3])
            if isinstance(v, str) and v:
                return v[:60]
        return default

    rows = [
        ("K-뷰티 위치",  _v(us, ["kbeauty_share"]),  _v(jp, ["kbeauty_share"])),
        ("주요 유통",    _v(us, ["channels"],),        _v(jp, ["channels"])),
        ("경쟁 브랜드",  _v(us, ["competitors"]),      _v(jp, ["competitors"])),
        ("성분 트렌드",  _v(us, ["trends"]),           _v(jp, ["trends"])),
        ("HS 코드",      research.get("hs_code", "—"), research.get("hs_code", "—")),
    ]

    # channels 특별 처리
    def _channels(r):
        ch = r.get("channels", {})
        def _name(x): return x["name"] if isinstance(x, dict) else x
        online = [_name(x) for x in ch.get("online", [])]
        offline = [_name(x) for x in ch.get("offline", [])]
        items = online[:2] + offline[:1]
        return ", ".join(items) if items else "—"

    def _competitors(r):
        comp = r.get("competitors", {})
        brands = comp.get("brands", [])
        return ", ".join(b["name"] for b in brands[:3]) if brands else "—"

    def _trends_ingredients(r):
        tr = r.get("trends", {})
        ing = tr.get("ingredients", [])
        return ", ".join(ing[:3]) if ing else "—"

    rows = [
        ("K-뷰티 위치",  _v(us, ["kbeauty_share"]),       _v(jp, ["kbeauty_share"])),
        ("주요 유통",    _channels(us),                    _channels(jp)),
        ("경쟁 브랜드",  _competitors(us),                 _competitors(jp)),
        ("성분 트렌드",  _trends_ingredients(us),          _trends_ingredients(jp)),
        ("HS 코드",      research.get("hs_code", "—"),     research.get("hs_code", "—")),
    ]

    html = '<table class="compare-table"><thead><tr>'
    html += '<th class="label-col">항목</th>'
    html += '<th class="us-col">🇺🇸 미국 (USA)</th>'
    html += '<th class="jp-col">🇯🇵 일본 (JPN)</th>'
    html += '</tr></thead><tbody>'
    for label, us_val, jp_val in rows:
        html += f'<tr><td class="label-col">{label}</td>'
        html += f'<td class="us-col">{us_val}</td>'
        html += f'<td class="jp-col">{jp_val}</td></tr>'
    html += '</tbody></table>'
    return html


def render_market_bar_chart(research: dict):
    """시장 규모 비교 Bar Chart"""
    import re

    def _parse_value(v: str) -> float:
        """시장 규모 문자열 → USD billion 기준 float
        처리: $18.4B / ¥1.2T / 9,709억 엔 / 2.1조 엔 / €500M
        JPY 환산: 1 USD = 150 JPY
        """
        if not v:
            return 0
        v_clean = v.replace(",", "").strip()

        nums = re.findall(r"[\d.]+", v_clean)
        if not nums:
            return 0
        num = float(nums[0])

        # 한국/일본식 단위 (억, 조)
        is_jpy = "엔" in v_clean or "¥" in v_clean or "JPY" in v_clean.upper()
        if "조" in v_clean:
            num *= 1_000_000_000_000   # 조 = 1T
        elif "억" in v_clean:
            num *= 100_000_000          # 억 = 100M
        elif "T" in v_clean.upper():
            num *= 1_000_000_000_000
        elif "B" in v_clean.upper():
            num *= 1_000_000_000
        elif "M" in v_clean.upper():
            num *= 1_000_000

        # JPY → USD 환산 (1 USD ≈ 150 JPY)
        if is_jpy:
            num = num / 150

        # → USD billion 단위로 반환
        return num / 1_000_000_000

    data = []
    for code, label in [("US", "미국"), ("JP", "일본")]:
        r = research.get(code, {})
        ms = r.get("market_size", {})
        data.append({
            "국가": label,
            "시장 규모": _parse_value(ms.get("value", "0")),
            "원본": ms.get("value", "N/A"),
            "성장률": ms.get("growth_rate") or ms.get("cagr", ""),
        })

    df = pd.DataFrame(data)
    colors = {"미국": "#3b82f6", "일본": "#ec4899"}

    fig = go.Figure()
    for _, row in df.iterrows():
        label = f"{row['원본']}" + (f"  {row['성장률']}" if row['성장률'] else "")
        fig.add_trace(go.Bar(
            name=row["국가"],
            x=[row["국가"]],
            y=[row["시장 규모"]],
            marker_color=colors[row["국가"]],
            text=label,
            textposition="auto",
            textfont=dict(size=11, color="white"),
            insidetextanchor="middle",
        ))

    fig.update_layout(
        height=240,
        margin=dict(l=10, r=10, t=10, b=10),
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        xaxis=dict(showgrid=False, tickfont=dict(size=12)),
        bargap=0.35,
        uniformtext=dict(mode="hide", minsize=9),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_channel_donut(research: dict):
    """유통 채널 온/오프라인 비중 도넛 차트 (US 기준)"""
    us = research.get("US", {})
    ch = us.get("channels", {})
    online_ratio_str = ch.get("online_ratio", "")

    try:
        import re
        nums = re.findall(r"[\d.]+", online_ratio_str)
        online_pct = float(nums[0]) if nums else 65.0
    except Exception:
        online_pct = 65.0

    offline_pct = 100 - online_pct

    fig = go.Figure(go.Pie(
        labels=["온라인", "오프라인"],
        values=[online_pct, offline_pct],
        hole=0.65,
        marker=dict(colors=["#3b82f6", "#e5e7eb"]),
        textinfo="label+percent",
        textfont=dict(size=11),
        showlegend=False,
    ))
    fig.add_annotation(
        text=f"온라인<br><b>{online_pct:.0f}%</b>",
        x=0.5, y=0.5,
        font_size=13,
        showarrow=False,
    )
    fig.update_layout(
        height=240,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_trend_keywords(research: dict):
    """국가별 트렌드 키워드: 성분/제형/기능"""

    def _bar_html(items: list, us_list: list, jp_list: list) -> str:
        """항목별 미국(파랑)/일본(핑크) 듀얼 바 HTML 생성"""
        legend = """
        <div style='display:flex;gap:12px;margin-top:8px'>
            <span style='font-size:10px;color:#3b82f6'>■ 미국</span>
            <span style='font-size:10px;color:#ec4899'>■ 일본</span>
        </div>"""

        def _score(item, lst):
            if item not in lst:
                return 15
            idx = lst.index(item)
            return max(85 - idx * 10, 45)

        rows = ""
        for item in items:
            us_pct = _score(item, us_list)
            jp_pct = _score(item, jp_list)
            rows += f"""
            <div style="margin-bottom:12px">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
                    <span style="font-size:13px;font-weight:600;color:var(--text-color)">{item}</span>
                    <span style="font-size:10px;color:#9ca3af">USA {us_pct}% | JPN {jp_pct}%</span>
                </div>
                <div style="height:6px;border-radius:3px;background:rgba(128,128,128,0.15);margin-bottom:3px">
                    <div style="height:100%;width:{us_pct}%;background:#3b82f6;border-radius:3px"></div>
                </div>
                <div style="height:6px;border-radius:3px;background:rgba(128,128,128,0.15)">
                    <div style="height:100%;width:{jp_pct}%;background:#ec4899;border-radius:3px"></div>
                </div>
            </div>"""
        return rows + legend if rows else ""

    cols = st.columns(3)

    with cols[0]:
        st.markdown("**🧪 성분 트렌드**")
        for code, css_cls in [("US", "tag-us"), ("JP", "tag-jp")]:
            r = research.get(code, {})
            tr = r.get("trends", {})
            ingredients = tr.get("ingredients", [])
            label = "USA" if code == "US" else "JPN"
            if ingredients:
                st.markdown(f'<div class="tag-label">{label}</div>', unsafe_allow_html=True)
                tags = " ".join(f'<span class="{css_cls}">{i}</span>' for i in ingredients[:5])
                st.markdown(tags, unsafe_allow_html=True)
            _source_expander(tr.get("source_quote", ""), f"📄 {label} 트렌드 원문 근거")

    with cols[1]:
        st.markdown("**💧 제형 트렌드**")
        us_forms = research.get("US", {}).get("trends", {}).get("formulations", [])
        jp_forms = research.get("JP", {}).get("trends", {}).get("formulations", [])
        all_forms = list(dict.fromkeys(us_forms + jp_forms))[:5]
        html = _bar_html(all_forms, us_forms, jp_forms)
        if html:
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.caption("데이터 없음")

    with cols[2]:
        st.markdown("**✨ 기능 트렌드**")
        us_funcs = research.get("US", {}).get("trends", {}).get("functions", [])
        jp_funcs = research.get("JP", {}).get("trends", {}).get("functions", [])
        all_funcs = list(dict.fromkeys(us_funcs + jp_funcs))[:5]
        html = _bar_html(all_funcs, us_funcs, jp_funcs)
        if html:
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.caption("데이터 없음")


def render_channel_rankings(research: dict):
    """미국/일본 온라인 채널 순위 (K-뷰티 중심)"""

    def _parse_ch(ch_list: list) -> list:
        """string[] / dict[] 모두 {name, description} 형태로 정규화"""
        result = []
        for item in ch_list:
            if isinstance(item, dict) and item.get("name"):
                result.append({
                    "name": item.get("name", ""),
                    "description": item.get("description", ""),
                })
            elif isinstance(item, str) and item:
                result.append({"name": item, "description": ""})
        return result

    cols = st.columns(2)

    for idx, (code, label_detail) in enumerate([
        ("US", "🇺🇸 미국 온라인 채널 순위"),
        ("JP", "🇯🇵 일본 온라인 채널 순위"),
    ]):
        r = research.get(code, {})
        ch = r.get("channels", {})
        online_channels = _parse_ch(ch.get("online", []))
        offline_channels = _parse_ch(ch.get("offline", []))

        ch_details = ch.get("details", "")

        with cols[idx]:
            st.markdown(f"**{label_detail}**", unsafe_allow_html=True)
            if online_channels:
                html = ""
                for i, c in enumerate(online_channels[:5], 1):
                    rank_cls = "top" if i == 1 else ""
                    name = c["name"]
                    desc = c["description"] or "K-뷰티 주요 온라인 판매 채널"
                    html += f"""
                    <div class="rank-row">
                        <div class="rank-num {rank_cls}">{i}</div>
                        <div>
                            <div class="rank-name">{name}</div>
                            <div class="rank-desc">{desc}</div>
                        </div>
                    </div>"""
                if offline_channels:
                    html += '<div style="margin-top:10px;font-size:11px;color:#9ca3af;font-weight:700;letter-spacing:0.05em">오프라인</div>'
                    for c in offline_channels[:3]:
                        desc = c["description"] or "오프라인 판매 채널"
                        html += f"""
                        <div class="rank-row">
                            <div class="rank-num">•</div>
                            <div>
                                <div class="rank-name">{c["name"]}</div>
                                <div class="rank-desc">{desc}</div>
                            </div>
                        </div>"""
                st.markdown(html, unsafe_allow_html=True)
                if ch_details:
                    st.caption(ch_details)
                _source_expander(ch.get("source_quote", ""), "📄 채널 원문 근거")
            else:
                st.caption("채널 데이터 없음 — 딥리서치 재실행 필요")


def render_export_stats(stats: dict, category: str):
    """수출 통계 섹션"""
    COUNTRY_LABELS_SHORT = {"US": "미국", "JP": "일본"}
    plot_list = []
    for country, years_data in stats.items():
        for d in years_data:
            plot_list.append({
                "연도": d["year"],
                "수출액(USD)": d["amount"],
                "수출중량(kg)": d["weight"],
                "국가": COUNTRY_LABELS_SHORT.get(country, country),
            })

    df = pd.DataFrame(plot_list)
    if df.empty:
        st.warning("수출 통계 데이터가 없습니다.")
        return

    tab1, tab2 = st.tabs(["📈 수출 추이", "📋 상세 데이터"])

    with tab1:
        fig = px.line(
            df, x="연도", y="수출액(USD)", color="국가",
            markers=True,
            color_discrete_map={"미국": "#3b82f6", "일본": "#ec4899"},
            title=f"{category} 최근 5개년 수출 실적 ($)",
        )
        fig.update_layout(
            hovermode="x unified",
            height=300,
            margin=dict(l=0, r=0, t=40, b=0),
            plot_bgcolor="white",
            paper_bgcolor="white",
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with tab2:
        pivot = df.pivot(index="연도", columns="국가", values="수출액(USD)")
        st.dataframe(pivot, use_container_width=True)
        st.caption("※ 관세청 무역통계 API(TRASS) 기준")


# ============================================================
# 메인
# ============================================================
if page == "시장 & 트렌드":
    if not submit_btn:
        st.markdown("""
        <div style='text-align:center; padding: 80px 0; color:#9ca3af'>
            <div style='font-size:48px'>📊</div>
            <div style='font-size:18px;font-weight:600;color:#374151;margin-top:16px'>K-Beauty 시장 인텔리전스</div>
            <div style='font-size:14px;margin-top:8px'>사이드바에서 카테고리를 선택하고 분석을 실행하세요</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        with st.spinner(f'"{selected_category}" 분석 중...'):
            try:
                resp = requests.post(
                    f"{API_BASE}/match/",
                    json={"category": selected_category, "product_info": product_info},
                    timeout=120,
                )

                if resp.status_code != 200:
                    st.error(f"서버 오류 ({resp.status_code})")
                    st.json(resp.json())
                    st.stop()

                result = resp.json()
                research = result.get("research", {})
                stats = result.get("stats", {})
                hs_code = result.get("hs_code", "—")
                reason = result.get("reason", "")

                # HS 코드 표시
                c1, c2 = st.columns([1, 4])
                with c1:
                    st.markdown(f"""
                    <div class="card" style="text-align:center">
                        <div class="card-title">판정 HS 코드</div>
                        <div style="font-size:26px;font-weight:700;color:var(--text-color)">{hs_code}</div>
                    </div>""", unsafe_allow_html=True)
                with c2:
                    st.markdown(f"""
                    <div class="card">
                        <div class="card-title">분류 근거</div>
                        <div style="font-size:13px;color:var(--text-color)">{reason}</div>
                    </div>""", unsafe_allow_html=True)

                if not research:
                    st.warning("시장 리서치 데이터가 없습니다. `python manage.py ingest_research --deep-research` 를 먼저 실행해주세요.")
                else:
                    # research에 hs_code 주입 (비교 테이블용)
                    research["hs_code"] = hs_code

                    # 데이터 소스 배지
                    sources_info = []
                    for code in ["US", "JP"]:
                        r = research.get(code, {})
                        if r.get("data_source") == "estimated":
                            sources_info.append(f"{COUNTRY_SHORT[code]}: AI 추정")
                    if sources_info:
                        st.markdown(
                            f'<small style="color:#92400e">⚠️ 일부 수치 AI 추정값: {", ".join(sources_info)}</small>',
                            unsafe_allow_html=True
                        )

                    # ── 4개 KPI 카드 ──────────────────────────────
                    render_metric_cards(research)

                    # ── 3열 레이아웃: 비교표 | 바차트 | 도넛 ──────
                    col_table, col_bar, col_donut = st.columns([5, 3, 3])

                    with col_table:
                        st.markdown(f"""
                        <div class="card">
                            <div class="card-title">🏴 미국 vs 일본 핵심 요약</div>
                            {render_comparison_table_html(research)}
                        </div>""", unsafe_allow_html=True)

                    with col_bar:
                        with st.container(border=True):
                            st.markdown('<div class="card-title">📊 시장 규모 및 성장률</div>', unsafe_allow_html=True)
                            render_market_bar_chart(research)

                    with col_donut:
                        with st.container(border=True):
                            st.markdown('<div class="card-title">🛒 주요 유통 채널 점유율</div>', unsafe_allow_html=True)
                            render_channel_donut(research)

                    # ── 트렌드 키워드 ────────────────────────────
                    with st.container(border=True):
                        st.markdown('<div class="card-title" style="font-size:13px;margin-bottom:14px">국가별 트렌드 키워드 (미국 vs 일본)</div>', unsafe_allow_html=True)
                        render_trend_keywords(research)

                    # ── 채널별 인기 K-뷰티 제품 순위 ────────────
                    with st.container(border=True):
                        st.markdown('<div class="card-title" style="font-size:13px;margin-bottom:14px">채널별 인기 K-뷰티 제품 순위</div>', unsafe_allow_html=True)
                        render_channel_rankings(research)

                    # ── 경쟁 브랜드 (현지) ────────────────────────
                    with st.container(border=True):
                        st.markdown('<div class="card-title" style="font-size:13px;margin-bottom:14px">🏆 주요 경쟁 브랜드 (현지)</div>', unsafe_allow_html=True)
                        comp_cols = st.columns(2)
                        for cidx, (code, flag) in enumerate([("US", "🇺🇸"), ("JP", "🇯🇵")]):
                            r = research.get(code, {})
                            comps = r.get("competitors", {}).get("brands", [])
                            with comp_cols[cidx]:
                                st.markdown(f"**{flag} {COUNTRY_SHORT[code]} 주요 경쟁 브랜드**")
                                if comps:
                                    html = ""
                                    for i, b in enumerate(comps[:5], 1):
                                        rank_cls = "top" if i == 1 else ""
                                        html += f"""
                                        <div class="rank-row">
                                            <div class="rank-num {rank_cls}">{i}</div>
                                            <div>
                                                <div class="rank-name">{b.get('name', '')}</div>
                                                <div class="rank-desc">{b.get('description', '')}</div>
                                            </div>
                                        </div>"""
                                    st.markdown(html, unsafe_allow_html=True)
                                    _source_expander(
                                        r.get("competitors", {}).get("source_quote", ""),
                                        "📄 경쟁 브랜드 원문 근거"
                                    )
                                else:
                                    st.caption("데이터 없음")

                    # ── AI 요약 ───────────────────────────────────
                    for code, label in [("US", "🇺🇸 미국"), ("JP", "🇯🇵 일본")]:
                        r = research.get(code, {})
                        if r and r.get("summary"):
                            with st.expander(f"📝 {label} AI 종합 요약"):
                                st.write(r["summary"])
                                updated = r.get("updated_at", "")
                                if updated:
                                    st.caption(f"업데이트: {updated[:10]}")

                st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

                # ── 수출 통계 ────────────────────────────────
                with st.expander("📈 수출 통계 (TRASS 관세청)", expanded=bool(stats)):
                    if stats:
                        render_export_stats(stats, selected_category)
                    else:
                        st.warning("수출 통계 데이터가 없습니다.")

                # 출처
                all_sources = []
                for r in research.values():
                    if isinstance(r, dict):
                        all_sources.extend(r.get("sources", []))
                if all_sources:
                    with st.expander("📚 데이터 출처"):
                        for s in sorted(set(all_sources)):
                            st.markdown(f"- {s}")

            except requests.exceptions.ConnectionError:
                st.error("❌ Django 서버가 실행 중이 아닙니다. `python manage.py runserver` 확인")
            except Exception as e:
                st.error(f"❌ 오류 발생: {e}")
                st.exception(e)

elif page == "국가 수출 & 마케팅 전략":
    st.info("🚧 이 페이지는 준비 중입니다.")
