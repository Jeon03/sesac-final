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
    "cache_key":     None,
    "rec_data":      None,
    "top_country":   "US",
    "research":      None,
    "strategy_data": None,
    "ad_images":     None,
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ── 제품 정보 입력 폼 ──────────────────────────────────────────────────────────
with st.container(border=True):
    st.markdown("""
    <div class="input-card-header">
      <div class="input-card-icon">📋</div>
      <div>
        <div class="input-card-title">제품 정보 입력</div>
        <div class="input-card-subtitle">분석하고자 하는 제품의 상세 정보를 입력해주세요.</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    left_col, right_col = st.columns([2, 1])

    with left_col:
        r1c1, r1c2 = st.columns(2)
        with r1c1:
            st.markdown('<div class="input-field-label">카테고리 <span class="required">*</span></div>', unsafe_allow_html=True)
            selected_category = st.selectbox("카테고리", CATEGORY_LIST, label_visibility="collapsed")
        with r1c2:
            st.markdown('<div class="input-field-label">제품명 <span class="required">*</span></div>', unsafe_allow_html=True)
            product_name = st.text_input("제품명", placeholder="예: 울트라 페이셜 크림", label_visibility="collapsed")

        r2c1, r2c2 = st.columns(2)
        with r2c1:
            st.markdown('<div class="input-field-label">주요 성분</div>', unsafe_allow_html=True)
            selected_ingredients = st.multiselect("주요 성분", INGREDIENT_LIST, label_visibility="collapsed")
            ingredients = ", ".join(selected_ingredients)
        with r2c2:
            st.markdown('<div class="input-field-label">핵심 효능</div>', unsafe_allow_html=True)
            selected_effects = st.multiselect("핵심 효능", EFFECT_LIST, label_visibility="collapsed")
            effects = ", ".join(selected_effects)

    with right_col:
        st.markdown('<div class="input-field-label">제품 이미지 <span class="optional">선택 사항</span></div>', unsafe_allow_html=True)
        uploaded_image = st.file_uploader("이미지 업로드", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        submit_btn = st.button("📊 시장 분석 시작하기", type="primary", use_container_width=True)

st.markdown("---")

# ── 메인 ──────────────────────────────────────────────────────────────────────
current_cache_key = f"{product_name}|{selected_category}|{ingredients}|{effects}"

if submit_btn:
    # 입력값이 바뀌면 캐시 초기화
    if current_cache_key != st.session_state.cache_key:
        st.session_state.cache_key     = current_cache_key
        st.session_state.rec_data      = None
        st.session_state.top_country   = "US"
        st.session_state.research      = None
        st.session_state.strategy_data = None
        st.session_state.ad_images     = None

if st.session_state.cache_key:
    product_info = f"제품명: {product_name}, 주요 성분: {ingredients}, 핵심 효능: {effects}"

    # ── 1. AI 최적 국가 추천: 로딩 → 즉시 렌더링 ────────────────────────────
    if st.session_state.rec_data is None:
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
                    st.session_state.rec_data    = rec_resp.json()
                    st.session_state.top_country = st.session_state.rec_data.get("top_country", {}).get("country", "US")
                else:
                    st.warning("국가 추천 데이터를 불러올 수 없습니다.")
            except Exception as e:
                st.warning(f"국가 추천 서비스 오류: {e}")

    if st.session_state.rec_data:
        render_country_recommendation(st.session_state.rec_data)
        st.markdown("---")

    # ── 2. 시장 데이터: 로딩 → 즉시 렌더링 ──────────────────────────────────
    if st.session_state.research is None:
        with st.spinner(f"'{selected_category}' 시장 데이터 로딩 중..."):
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

    research = st.session_state.research or {}
    if research:
        st.markdown('<div class="section-header">국가별 시장 분석</div>', unsafe_allow_html=True)
        tab_us, tab_jp = st.tabs(["🇺🇸 미국 (USA)", "🇯🇵 일본 (Japan)"])

        for tab, country in [(tab_us, "US"), (tab_jp, "JP")]:
            r = research.get(country, {})
            with tab:
                if not r:
                    st.warning(f"{COUNTRY_KO[country]} 데이터가 없습니다.")
                    continue

                render_kpi_row(r, country)
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

                st.markdown(f'<div class="section-header">K-뷰티 시장 점유율 ({COUNTRY_KO[country]})</div>', unsafe_allow_html=True)
                render_kbeauty_share_section(r, country)
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

                render_trade_and_channels(selected_category, country, r)
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

                render_trends_section(r, country)
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

                st.markdown('<div class="section-header">채널별 베스트셀러 Top 5</div>', unsafe_allow_html=True)
                render_top5_rankings(country)
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

                st.markdown('<div class="section-header">리뷰 인사이트 & 채널 분석</div>', unsafe_allow_html=True)
                render_top10_rankings(country)
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

                st.markdown('<div class="section-header">Top10 브랜드 Meta 광고 현황</div>', unsafe_allow_html=True)
                render_meta_ads_section(country)

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── 3. AI 마케팅 전략: 로딩 → 즉시 렌더링 ───────────────────────────────
    if st.session_state.strategy_data is None:
        with st.spinner("AI 마케팅 전략 생성 중..."):
            try:
                strategy_resp = requests.post(
                    f"{API_BASE}/ad-strategy/",
                    json={
                        "product_name": product_name,
                        "category":     selected_category,
                        "ingredients":  ingredients,
                        "effects":      effects,
                        "country":      st.session_state.top_country,
                    },
                    timeout=120,
                )
                if strategy_resp.status_code == 200:
                    st.session_state.strategy_data = strategy_resp.json()
            except Exception as e:
                st.info(f"마케팅 전략 서비스 오류: {e}")

    # ── 4. 광고 이미지 생성: 로딩 → 즉시 렌더링 ─────────────────────────────
    if uploaded_image and st.session_state.strategy_data and st.session_state.ad_images is None:
        ad_copies = st.session_state.strategy_data.get("ad_copies", [])
        headline1 = ad_copies[0].get("headline", "") if len(ad_copies) > 0 else ""
        headline2 = ad_copies[1].get("headline", "") if len(ad_copies) > 1 else ""

        with st.spinner("광고 이미지 생성 중..."):
            try:
                uploaded_image.seek(0)
                img_resp = requests.post(
                    f"{API_BASE}/ad-image/",
                    files={"image": (uploaded_image.name, uploaded_image.read(), uploaded_image.type)},
                    data={
                        "product_name": product_name,
                        "category":     selected_category,
                        "ingredients":  ingredients,
                        "effects":      effects,
                        "headline1":    headline1,
                        "headline2":    headline2,
                    },
                    timeout=180,
                )
                if img_resp.status_code == 200:
                    st.session_state.ad_images = img_resp.json().get("images", [])
                else:
                    st.warning(f"광고 이미지 생성 실패 ({img_resp.status_code}): {img_resp.text[:200]}")
            except Exception as e:
                st.warning(f"광고 이미지 생성 오류: {e}")

    if st.session_state.strategy_data:
        render_ad_strategy(st.session_state.strategy_data, ad_images=st.session_state.ad_images)

else:
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
