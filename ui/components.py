import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

API_BASE = "http://127.0.0.1:8000/api"

COUNTRY_KO    = {"US": "미국 (USA)", "JP": "일본 (Japan)"}
COUNTRY_SHORT = {"US": "미국", "JP": "일본"}


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────

def _parse_channel_list(ch_list):
    result = []
    for item in ch_list:
        if isinstance(item, dict) and item.get("name"):
            result.append({"name": item["name"], "description": item.get("description", "")})
        elif isinstance(item, str) and item:
            result.append({"name": item, "description": ""})
    return result


def _tags_html(items: list, cls: str) -> str:
    if not items:
        return ""
    return " ".join(f'<span class="{cls}">{item}</span>' for item in items)


_EN_MAP = {"낮음": "Low", "보통": "Moderate", "높음": "High", "중간": "Medium"}

def _score_to_label(score: float, labels=("낮음", "보통", "높음"), thresholds=(40, 60)):
    palette = ("#ef4444", "#f59e0b", "#10b981")
    if score >= thresholds[1]:
        idx = 2
    elif score >= thresholds[0]:
        idx = 1
    else:
        idx = 0
    ko = labels[idx]
    en = _EN_MAP.get(ko, ko)
    return f"{ko} ({en})", palette[idx]


# ── render 함수들 ──────────────────────────────────────────────────────────────

def render_country_recommendation(result: dict, selected_country: str = "US"):
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
    score_color  = "#8271FF"

    trend_label,  trend_color  = _score_to_label(detail.get("trend",  0))
    market_label, market_color = _score_to_label(detail.get("market", 0))
    review_label, review_color = _score_to_label(
        detail.get("review", 0),
        labels=("낮음", "중간", "높음"),
    )

    if rationale:
        short = rationale.split(".")[0] + "." if "." in rationale else rationale[:80]
    else:
        short = ""

    matched = top.get("trend_matched", [])
    tag_cls = "tag-us" if top_country == "US" else "tag-jp"
    matched_html = ""
    if matched:
        tags = " ".join(f'<span class="{tag_cls}">{k}</span>' for k in matched)
        matched_html = f'<div class="tag-label" style="margin-top:14px;margin-bottom:6px">트렌드 매칭</div><div style="padding-bottom:8px">{tags}</div>'

    st.markdown("""
    <style>
    [data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"])
        > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] {
        align-items: stretch;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"])
        > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]
        > [data-testid="stColumn"]:last-child { display: flex; flex-direction: column; }
    [data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"])
        > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]
        > [data-testid="stColumn"]:last-child > div { flex: 1; display: flex; flex-direction: column; }
    [data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"])
        > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]
        > [data-testid="stColumn"]:last-child > div > [data-testid="stVerticalBlock"] { flex: 1; display: flex; flex-direction: column; }
    [data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"])
        > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]
        > [data-testid="stColumn"]:last-child > div > [data-testid="stVerticalBlock"]
        > [data-testid="stVerticalBlockBorderWrapper"] { flex: 1; }
    </style>
    """, unsafe_allow_html=True)

    with st.container(border=True):
      col_left, col_right = st.columns([3, 2], gap="large")

      with col_left:
        with st.container(border=False):
            st.markdown(f"""
            <div style="display:inline-block;font-size:11px;font-weight:700;color:#8271FF;
                        border:1.5px solid #8271FF;border-radius:20px;padding:2px 10px;margin-bottom:12px;letter-spacing:.04em">
                최적 시장 추천
            </div>
            <div style="display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:10px">
                <div style="font-size:28px;font-weight:800;color:var(--text-color);line-height:1.2">
                    {country_name}
                </div>
                <div style="text-align:right;line-height:1">
                    <span style="font-size:40px;font-weight:800;color:{score_color}">{score}</span>
                    <span style="font-size:13px;color:#9ca3af;font-weight:600">/100</span>
                    <div style="font-size:10px;color:#9ca3af;font-weight:600;letter-spacing:.06em">AI SCORE</div>
                </div>
            </div>
            <div style="font-size:13px;color:#6b7280;line-height:1.5;margin-bottom:16px">{short}</div>
            {matched_html}
            <div style="display:flex;gap:10px;margin-top:16px;padding-bottom:4px">
                <div style="flex:1;border:none;border-radius:10px;padding:14px 8px;text-align:center">
                    <div style="font-size:10px;color:#9ca3af;font-weight:700;margin-bottom:6px">성분 적합도</div>
                    <div style="font-size:15px;font-weight:800;color:{trend_color}">{trend_label}</div>
                </div>
                <div style="flex:1;border:none;border-radius:10px;padding:14px 8px;text-align:center">
                    <div style="font-size:10px;color:#9ca3af;font-weight:700;margin-bottom:6px">시장 성장성</div>
                    <div style="font-size:15px;font-weight:800;color:{market_color}">{market_label}</div>
                </div>
                <div style="flex:1;border:none;border-radius:10px;padding:14px 8px;text-align:center">
                    <div style="font-size:10px;color:#9ca3af;font-weight:700;margin-bottom:6px">카테고리 친숙도</div>
                    <div style="font-size:15px;font-weight:800;color:{review_color}">{review_label}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

      with col_right:
        with st.container(border=False):
            st.markdown('<div style="font-size:18px;font-weight:700;color:var(--text-color);margin-bottom:20px;padding-top:4px;margin-top:20px">국가별 적합도 순위</div>', unsafe_allow_html=True)
            for i, c in enumerate(countries, 1):
                c_name    = {"US": "미국 (USA)", "JP": "일본 (Japan)"}.get(c["country"], c["country"])
                c_score   = c["score"]
                c_color   = "#8271FF" if c_score >= 60 else "#9ca3af"
                reasoning = (c.get("trend_reasoning") or "")[:40]
                is_selected = c["country"] == selected_country
                is_top      = c["country"] == top_country
                circle_bg     = "#8271FF" if is_selected else "transparent"
                circle_border = "#8271FF" if is_selected else "#d1d5db"
                circle_color  = "#fff" if is_selected else "#9ca3af"
                row_bg        = "rgba(130,113,255,0.08)" if is_selected else "transparent"
                row_border    = "1.5px solid rgba(130,113,255,0.35)" if is_selected else "1.5px solid transparent"
                ai_badge      = '<span style="font-size:10px;font-weight:700;color:#8271FF;background:rgba(130,113,255,0.12);border-radius:4px;padding:2px 6px;margin-left:6px">AI 추천</span>' if is_top else ""
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:14px;padding:20px 12px;
                            border-radius:10px;margin-bottom:10px;background:{row_bg};
                            border:{row_border};cursor:pointer;pointer-events:none;transition:all 0.15s">
                    <div style="width:34px;height:34px;border-radius:50%;background:{circle_bg};
                                border:2px solid {circle_border};display:flex;align-items:center;
                                justify-content:center;font-size:15px;font-weight:800;color:{circle_color};flex-shrink:0">
                        {i}
                    </div>
                    <div style="flex:1;min-width:0">
                        <div style="font-size:16px;font-weight:700;color:var(--text-color)">{c_name}{ai_badge}</div>
                        <div style="font-size:12px;color:#9ca3af;margin-top:4px;white-space:nowrap;
                                    overflow:hidden;text-overflow:ellipsis">{reasoning}</div>
                    </div>
                    <div style="font-size:24px;font-weight:800;color:{c_color};flex-shrink:0">
                        {c_score}<span style="font-size:12px;color:#9ca3af">점</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("　", key=f"btn_country_{c['country']}", use_container_width=True):
                    st.session_state.selected_country = c["country"]
                    st.rerun()



def render_trade_and_channels(category: str, country: str, r: dict):
    CHART_H = 200

    with st.container(border=True):
        col1, col2 = st.columns(2)

        with col1:
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
                    
                    if stats:
                        df = pd.DataFrame(stats)
                        df["amount_M"] = (df["amount"] / 1_000_000).round(1)
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=df["year"],
                            y=df["amount_M"],
                            mode="lines+markers",
                            line=dict(color="#8271FF", width=4),
                            marker=dict(color="#8271FF", size=6),
                        ))
                        fig.update_layout(
                            margin=dict(t=10, b=10, l=0, r=10),
                            height=CHART_H,
                            plot_bgcolor="rgba(0,0,0,0)",
                            paper_bgcolor="rgba(0,0,0,0)",
                            yaxis=dict(gridcolor="rgba(128,128,128,0.15)", zeroline=False, showline=False, tickfont=dict(size=10)),
                            xaxis=dict(type="category", tickmode="array", tickvals=df["year"].tolist(), showgrid=False, tickfont=dict(size=10)),
                            showlegend=False,
                        )
                        st.plotly_chart(fig, use_container_width=True)

                    else:
                        st.caption("수출 통계 데이터 없음")
                else:
                    st.caption("수출 데이터를 불러올 수 없습니다.")
            except Exception as e:
                st.caption(f"수출 데이터 오류: {e}")

        with col2:
            st.markdown("**주요 채널**")
            st.markdown(
                '<div style="display:flex;flex-direction:column;gap:8px;padding:4px 0">',
                unsafe_allow_html=True,
            )
            ch = r.get("channels", {})
            list  = _parse_channel_list(ch.get("channels", []))
            top3 = (list)[:3]
            if top3:
                html = ""
                for i, c in enumerate(top3, 1):
                    rank_cls = "top" if i == 1 else ""
                    html += f"""<div class="rank-row">
                        <div class="rank-num {rank_cls}">{i}</div>
                        <div>
                            <div class="rank-name">{c['name']}</div>
                            <div class="rank-desc">{c['description'][:100] if c['description'] else ''}</div>
                        </div></div>"""
                st.markdown(html, unsafe_allow_html=True)
            else:
                st.caption("채널 데이터 없음")
            st.markdown("</div>", unsafe_allow_html=True)


def render_kpi_row(r: dict, country: str):
    ms = r.get("market_size", {})
    ch = r.get("channels", {})

    value   = ms.get("value") or "N/A"
    cagr    = ms.get("cagr") or ms.get("growth_rate") or "N/A"
    f_year  = ms.get("forecast_year") or ""
    _online_first = ch.get("online", [None])[0] if ch.get("online") else None
    key_platform  = ch.get("key_platform") or (
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
        forecast_label = f"2024 - {f_year} 예측" if f_year else "연평균 성장률"
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
    tr = r.get("trends", {})

    ingredients = tr.get("ingredients", [])[:7]
    functions   = tr.get("functions", [])[:7]
    rising      = tr.get("rising_keywords", [])[:5]

    with st.container(border=True):
        st.markdown('**성분 · 기능 · 부상 트렌드**', unsafe_allow_html=True)
        parts = []
        parts += [f'<span class="tag-ingredient">{item}</span>' for item in ingredients]
        parts += [f'<span class="tag-function">{item}</span>' for item in functions]
        parts += [f'<span class="tag-rising">{item}</span>' for item in rising]
        if parts:
            st.markdown(" ".join(parts), unsafe_allow_html=True)
        else:
            st.caption("데이터 없음")


def render_competitors_section(r: dict, country: str):
    st.markdown(f'<div class="section-header">주요 경쟁 브랜드 ({COUNTRY_KO[country]})</div>', unsafe_allow_html=True)
    comp    = r.get("competitors", {})
    brands  = comp.get("brands", [])
    kbeauty = comp.get("kbeauty_brands", [])

    col1, col2 = st.columns([3, 2])
    with col1:
        with st.container(border=True):
            st.markdown("**경쟁 브랜드 순위**")
            if brands:
                html = ""
                for i, b in enumerate(brands[:6], 1):
                    rank_cls  = "top" if i == 1 else ""
                    share     = b.get("market_share", "")
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

            leader       = comp.get("market_leader", "")
            leader_share = comp.get("market_leader_share", "")
            if leader:
                st.markdown("---")
                st.markdown(f"**시장 1위:** {leader}" + (f" ({leader_share})" if leader_share else ""))


def render_kbeauty_share_section(r: dict, country: str):
    ks = r.get("kbeauty_share", {})
    if not ks:
        return

    share      = ks.get("share", "")
    rank       = ks.get("rank", "")
    export_val = ks.get("export_value", "")
    yoy        = ks.get("yoy_growth", "")
    competing  = ks.get("competing_countries", [])
    details    = ks.get("details", "")

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
    try:
        resp = requests.get(f"{API_BASE}/rankings/", params={"country": country}, timeout=10)
        if resp.status_code != 200:
            st.caption("랭킹 데이터를 불러올 수 없습니다.")
            return
        data = resp.json().get("rankings", {})
    except Exception:
        st.caption("랭킹 서버 연결 실패.")
        return

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
    for col, (platform, title, header_bg, title_color, _) in zip([col1, col2], platforms):
        rows = data.get(platform, [])[:5]
        with col:
            rows_html = ""
            for idx, r in enumerate(rows):
                num   = r.get("rank", "")
                name  = r.get("title", "")[:55]
                brand = r.get("brand", "") or ""
                url   = r.get("url", "")
                border_top = "border-top:1px solid rgba(128,128,128,0.1);" if idx > 0 else ""
                name_html = (
                    f'<a href="{url}" target="_blank" style="color:var(--text-color);text-decoration:none;"'
                    f' onmouseover="this.style.textDecoration=\'underline\'" onmouseout="this.style.textDecoration=\'none\'">'
                    f'{name}</a>'
                    if url else f'<span>{name}</span>'
                )
                rows_html += f"""
                <tr style="{border_top}">
                  <td style="font-size:15px;font-weight:700;color:#374151;width:48px">{num:02d}</td>
                  <td style="font-size:14px;color:var(--text-color)">{name_html}</td>
                  <td style="font-size:13px;color:#9ca3af;white-space:nowrap">{brand}</td>
                </tr>"""

            st.markdown(f"""
            <div style="border:1px solid rgba(128,128,128,0.2);border-radius:12px;overflow:hidden">
              <div style="background:{header_bg};padding:14px 20px 12px;border-bottom:1px solid rgba(128,128,128,0.15)">
                <span style="font-size:16px;font-weight:700;color:{title_color}">{title}</span>
              </div>
              <table style="width:100%;border-collapse:collapse;padding:0 8px">
                <thead><tr style="border-bottom:1px solid rgba(128,128,128,0.15)">
                  <th style="font-size:10px;font-weight:700;color:#9ca3af;letter-spacing:.08em;padding:10px 20px 8px;text-align:left;width:48px">RANK</th>
                  <th style="font-size:10px;font-weight:700;color:#9ca3af;letter-spacing:.08em;padding:10px 20px 8px;text-align:left">PRODUCT NAME</th>
                  <th style="font-size:10px;font-weight:700;color:#9ca3af;letter-spacing:.08em;padding:10px 20px 8px;text-align:left">BRAND</th>
                </tr></thead>
                <tbody style="padding:0 12px">{rows_html}</tbody>
              </table>
            </div>""", unsafe_allow_html=True)


def render_review_analysis(platform: str, item: dict):
    item_id = item.get("platform_item_id", "")
    title   = item.get("title", "")
    rank    = item.get("rank", "")

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

    total_rating            = d.get("total_rating")
    review_count            = d.get("review_count", 0)
    sentiment               = d.get("sentiment", {})
    category_scores         = d.get("category_scores", [])
    top_keywords            = d.get("top_keywords", [])
    sample_reviews          = d.get("sample_reviews", {})
    complaints              = d.get("complaints", [])
    opportunities           = d.get("opportunities", [])

    # ── 헤더: 제품명 + 만족도 뱃지 ──
    st.markdown(f"""
    <div class="rv-header">
        <div>
            <div class="rv-label">선택 제품 리뷰 분석</div>
            <div class="rv-title">{title}&nbsp;&nbsp;<span class="rv-platform">({platform} #{rank})</span></div>
            <div class="rv-sub">최근 2년 기준 {review_count:,}건</div>
        </div>
        <div class="rv-badge">
            <div class="rv-badge-label">전체 만족도</div>
            <div class="rv-badge-score">{total_rating}<span class="rv-badge-denom"> / 5.0</span></div>
        </div>
    </div>""", unsafe_allow_html=True)

    # ── 카테고리 만족도 + 감성 도넛 ──
    col_left, col_right = st.columns([5, 3])

    with col_left:
        st.markdown('<div class="rv-section-label">카테고리별 만족도 (CATEGORY SATISFACTION)</div>', unsafe_allow_html=True)
        for cs in category_scores[:6]:
            score    = cs["score"]
            count    = cs.get("count", "")
            fill_pct = int(score / 5 * 100)
            count_html = f'<span style="font-size:11px;color:#9ca3af;font-weight:400">({count}건)</span>' if count else ""
            st.markdown(f"""
            <div class="rv-bar-wrap">
                <div class="rv-bar-label">
                    <span>{cs['category']}</span>
                    <span><span class="rv-bar-score">{score}</span> {count_html}</span>
                </div>
                <div class="rv-bar-bg"><div class="rv-bar-fill" style="width:{fill_pct}%"></div></div>
            </div>""", unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="rv-section-label">긍부정 감성 비율 (SENTIMENT RATIO)</div>', unsafe_allow_html=True)
        pos_pct = sentiment.get("positive", 0)
        neg_pct = sentiment.get("negative", 0)
        fig = go.Figure(go.Pie(
            values=[pos_pct, neg_pct],
            labels=["긍정", "부정"],
            hole=0.65,
            marker_colors=["#7c3aed", "#e5e7eb"],
            textinfo="none",
            hoverinfo="label+percent",
        ))
        fig.update_layout(
            margin=dict(t=0, b=0, l=0, r=0),
            height=150,
            showlegend=False,
            annotations=[dict(
                text=f"<b>{pos_pct}%</b><br><span style='font-size:10px'>POSITIVE</span>",
                x=0.5, y=0.5, font_size=16, showarrow=False,
            )],
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown(f"""
        <div style="text-align:center;font-size:12px;margin-top:-10px">
            <span style="color:#7c3aed;font-weight:600">● 긍정 {pos_pct}%</span>&nbsp;&nbsp;
            <span style="color:#9ca3af">◎ 부정 {neg_pct}%</span>
        </div>""", unsafe_allow_html=True)

    # ── 핵심 키워드 ──
    if top_keywords:
        st.markdown('<div class="rv-section-label" style="margin-top:12px">핵심 키워드 (KEY KEYWORDS)</div>', unsafe_allow_html=True)
        tags_html = " ".join(
            f'<span class="rv-kw">{kw}</span>' if i < 4 else f'<span class="rv-kw-gray">{kw}</span>'
            for i, kw in enumerate(top_keywords)
        )
        st.markdown(tags_html, unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── 리뷰 요약 카드 ──
    col_p, col_neg = st.columns(2)
    with col_p:
        pos_text = sample_reviews.get("positive") or "데이터 없음"
        st.markdown(f"""
        <div class="rv-review-card pos">
            <div class="rv-review-card-label pos">👍 긍정 리뷰 요약 (Positive)</div>
            <div class="rv-review-card-text">"{pos_text}"</div>
        </div>""", unsafe_allow_html=True)
    with col_neg:
        neg_text = sample_reviews.get("negative") or "데이터 없음"
        st.markdown(f"""
        <div class="rv-review-card neg">
            <div class="rv-review-card-label neg">👎 부정 리뷰 요약 (Negative)</div>
            <div class="rv-review-card-text">"{neg_text}"</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Complaints + Opportunities ──
    if complaints or opportunities:
        col_c, col_o = st.columns(2)
        with col_c:
            if complaints:
                st.markdown('<div class="rv-section-title red">COMPLAINTS (주요 불만 사항)</div>', unsafe_allow_html=True)
                for c in complaints:
                    st.markdown(f"""
                    <div class="rv-complaint-row">
                        <span class="rv-complaint-label">{c['label']}</span>
                        <div class="rv-complaint-bar-bg"><div class="rv-complaint-bar-fill" style="width:{c['pct']}%"></div></div>
                        <span class="rv-complaint-pct">{c['pct']}%</span>
                    </div>""", unsafe_allow_html=True)
        with col_o:
            if opportunities:
                st.markdown('<div class="rv-section-title green">OPPORTUNITIES (시장 기회)</div>', unsafe_allow_html=True)
                for op in opportunities:
                    t    = op.get('title', '')
                    desc = op.get('description', '') or op.get('summary', '')
                    st.markdown(
                        f'<div class="rv-opp-item">✓ <b style="color:#10b981">{t}</b>: {desc}</div>',
                        unsafe_allow_html=True)


def render_ad_strategy(result: dict, ad_images: list = None, image_generating: bool = False):
    """
    result          : ad-strategy API 응답
    ad_images       : [{"data": base64, "mime_type": "image/png"}, ...] (없으면 placeholder)
    image_generating: True면 이미지 생성 중 애니메이션 표시
    """
    if not result or "error" in result:
        st.info(result.get("error", "마케팅 전략 데이터를 생성할 수 없습니다."))
        return

    country = result.get("country", "US")
    country_desc = {
        "US": "미국 시장 진출을 위한 고도화된 타겟팅 및 컨셉 전략",
        "JP": "일본 시장 진출을 위한 고도화된 타겟팅 및 컨셉 전략",
    }.get(country, "")
    concept   = result.get("brand_concept", "")
    reasoning = result.get("concept_reasoning", "")
    messages  = result.get("key_messages", [])
    ad_copies = result.get("ad_copies", [])
    if not ad_copies and result.get("headline"):
        ad_copies = [{"headline": result["headline"], "body_text": result.get("body_text", "")}]

    usp_items = "".join(
        f'<div class="ad-usp-item">'
        f'<div class="ad-usp-check">✔</div>'
        f'<div class="ad-usp-text">{m}</div>'
        f'</div>'
        for m in messages
    )

    ref_cards = ""
    for i, copy in enumerate(ad_copies[:2]):
        h = copy.get("headline", "")
        b = copy.get("body_text", "")

        # 생성된 이미지가 있으면 표시, 생성 중이면 애니메이션, 없으면 placeholder
        img_data = (ad_images or [])[i] if ad_images and i < len(ad_images) else None
        if img_data and "data" in img_data:
            mime = img_data.get("mime_type", "image/png")
            if i == 1:
                # 2번째: 9:16 세로 이미지 — 높이 고정, 양옆 공백 허용
                img_html = (
                    f'<img src="data:{mime};base64,{img_data["data"]}" '
                    f'style="width:100%;height:300px;object-fit:contain;background:#f8f8f8;" />'
                )
            else:
                # 1번째: 1:1 피드 이미지
                img_html = (
                    f'<img src="data:{mime};base64,{img_data["data"]}" '
                    f'style="width:100%;height:300px;object-fit:contain;background:#f8f8f8;" />'
                )
        elif image_generating:
            img_html = (
                '<div class="ad-ref-img">'
                '<div class="img-spinner"></div>'
                '<div style="color:#9ca3af;font-size:13px;">광고 이미지 생성 중...</div>'
                '</div>'
            )
        else:
            img_html = '<div class="ad-ref-img"></div>'

        ref_cards += (
            f'<div class="ad-ref-card">'
            f'{img_html}'
            f'<div class="ad-ref-content">'
            f'<div class="ad-ref-label">HEADLINE</div>'
            f'<div class="ad-ref-headline">&ldquo;{h}&rdquo;</div>'
            f'<div class="ad-ref-label">BODY COPY</div>'
            f'<div class="ad-ref-body">{b}</div>'
            f'</div>'
            f'</div>'
        )

    st.markdown(
        f'<div class="ad-strategy-outer">'
        f'<div class="ad-strategy-badge">'
        f'<div class="badge-icon-box">'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="#a78bfa" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>'
        f'</div>'
        f'<div>'
        f'<div class="badge-title">AI 종합 마케팅 전략 제안</div>'
        f'<div class="badge-subtitle">{country_desc}</div>'
        f'</div>'
        f'</div>'
        f'<div class="ad-concept-box">'
        f'<div class="ad-strategy-concept">&ldquo;{concept}&rdquo;</div>'
        f'<div class="ad-strategy-reasoning">{reasoning}</div>'
        f'</div>'
        f'<div class="ad-cards-row">'
        f'<div class="ad-col-usp">'
        f'<div class="ad-section-header-item">'
        f'<div class="header-icon-box"><svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="#a78bfa" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/></svg></div>'
        f' 핵심 상품 소구점</div>'
        f'<div class="ad-usp-card">{usp_items}</div>'
        f'</div>'
        f'<div class="ad-col-refs">'
        f'<div class="ad-section-header-item">'
        f'<div class="header-icon-box"><svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="#a78bfa" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg></div>'
        f' 광고 시안 레퍼런스</div>'
        f'<div class="ad-ref-cards-inner">{ref_cards}</div>'
        f'</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


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

        last_updated = str(ads[0].get("updated_at", ""))[:10].replace("-", ".")

        with st.container(border=True):
            st.markdown(f"""
            <div class="mon-header">
              <div class="mon-title">Meta 광고 모니터링</div>
              <div class="mon-updated">마지막 업데이트: {last_updated}</div>
            </div>
            """, unsafe_allow_html=True)

            cols = st.columns(len(ads))
            for col, ad in zip(cols, ads):
                copy_text = ad.get("latest_ad_text", "") or "—"
                if len(copy_text) > 60:
                    copy_text = copy_text[:60] + "..."
                brand_name = ad["brand"]
                total_ads  = ad["total_ads"]
                count_str  = f"{total_ads}개 이상" if total_ads >= 200 else f"{total_ads}개"

                page_id = ad.get("page_id", "")
                market  = "US" if ad["channel"] in ("ulta", "sephora") else "JP"
                link_html = ""
                if page_id:
                    ad_url = (
                        f"https://www.facebook.com/ads/library/"
                        f"?active_status=active&ad_type=all&country={market}"
                        f"&media_type=all&search_type=page&view_all_page_id={page_id}"
                    )
                    link_html = f'<a class="mon-link" href="{ad_url}" target="_blank">Meta 광고 보기 →</a>'

                with col:
                    st.markdown(f"""
                    <div class="mon-card">
                      <div class="mon-brand-name">{brand_name}</div>
                      <div class="mon-count-row">
                        <span class="mon-count-label">활성 광고수</span>
                        <span class="mon-count-value">{count_str}</span>
                      </div>
                      <div class="mon-copy-label">최근 광고 카피</div>
                      <div class="mon-copy-text">"{copy_text}"</div>
                      {link_html}
                    </div>
                    """, unsafe_allow_html=True)
            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Meta 광고 섹션 오류: {e}")


@st.fragment
def render_top10_rankings(country: str):
    try:
        resp = requests.get(f"{API_BASE}/rankings/", params={"country": country}, timeout=10)
        if resp.status_code != 200:
            st.caption("랭킹 데이터를 불러올 수 없습니다.")
            return
        data = resp.json().get("rankings", {})
    except Exception:
        st.caption("랭킹 서버 연결 실패.")
        return

    if country == "US":
        platforms = [("Ulta", "Ulta Beauty"), ("Sephora", "Sephora")]
    else:
        platforms = [("Qoo10", "Qoo10"), ("Rakuten", "Rakuten")]

    platform_names = [name for name, _ in platforms]

    with st.container(border=True):
        tabs = st.tabs(platform_names)

        for tab, (platform, _) in zip(tabs, platforms):
            sk_item    = f"ri_item_{country}_{platform}"
            sk_item_id = f"ri_item_id_{country}_{platform}"

            if sk_item not in st.session_state:
                st.session_state[sk_item]    = None
                st.session_state[sk_item_id] = None

            def _select(row, item_id, _sk_item=sk_item, _sk_item_id=sk_item_id):
                st.session_state[_sk_item]    = row
                st.session_state[_sk_item_id] = item_id

            with tab:
                rows = data.get(platform, [])
                # 플랫폼별 최초 1회만 1위 자동 선택
                if rows and st.session_state[sk_item] is None:
                    st.session_state[sk_item]    = rows[0]
                    st.session_state[sk_item_id] = rows[0].get("platform_item_id", "")

                col_list, col_detail = st.columns([4, 10])

                with col_list:
                    st.markdown(
                        '<div class="panel-label" style="margin-bottom:6px">TOP 10 베스트셀러</div>',
                        unsafe_allow_html=True,
                    )
                    for row in rows:
                        num     = row.get("rank", 0)
                        name    = row.get("title", "")
                        item_id = row.get("platform_item_id", "")
                        is_selected = st.session_state[sk_item_id] == item_id
                        display_name = name[:100] + ("..." if len(name) > 25 else "")
                        sub_text = f"{platform} #{num}"
                        sel_cls = "selected" if is_selected else ""
                        arrow = '<div class="rank-arrow">›</div>' if is_selected else ""

                        with st.container():
                            st.markdown(f"""
                            <div class="rank-item {sel_cls}">
                                <div class="rank-num">{num:02d}</div>
                                <div class="rank-info">
                                    <div class="rank-name">{display_name}</div>
                                    <div class="rank-sub">{sub_text}</div>
                                </div>
                                {arrow}
                            </div>""", unsafe_allow_html=True)
                            st.button(
                                " ",
                                key=f"ri_{country}_{platform}_{item_id}",
                                use_container_width=True,
                                on_click=_select,
                                args=(row, item_id),
                            )

                with col_detail:
                    if st.session_state[sk_item]:
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
