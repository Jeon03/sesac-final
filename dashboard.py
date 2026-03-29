import streamlit as st
import requests

from ui.styles import STYLES
from ui.components import (
    render_country_recommendation,
    render_trade_and_channels,
    render_kpi_row,
    render_trends_section,
    render_kbeauty_share_section,
    render_top5_rankings,
    render_meta_ads_section,
    render_top10_rankings,
    render_ad_strategy,
    COUNTRY_KO,
)
from ui.report import generate_report_pdf

st.set_page_config(
    page_title="Global Beauty Insight",
    page_icon="G",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(STYLES, unsafe_allow_html=True)

API_BASE = "http://127.0.0.1:8000/api"

CATEGORY_LIST = ["스킨케어"]

INGREDIENT_LIST = [
    "히알루론산", "글리세린", "레티놀", "나이아신아마이드", "펩타이드", "아데노신",
    "알부틴", "트라넥삼산", "AHA", "BHA", "비타민 C",
    "세라마이드", "판테놀", "시카", "발효추출물", "병풀추출물",
    "스피큘", "PDRN", "마데카소사이드", "바쿠치올",
]

EFFECT_LIST = [
    "수분", "재생", "미백", "각질", "항산화",
    "장벽", "진정", "피지", "기능성", "주름 개선", "결 개선",
]

# ── 세션 스테이트 초기화 ───────────────────────────────────────────────────────
for _k, _v in {
    "cache_key":           None,
    "rec_data":            None,
    "top_country":         "US",
    "selected_country":    "US",
    "research":            None,
    "strategy_data":       None,
    "strategy_attempted":  False,
    "ad_images":           None,
    "review_summary":      None,
    "report_pdf":          None,
    "_img_bytes":          None,
    "_img_name":           None,
    "_img_type":           None,
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── 현재 탭 (session state) ────────────────────────────────────────────────────
if "current_tab" not in st.session_state:
    st.session_state.current_tab = "market"
current_tab = st.session_state.current_tab
has_data    = bool(st.session_state.cache_key)

# ── 고정 헤더 (로고만 HTML, nav는 아래 Streamlit 버튼으로) ────────────────────
st.markdown("""
<div class="fixed-header">
    <div class="fh-logo">
        <div class="fh-logo-icon">V</div>
        <span class="fh-logo-text">VORA</span>
    </div>
</div>
""", unsafe_allow_html=True)

# nav 버튼 — CSS로 고정 헤더 안에 위치 (position: fixed via .st-key-nav_*)
_nav_disabled = not has_data
if st.button("시장 분석",    key="nav_market",   type="primary" if current_tab == "market"   else "secondary", disabled=_nav_disabled):
    st.session_state.current_tab = "market";   st.rerun()
if st.button("리뷰 인사이트", key="nav_review",   type="primary" if current_tab == "review"   else "secondary", disabled=_nav_disabled):
    st.session_state.current_tab = "review";   st.rerun()
if st.button("마케팅 전략",   key="nav_strategy", type="primary" if current_tab == "strategy" else "secondary", disabled=_nav_disabled):
    st.session_state.current_tab = "strategy"; st.rerun()


# ── 초기 상태: 히어로 + 폼 중앙 배치 ─────────────────────────────────────────
if not st.session_state.cache_key:
    st.markdown("<div style='height:18vh'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align:center; padding-bottom:32px;">
        <div style="font-size:42px; font-weight:800; letter-spacing:-1px;
                    background:linear-gradient(135deg,#6366f1,#8b5cf6);
                    -webkit-background-clip:text; -webkit-text-fill-color:transparent;">
            VORA
        </div>
        <div style="font-size:15px; color:#9ca3af; margin-top:8px; font-weight:500;">
            K-뷰티 글로벌 진출 AI 분석 플랫폼
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── 제품 정보 입력 폼 ──────────────────────────────────────────────────────────
with st.container(border=True):
    st.markdown("""
    <div class="input-card-header">
      <div>
        <div class="input-card-title">제품 정보 입력</div>
        <div class="input-card-subtitle">분석하고자 하는 제품의 상세 정보를 입력해주세요.</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    col_inputs, col_right = st.columns([2, 1])

    with col_inputs:
        # 행 1: 카테고리 + 제품명
        row1_a, row1_b = st.columns([1, 1])
        with row1_a:
            st.markdown('<div class="input-field-label">카테고리 <span class="required">*</span></div>', unsafe_allow_html=True)
            selected_category = st.selectbox("카테고리", CATEGORY_LIST, label_visibility="collapsed")
        with row1_b:
            st.markdown('<div class="input-field-label">제품명 <span class="required">*</span></div>', unsafe_allow_html=True)
            product_name = st.text_input("제품명", placeholder="예: 울트라 페이셜 크림", label_visibility="collapsed")

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        # 행 2: 주요 성분 + 핵심 효능
        row2_a, row2_b = st.columns([1, 1])
        with row2_a:
            st.markdown('<div class="input-field-label">주요 성분</div>', unsafe_allow_html=True)
            selected_ingredients = st.multiselect("주요 성분", INGREDIENT_LIST,
                                                  placeholder="예: 병풀 추출물, 판테놀, 히알루론산",
                                                  label_visibility="collapsed")
        with row2_b:
            st.markdown('<div class="input-field-label">핵심 효능</div>', unsafe_allow_html=True)
            selected_effects = st.multiselect("핵심 효능", EFFECT_LIST,
                                              placeholder="예: 장벽 강화, 진정, 미백",
                                              label_visibility="collapsed")

    ingredients = ", ".join(selected_ingredients)
    effects = ", ".join(selected_effects)

    with col_right:
        st.markdown('<div class="input-field-label">제품 이미지 <span class="optional">선택 사항</span></div>', unsafe_allow_html=True)

        if st.session_state._img_bytes is None:
            _tmp_upload = st.file_uploader("이미지 업로드", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
            if _tmp_upload is not None:
                st.session_state._img_bytes = _tmp_upload.read()
                st.session_state._img_name  = _tmp_upload.name
                st.session_state._img_type  = _tmp_upload.type
                st.rerun()
        else:
            import base64 as _b64
            _img_b64 = _b64.b64encode(st.session_state._img_bytes).decode()
            with st.container(key="img_preview_container"):
                _del = st.button("✕", key="btn_change_img")
                st.markdown(f"""
                <div class="img-preview-wrap">
                    <img src="data:{st.session_state._img_type};base64,{_img_b64}" alt="제품 이미지 미리보기">
                </div>
                """, unsafe_allow_html=True)
            if _del:
                st.session_state._img_bytes = None
                st.session_state._img_name  = None
                st.session_state._img_type  = None
                st.rerun()

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        submit_btn = st.button("📊 시장 분석 시작하기", type="primary", use_container_width=True, key="submit_btn")


# ── 메인 ──────────────────────────────────────────────────────────────────────
current_cache_key = f"{product_name}|{selected_category}|{ingredients}|{effects}"

if submit_btn:
    if current_cache_key != st.session_state.cache_key:
        st.session_state.cache_key          = current_cache_key
        st.session_state.rec_data           = None
        st.session_state.top_country        = "US"
        st.session_state.selected_country   = "US"
        st.session_state.research           = None
        st.session_state.strategy_data      = None
        st.session_state.strategy_attempted = False
        st.session_state.ad_images          = None
        st.session_state.review_summary     = None
        st.session_state.report_pdf         = None
        st.session_state.current_tab        = "market"
    st.rerun()

if st.session_state.cache_key:
    product_info = f"제품명: {product_name}, 주요 성분: {ingredients}, 핵심 효능: {effects}"


    # ── 1+2. 로딩이 필요한 경우 대형 로딩 UI 표시 후 API 호출 ────────────────
    if st.session_state.rec_data is None or st.session_state.research is None:
        st.markdown("""
        <div class="loading-overlay">
            <div class="loading-spinner-big"></div>
            <div class="loading-title">AI 시장 분석 중</div>
            <div class="loading-sub">글로벌 K-뷰티 시장 데이터를 분석하고 있습니다…</div>
        </div>
        """, unsafe_allow_html=True)

        if st.session_state.rec_data is None:
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
                    st.session_state.rec_data         = rec_resp.json()
                    st.session_state.top_country      = st.session_state.rec_data.get("top_country", {}).get("country", "US")
                    st.session_state.selected_country = st.session_state.top_country
                else:
                    st.warning("국가 추천 데이터를 불러올 수 없습니다.")
            except Exception as e:
                st.warning(f"국가 추천 서비스 오류: {e}")

        if st.session_state.research is None:
            try:
                resp = requests.post(
                    f"{API_BASE}/match/",
                    json={"category": selected_category, "product_info": product_info},
                    timeout=120,
                )
                if resp.status_code == 200:
                    st.session_state.research = resp.json().get("research", {})
                else:
                    st.error(f"서버 오류 ({resp.status_code})")
                    st.stop()
            except requests.exceptions.ConnectionError:
                st.error("Django 서버가 실행 중이 아닙니다.")
                st.stop()
            except Exception as e:
                st.error(f"오류 발생: {e}")
                st.stop()

        st.rerun()

    research = st.session_state.research or {}

    selected_country = st.session_state.selected_country
    top_country      = st.session_state.top_country
    country = selected_country
    r = research.get(country, {})

    # ── 탭 콘텐츠 (헤더 nav로 전환) ──────────────────────────────────────────

    # ── 시장 분석 ────────────────────────────────────────────────────────────
    if current_tab == "market":
        if st.session_state.rec_data:
            render_country_recommendation(st.session_state.rec_data, selected_country)

        if r:
            render_kpi_row(r, country)
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

            render_kbeauty_share_section(r, country)
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            
            render_trends_section(r, country)
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            
            render_trade_and_channels(selected_category, country, r)
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)



            render_top5_rankings(country)
        elif research:
            st.warning(f"{COUNTRY_KO[country]} 시장 데이터가 없습니다.")

    # ── 리뷰 인사이트 ────────────────────────────────────────────────────────
    elif current_tab == "review":
        if r:
            render_top10_rankings(country)
        elif research:
            st.warning(f"{COUNTRY_KO[country]} 데이터가 없습니다.")

    # ── 마케팅 전략 ──────────────────────────────────────────────────────────
    elif current_tab == "strategy":
        if st.session_state.strategy_data is None and not st.session_state.strategy_attempted:
            st.session_state.strategy_attempted = True
            st.markdown("""
            <div class="loading-overlay">
                <div class="loading-spinner-big"></div>
                <div class="loading-title">AI 마케팅 전략 생성 중</div>
                <div class="loading-sub">타겟 시장에 최적화된 광고 전략을 분석하고 있습니다…</div>
            </div>
            """, unsafe_allow_html=True)
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
                    st.session_state.strategy_data = strategy_resp.json()
            except Exception as e:
                st.info(f"마케팅 전략 서비스 오류: {e}")
            st.rerun()
        elif st.session_state.strategy_data is None and st.session_state.strategy_attempted:
            st.warning("마케팅 전략 생성에 실패했습니다.")
            if st.button("다시 시도", key="retry_strategy"):
                st.session_state.strategy_attempted = False
                st.rerun()

        if st.session_state._img_bytes and st.session_state.strategy_data and st.session_state.ad_images is None:
            import json as _json
            strategy  = st.session_state.strategy_data
            ad_copies = strategy.get("ad_copies", [])
            headline1  = ad_copies[0].get("headline", "")  if len(ad_copies) > 0 else ""
            body_text1 = ad_copies[0].get("body_text", "") if len(ad_copies) > 0 else ""
            headline2  = ad_copies[1].get("headline", "")  if len(ad_copies) > 1 else ""
            body_text2 = ad_copies[1].get("body_text", "") if len(ad_copies) > 1 else ""

            with st.spinner("광고 이미지 생성 중..."):
                try:
                    img_resp = requests.post(
                        f"{API_BASE}/ad-image/",
                        files={"image": (st.session_state._img_name, st.session_state._img_bytes, st.session_state._img_type)},
                        data={
                            "product_name":  product_name,
                            "category":      selected_category,
                            "ingredients":   ingredients,
                            "effects":       effects,
                            "brand_concept": strategy.get("brand_concept", ""),
                            "headline1":     headline1,
                            "body_text1":    body_text1,
                            "headline2":     headline2,
                            "body_text2":    body_text2,
                            "key_messages":  _json.dumps(strategy.get("key_messages", [])),
                            "country":       top_country,
                        },
                        timeout=180,
                    )
                    if img_resp.status_code == 200:
                        st.session_state.ad_images = img_resp.json().get("images", [])
                    else:
                        st.warning(f"광고 이미지 생성 실패 ({img_resp.status_code}): {img_resp.text[:200]}")
                except Exception as e:
                    st.warning(f"광고 이미지 생성 오류: {e}")

        if r:
            st.markdown('<div class="section-header">Top10 브랜드 Meta 광고 현황</div>', unsafe_allow_html=True)
            render_meta_ads_section(country)
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        if st.session_state.strategy_data:
            render_ad_strategy(st.session_state.strategy_data, ad_images=st.session_state.ad_images)

        if st.session_state.rec_data or research:
            st.markdown("---")
            st.markdown('<div class="section-header">보고서 다운로드</div>', unsafe_allow_html=True)

            # review_summary 캐시
            if st.session_state.review_summary is None:
                try:
                    rv_resp = requests.get(
                        f"{API_BASE}/review-summary/",
                        params={"country": top_country},
                        timeout=60,
                    )
                    if rv_resp.status_code == 200:
                        st.session_state.review_summary = rv_resp.json()
                except Exception:
                    pass

            # PDF 캐시 — 전략/이미지가 완성된 시점에 한 번만 생성
            if st.session_state.report_pdf is None:
                st.session_state.report_pdf = generate_report_pdf(
                    product_name=product_name,
                    category=selected_category,
                    ingredients=ingredients,
                    effects=effects,
                    rec_data=st.session_state.rec_data,
                    research=research,
                    strategy_data=st.session_state.strategy_data,
                    top_country=top_country,
                    ad_images=st.session_state.ad_images,
                    review_summary=st.session_state.review_summary,
                )

            st.download_button(
                label="📄 분석 보고서 다운로드 (PDF)",
                data=st.session_state.report_pdf,
                file_name=f"beauty_insight_{product_name}_{selected_category}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

# ── 푸터 ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="fixed-footer">
    <div class="ff-logo">VORA</div>
    <div class="ff-links">
        <a href="#">Privacy Policy</a>
        <a href="#">Terms of Service</a>
        <a href="#">Contact Support</a>
    </div>
    <div class="ff-copy">© 2026 Global Beauty Insight Dashboard. All rights reserved.</div>
</div>
""", unsafe_allow_html=True)
