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


def _score_to_label(score: float, labels=("낮음", "보통", "높음"), thresholds=(40, 60)):
    palette = ("#ef4444", "#f59e0b", "#10b981")
    if score >= thresholds[1]:
        idx = 2
    elif score >= thresholds[0]:
        idx = 1
    else:
        idx = 0
    return labels[idx], palette[idx]


# ── render 함수들 ──────────────────────────────────────────────────────────────

def render_country_recommendation(result: dict):
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

    trend_label,  trend_color  = _score_to_label(detail.get("trend",  0))
    market_label, market_color = _score_to_label(detail.get("market", 0))
    review_label, review_color = _score_to_label(
        detail.get("review", 0),
        labels=("낮음", "중간", "높음"),
    )

    col_left, col_right = st.columns([3, 2])

    with col_left:
        with st.container(border=True):
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

            if rationale:
                short = rationale.split(".")[0] + "." if "." in rationale else rationale[:80]
                st.markdown(
                    f'<div style="font-size:13px;color:#6b7280;margin-bottom:16px;line-height:1.5">{short}</div>',
                    unsafe_allow_html=True,
                )

            k1, k2, k3 = st.columns(3)
            for col, label, val, color, title in [
                (k1, trend_label,  detail.get("trend",  0), trend_color,  "성분 적합도"),
                (k2, market_label, detail.get("market", 0), market_color, "시장 성장성"),
                (k3, review_label, detail.get("review", 0), review_color, "카테고리 친숙도"),
            ]:
                with col:
                    st.markdown(f"""
                    <div style="background:rgba(128,128,128,0.06);border-radius:10px;padding:12px 14px;text-align:center">
                        <div style="font-size:10px;color:#9ca3af;font-weight:700;margin-bottom:6px">{title}</div>
                        <div style="font-size:16px;font-weight:800;color:{color}">{label}</div>
                        <div style="font-size:10px;color:#9ca3af;margin-top:2px">{val:.0f}점</div>
                    </div>
                    """, unsafe_allow_html=True)

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
            st.markdown('<div class="panel-label">국가별 적합도 순위</div>', unsafe_allow_html=True)
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



def render_trade_and_channels(category: str, country: str, r: dict):
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
            st.markdown("**주요 채널**")
            st.markdown(
                '<div style="flex:1;display:flex;flex-direction:column;justify-content:space-around;padding:8px 0;min-height:220px">',
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
    st.markdown('<div class="section-header">성분 · 기능 트렌드</div>', unsafe_allow_html=True)
    tr = r.get("trends", {})

    ingredients = tr.get("ingredients", [])[:7]
    functions   = tr.get("functions", [])[:7]
    rising      = tr.get("rising_keywords", [])[:5]

    with st.container(border=True):
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
    for col, (platform, title, header_bg, title_color, accent) in zip([col1, col2], platforms):
        rows = data.get(platform, [])[:5]
        with col:
            rows_html = ""
            for r in rows:
                num   = r.get("rank", "")
                name  = r.get("title", "")[:55]
                brand = r.get("brand", "") or ""
                url   = r.get("url", "")
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
                  <th>RANK</th><th>PRODUCT NAME</th><th>BRAND</th>
                </tr></thead>
                <tbody>{rows_html}</tbody>
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

    html = (
        f'<div class="ad-strategy-outer">'
        f'<div class="ad-strategy-badge"><span class="badge-icon">⚡</span> AI 종합 마케팅 전략 제안</div>'
        f'<div class="ad-strategy-subtitle">{country_desc}</div>'
        f'<div class="ad-concept-box">'
        f'<div class="ad-strategy-concept">&ldquo;{concept}&rdquo;</div>'
        f'<div class="ad-strategy-reasoning">{reasoning}</div>'
        f'</div>'
        f'<div class="ad-section-headers">'
        f'<div class="ad-section-header-item"><div class="header-icon">💬</div> 핵심 상품 소구점</div>'
        f'<div class="ad-section-header-item"><div class="header-icon">🖼</div> 광고 시안 레퍼런스</div>'
        f'</div>'
        f'<div class="ad-cards-row">'
        f'<div class="ad-usp-card">{usp_items}</div>'
        f'{ref_cards}'
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
            updated   = str(ad.get("updated_at", ""))[:10]
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
                market  = "US" if ad["channel"] in ("ulta", "sephora") else "JP"
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

    # 우측 상단 국가 + 플랫폼 셀렉터
    _, col_sel = st.columns([7, 3])
    with col_sel:
        platform_names = [name for name, _ in platforms]
        selected_idx = 0
        if st.session_state[sk_platform] in platform_names:
            selected_idx = platform_names.index(st.session_state[sk_platform])
        platform_choice = st.selectbox(
            "플랫폼",
            platform_names,
            index=selected_idx,
            key=f"ri_sel_{country}",
            label_visibility="collapsed",
            format_func=lambda x: f"{COUNTRY_KO[country]}  ·  {x}",
        )

    platform = platform_choice
    rows = data.get(platform, [])

    with st.container(border=True):
        col_list, col_detail = st.columns([4, 10])

        with col_list:
            st.markdown(
                '<div class="panel-label" style="margin-bottom:6px">TOP 10 베스트셀러</div>',
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
                        args=(platform, row, item_id),
                    )

        with col_detail:
            if st.session_state[sk_platform] == platform and st.session_state[sk_item]:
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
