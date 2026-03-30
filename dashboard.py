import os
import streamlit as st
import requests
import base64
from pathlib import Path
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


API_BASE = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000") + "/api"

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
    "generating_pdf":      False,
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

# 1. 이미지를 Base64로 변환하는 함수
def get_base64_img(path):
    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

# 2. 이미지 경로 및 데이터 준비
img_path = "ui/fonts/1.png"
img_base64 = get_base64_img(img_path)

# 3. HTML 작성 (styles.py에 정의된 클래스 활용)
# 아이콘 이미지는 fh-logo-img를 사용하고, 브랜드명은 fh-logo-text를 사용합니다.
header_html = f"""
<div class="fixed-header">
    <a href="/" target="_self" style="text-decoration:none;" class="fh-logo">
        <img src="data:image/png;base64,{img_base64}" alt="VORA Icon" class="fh-logo-img">
        <span class="fh-logo-text">VORA</span>
    </a>
</div>
"""

# 4. Streamlit에 렌더링
st.markdown(header_html, unsafe_allow_html=True)

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
    st.markdown("<div style='height:clamp(24px, calc((100vh - 816px) / 2), 28vh)'></div>", unsafe_allow_html=True)
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
        <div class="input-card-title"><svg xmlns="http://www.w3.org/2000/svg" width="25" height="25" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" style="vertical-align:-3px;margin-right:6px"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1" stroke-linecap="round" stroke-linejoin="round"/></svg>제품 정보 입력</div>
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
        _can_submit = bool(product_name.strip() and selected_ingredients and selected_effects)
        submit_btn = st.button("시장 분석 시작하기", type="primary", use_container_width=True, key="submit_btn", disabled=not _can_submit)


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
        st.session_state.generating_pdf     = False
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
            render_meta_ads_section(country)
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        if st.session_state.strategy_data:
            render_ad_strategy(st.session_state.strategy_data, ad_images=st.session_state.ad_images)

        st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)

        if st.session_state.rec_data or research:
            _, col_report, _ = st.columns([0.75, 1.5, 0.75])
            with col_report:
                with st.container(border=True, key="report_box"):
                    st.markdown("""
                    <div class="report-box-header">
                      <div class="report-icon-box">
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                          <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                        </svg>
                      </div>
                      <div>
                        <div class="report-box-title">분석 보고서</div>
                        <div class="report-box-subtitle">시장 분석, 리뷰 인사이트, 마케팅 전략을 포함한 종합 PDF 보고서</div>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

                    if st.session_state.report_pdf is None:
                        if st.session_state.generating_pdf:
                            with st.spinner("보고서 생성 중..."):
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
                                st.session_state.generating_pdf = False
                            st.rerun()
                        else:
                            if st.button("보고서 생성하기", type="primary", use_container_width=True, key="btn_generate_pdf"):
                                st.session_state.generating_pdf = True
                                st.rerun()
                    else:
                        st.markdown("""
                        <div class="report-download-label">
                          <div class="report-icon-box">
                            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                              <path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
                            </svg>
                          </div>
                          <span>보고서가 준비됐습니다</span>
                        </div>
                        """, unsafe_allow_html=True)
                        st.download_button(
                            label="분석 보고서 다운로드 (PDF)",
                            data=st.session_state.report_pdf,
                            file_name=f"beauty_insight_{product_name}_{selected_category}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            type="primary",
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
