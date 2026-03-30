import base64, os as _os

def _b64_font(filename):
    path = _os.path.join(_os.path.dirname(__file__), "fonts", filename)
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

_font_regular = _b64_font("Pretendard-Regular.ttf")
_font_bold    = _b64_font("Pretendard-Bold.ttf")

_FONT_FACE = (
    "<style>"
    "@font-face {"
    "font-family:'Pretendard';font-weight:400;"
    f"src:url('data:font/truetype;base64,{_font_regular}') format('truetype');"
    "}"
    "@font-face {"
    "font-family:'Pretendard';font-weight:700;"
    f"src:url('data:font/truetype;base64,{_font_bold}') format('truetype');"
    "}"
    "* { font-family:'Pretendard',-apple-system,BlinkMacSystemFont,sans-serif !important; }"
    "</style>"
)

STYLES = _FONT_FACE + """
<style>
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes pulse-fade { 0%,100%{opacity:.4} 50%{opacity:1} }
/* 배경 · 레이아웃 */
[data-testid="stAppViewContainer"] { zoom: 0.95; }
[data-testid="stAppViewContainer"], [data-testid="stMain"] { background: var(--secondary-background-color) !important; }
[data-testid="stHeader"] { display: none !important; }

/* 스크립트 실행 중 잔상 처리 — 0.15s fade out */
[data-stale="true"] {
    opacity: 0 !important;
    pointer-events: none !important;
    transition: opacity 5s !important;
}
.main .block-container, .stMainBlockContainer { padding-top: 86px !important; padding-bottom: 80px !important; padding-left: 20% !important; padding-right: 20% !important; max-width: 100% !important; }

/* ── 고정 푸터 ── */
.fixed-footer {
    position: fixed; bottom: 0; left: 0; right: 0;
    background: #ffffff;
    border-top: 1px solid rgba(128,128,128,0.15);
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    gap: 10px;
    padding: 16px 6%;
    z-index: 9999;
    box-shadow: 0 -1px 8px rgba(0,0,0,0.04);
}
.ff-logo {
    font-size: 15px; font-weight: 800; letter-spacing: -0.3px;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.ff-links { display: flex; gap: 28px; }
.ff-links a { font-size: 13px; color: #6b7280; text-decoration: none; }
.ff-links a:hover { color: #374151; }
.ff-copy { font-size: 12px; color: #9ca3af; }

/* ── 고정 헤더 ── */
.fixed-header {
    position: fixed; top: 0; left: 0; right: 0;
    height: 70px;
    background: #ffffff;
    border-bottom: 1px solid rgba(128,128,128,0.15);
    display: flex; align-items: center;
    padding: 0 6%;
    z-index: 9999;
    box-shadow: 0 1px 8px rgba(0,0,0,0.05);
}
.fh-logo { display: flex; align-items: center; gap: 8px; }
.fh-logo-img {
    height: 30px;
    width: auto;
    object-fit: contain; /* 이미지 비율 유지 */
    image-rendering: -webkit-optimize-contrast; /* 선명도 보정 */
}
.fh-logo-icon {
    width: 32px; height: 32px; border-radius: 8px;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    display: flex; align-items: center; justify-content: center;
    font-size: 15px; font-weight: 800; color: white; flex-shrink: 0;
}
.fh-logo-text { font-size: 15px; font-weight: 800; background: linear-gradient(135deg, #6366f1, #8b5cf6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: -0.3px; }
.fh-nav { display: flex; align-items: center; gap: 36px; margin: 0 auto; }
.fh-nav-item {
    font-size: 13px; font-weight: 500; color: #9ca3af;
    text-decoration: none; padding: 18px 0;
    border-bottom: 2px solid transparent;
    transition: color 0.15s, border-color 0.15s;
    white-space: nowrap;
}
.fh-nav-item:hover { color: var(--text-color); }
.fh-nav-item.active { color: #6366f1; border-bottom-color: #6366f1; font-weight: 600; }

/* ── 헤더 안에 고정되는 nav 버튼 ── */
.st-key-nav_market, .st-key-nav_review, .st-key-nav_strategy {
    position: fixed !important;
    top: 0 !important;
    height: 70px !important;
    display: flex !important;
    align-items: center !important;
    z-index: 10001 !important;
    margin: 0 !important;
    padding: 0 !important;
}
.st-key-nav_market   { left: calc(50% - 190px) !important; width: 120px !important; }
.st-key-nav_review   { left: calc(50% - 60px)  !important; width: 130px !important; }
.st-key-nav_strategy { left: calc(50% + 82px)  !important; width: 130px !important; }

.st-key-nav_market button,
.st-key-nav_review button,
.st-key-nav_strategy button {
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
    color: #9ca3af !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    height: 70px !important;
    min-height: 0 !important;
    padding: 0 4px !important;
    box-shadow: none !important;
    width: 100% !important;
}
.st-key-nav_market [data-testid="stButton"] > button[kind="primary"],
.st-key-nav_review [data-testid="stButton"] > button[kind="primary"],
.st-key-nav_strategy [data-testid="stButton"] > button[kind="primary"] {
    background: transparent !important;
    background-image: none !important;
    border-bottom-color: #6366f1 !important;
    color: #111827 !important;
    font-weight: 600 !important;
    box-shadow: none !important;
}
/* nav 버튼 hover — primary(선택됨) / secondary(미선택) 모두 배경 변화 없음 */
.st-key-nav_market [data-testid="stButton"] > button:hover,
.st-key-nav_review [data-testid="stButton"] > button:hover,
.st-key-nav_strategy [data-testid="stButton"] > button:hover,
.st-key-nav_market [data-testid="stButton"] > button[kind="primary"]:hover,
.st-key-nav_review [data-testid="stButton"] > button[kind="primary"]:hover,
.st-key-nav_strategy [data-testid="stButton"] > button[kind="primary"]:hover,
.st-key-nav_market [data-testid="stButton"] > button[kind="secondary"]:hover,
.st-key-nav_review [data-testid="stButton"] > button[kind="secondary"]:hover,
.st-key-nav_strategy [data-testid="stButton"] > button[kind="secondary"]:hover {
    background: transparent !important;
    background-color: transparent !important;
    background-image: none !important;
    border-color: transparent !important;
    border-bottom-color: #6366f1 !important;
    color: #111827 !important;
    box-shadow: none !important;
}

/* ── 대형 로딩 오버레이 — 화면 전체 fixed 커버 ── */
.loading-overlay {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    z-index: 9999;
    background: rgba(255,255,255,0.97);
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    gap: 20px;
}
.loading-spinner-big {
    width: 60px; height: 60px;
    border: 5px solid rgba(99,102,241,0.15);
    border-top-color: #6366f1;
    border-radius: 50%;
    animation: spin 0.9s linear infinite;
}
.loading-title {
    font-size: 20px; font-weight: 700; color: var(--text-color);
    animation: pulse-fade 1.8s ease-in-out infinite;
}
.loading-sub { font-size: 13px; color: #9ca3af; margin-top: -8px; }

/* 섹션 제목 */
.section-header { font-size: 16px; font-weight: 700; color: var(--text-color); padding-left: 12px; border-left: 4px solid #1d4ed8; margin-bottom: 16px; }

/* ── 제품 정보 입력 카드 ── */
/* 첫 번째 bordered container = 입력 폼 카드 */
[data-testid="stVerticalBlockBorderWrapper"]:first-of-type > div:first-child {
    border: 1.5px dashed rgba(128,128,128,0.35) !important;
    border-radius: 16px !important;
    box-shadow: 0 4px 16px rgba(0,0,0,.08), 0 1px 4px rgba(0,0,0,.05) !important;
}
.input-card-header { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.input-card-icon { width: 36px; height: 36px; border-radius: 10px; background: rgba(99,102,241,0.1); display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0; }
.input-card-title { font-size: 25px; font-weight: 700; color: var(--text-color); line-height: 1.3; }
.input-card-subtitle { font-size: 15px; color: #9ca3af; margin-top: 2px; }
.input-field-label { font-size: 13px; font-weight: 600; color: var(--text-color); margin-bottom: 4px; }
.input-field-label .required { color: #6366f1; margin-left: 2px; }
.input-field-label .optional { font-size: 11px; font-weight: 500; color: #9ca3af; background: rgba(128,128,128,0.1); border-radius: 4px; padding: 1px 6px; margin-left: 6px; }

/* 이미지 미리보기 컨테이너 (X버튼 포지셔닝 기준) */
.st-key-img_preview_container {
    position: relative !important;
}
.st-key-img_preview_container > div:first-child { /* X버튼 행 공간 없애기 */
    height: 0 !important;
    overflow: visible !important;
}

/* 이미지 미리보기 */
.img-preview-wrap {
    border: 1.5px solid rgba(99,102,241,0.25);
    border-radius: 12px;
    overflow: hidden;
    background: transparent;
    height: 160px;
    display: flex; align-items: center; justify-content: center;
}
.img-preview-wrap img {
    width: 100%; height: 100%;
    object-fit: contain;
    display: block;
}

/* 이미지 삭제 X 버튼 - 이미지 우상단 absolute */
.st-key-btn_change_img {
    position: absolute !important;
    top: 8px !important;
    right: 8px !important;
    z-index: 20 !important;
    width: auto !important;
    padding: 0 !important;
    margin: 0 !important;
}
.st-key-btn_change_img button {
    width: 26px !important;
    height: 26px !important;
    min-height: 26px !important;
    border-radius: 50% !important;
    padding: 0 !important;
    background: rgba(0,0,0,0.45) !important;
    background-image: none !important;
    color: #fff !important;
    border: none !important;
    font-size: 13px !important;
    line-height: 1 !important;
    box-shadow: none !important;
}

/* 파일 업로더 — 목업 스타일 (보라 테마, 아이콘 중앙) */
[data-testid="stFileUploaderDropzone"] {
    border: 1.5px dashed #c4b5fd !important;
    border-radius: 12px !important;
    background: transparent;
    padding: 28px 16px !important;
    min-height: 160px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}
[data-testid="stFileUploaderDropzone"] > div { justify-content: center; flex-direction: column; align-items: center; gap: 6px; }
[data-testid="stFileUploaderDropzoneInstructions"] > div > span {
    font-size: 14px !important; font-weight: 600 !important; color: #4f46e5 !important;
}
[data-testid="stFileUploaderDropzoneInstructions"] > div > small {
    font-size: 12px !important; color: #9ca3af !important;
}
[data-testid="stFileUploadDropzoneInput"] + div { display: none !important; }

/* 입력 필드 — 라운드, 연회색 배경, 높이 56px 통일 */
[data-testid="stTextInput"] > div,
[data-testid="stTextInput"] > div > div {
    min-height: 56px !important;
    height: 56px !important;
}
[data-testid="stTextInput"] input {
    background: #f9fafb !important;
    border: 1.5px solid #e5e7eb !important;
    border-radius: 10px !important;
    height: 56px !important;
    padding: 0 16px !important;
    font-size: 14px !important;
    box-sizing: border-box !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"] > div:first-child,
[data-testid="stMultiSelect"] [data-baseweb="select"] > div:first-child {
    background: #f9fafb !important;
    border: 1.5px solid #e5e7eb !important;
    border-radius: 10px !important;
    min-height: 56px !important;
    padding: 8px 16px !important;
}
/* 컬럼 간 행 높이 통일 — label+widget 블록을 동일 높이로 */
[data-testid="stSelectbox"],
[data-testid="stTextInput"],
[data-testid="stMultiSelect"] {
    margin-top: 0 !important;
    margin-bottom: 0 !important;
    padding-bottom: 0 !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stSelectbox"] [data-baseweb="select"] > div:first-child:focus-within,
[data-testid="stMultiSelect"] [data-baseweb="select"] > div:first-child:focus-within {
    border-color: #a5b4fc !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.08) !important;
}
/* 멀티셀렉트 태그 색상 */
[data-testid="stMultiSelect"] [data-baseweb="tag"] {
    background: #ede9fe !important;
    border-radius: 6px !important;
}
[data-testid="stMultiSelect"] [data-baseweb="tag"] span { color: #6d28d9 !important; }

/* 분석 시작 버튼 — 보라색 (탭 버튼 red보다 앞에 선언) */
[data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    border-color: #6366f1 !important;
    color: #fff !important;
    font-weight: 600 !important;
}
[data-testid="stButton"] > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #4f46e5, #7c3aed) !important;
    border-color: #4f46e5 !important;
}

/* KPI 카드 */
.kpi-card { background: var(--background-color); border: 1px solid rgba(128,128,128,0.2); border-radius: 14px; padding: 20px 22px; box-shadow: 0 1px 4px rgba(0,0,0,.06); }
.kpi-label { font-size: 12px; color: #9ca3af; font-weight: 600; margin-bottom: 8px; }
.kpi-value { font-size: 28px; font-weight: 700; color: var(--text-color); line-height: 1.2; }
.kpi-sub { font-size: 12px; color: #9ca3af; margin-top: 4px; }
.kpi-delta-pos { font-size: 12px; color: #10b981; font-weight: 600; margin-top: 4px; }
.kpi-channel { font-size: 24px; font-weight: 700; color: #0ea5e9; }

/* 태그 */
.tag-us { display: inline-block; background: rgba(130,113,255,0.12); color: #8271FF; border-radius: 6px; padding: 3px 10px; font-size: 12px; font-weight: 600; margin: 3px 3px 3px 0; }
.tag-jp { display: inline-block; background: rgba(130,113,255,0.12); color: #8271FF; border-radius: 6px; padding: 3px 10px; font-size: 12px; font-weight: 600; margin: 3px 3px 3px 0; }
.tag-ingredient { display: inline-block; background: rgba(29,78,216,0.12); color: #3b82f6; border-radius: 6px; padding: 3px 10px; font-size: 12px; font-weight: 600; margin: 3px 3px 3px 0; }
.tag-function { display: inline-block; background: rgba(16,185,129,0.12); color: #10b981; border-radius: 6px; padding: 3px 10px; font-size: 12px; font-weight: 600; margin: 3px 3px 3px 0; }
.tag-rising { display: inline-block; background: rgba(128,128,128,0.10); color: #9ca3af; border-radius: 6px; padding: 3px 10px; font-size: 12px; font-weight: 600; margin: 3px 3px 3px 0; }
.tag-label { font-size: 10px; font-weight: 700; letter-spacing: 0.1em; color: #9ca3af; margin-top: 10px; margin-bottom: 4px; }

/* 순위 리스트 */
.rank-row { display: flex; align-items: flex-start; padding: 10px 0; border-bottom: 1px solid rgba(128,128,128,0.15); }
.rank-num { font-size: 18px; font-weight: 700; color: rgba(156,163,175,0.8); width: 28px; flex-shrink: 0; margin-right: 12px; line-height: 1.4; }
.rank-num.top { color: #1d4ed8; }
.rank-name { font-size: 14px; font-weight: 600; color: var(--text-color); }
.rank-desc { font-size: 12px; color: #9ca3af; margin-top: 2px; }

/* Top5 테이블 */
.top5-wrap { border-radius: 12px; overflow: hidden; border: 1.5px solid rgba(128,128,128,0.25); box-shadow: 0 4px 16px rgba(0,0,0,.08), 0 1px 4px rgba(0,0,0,.05); }
.top5-table { width: 100%; border-collapse: collapse; }
.top5-table th { font-size: 10px; font-weight: 700; letter-spacing: .08em; color: #9ca3af; padding: 8px 12px; text-align: left; border-bottom: 1px solid rgba(128,128,128,0.15); background: var(--background-color); }
.top5-table td { padding: 9px 12px; font-size: 13px; color: var(--text-color); border-bottom: 1px solid rgba(128,128,128,0.1); vertical-align: middle; background: var(--background-color); }
.top5-name { font-weight: 600; }
.top5-brand { color: #9ca3af; font-size: 12px; }

/* 랭킹 섹션 래퍼 */
.ranking-wrapper {
    display: flex;
    border: 1.5px solid rgba(128,128,128,0.25);
    border-radius: 16px;
    background: var(--background-color);
    overflow: hidden;
    min-height: 620px;
    box-shadow: 0 4px 16px rgba(0,0,0,.08), 0 1px 4px rgba(0,0,0,.05);
}

/* 랭킹 리스트 아이템 */
.panel-label { font-size: 12px; font-weight: 700; color: #9ca3af; letter-spacing: .05em; margin-bottom: 8px; }
.rank-item { display: flex; align-items: center; gap: 12px; padding: 10px 14px; border-radius: 10px; border: 1px solid transparent; margin-bottom: 0; position: relative; z-index: 1; background: var(--background-color); cursor: pointer; transition: all 0.15s; }
.rank-item:hover { background: rgba(124,58,237,0.04); }
.rank-item.selected { background: rgba(124,58,237,0.08); border-color: #7c3aed; }
.rank-num { font-size: 18px; font-weight: 800; color: #d1d5db; min-width: 28px; line-height: 1; text-align: center; }
.rank-item.selected .rank-num { color: #7c3aed; }
.rank-info { flex: 1; min-width: 0; }
.rank-name { font-size: 13px; font-weight: 600; color: var(--text-color); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.rank-sub { font-size: 11px; color: #9ca3af; margin-top: 1px; }
.rank-arrow { font-size: 20px; font-weight: 700; color: #7c3aed; }

/* 랭킹 카드: 버튼을 카드 위에 겹치기 */
.rank-item {
    pointer-events: none;
}
[class*="st-key-ri_"] {
    margin-top: -52px !important;
    height: 52px !important;
    min-height: 0 !important;
    position: relative !important;
    z-index: 3 !important;
    overflow: visible !important;
}
[class*="st-key-ri_"] button {
    opacity: 0 !important;
    height: 52px !important;
    min-height: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
    border: none !important;
    cursor: pointer !important;
    width: 100% !important;
}

/* 리뷰 분석 헤더 */
.rv-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.rv-label { font-size: 11px; color: #9ca3af; font-weight: 600; margin-bottom: 4px; }
.rv-title { font-size: 20px; font-weight: 700; color: var(--text-color); }
.rv-platform { font-size: 14px; font-weight: 600; color: #7c3aed; }
.rv-sub { font-size: 12px; color: #9ca3af; margin-top: 2px; }
.rv-badge { background: rgba(124,58,237,0.08); border-radius: 12px; padding: 10px 18px; text-align: center; flex-shrink: 0; margin-left: 16px; }
.rv-badge-label { font-size: 11px; color: #9ca3af; font-weight: 600; }
.rv-badge-score { font-size: 30px; font-weight: 800; color: #7c3aed; }
.rv-badge-denom { font-size: 14px; color: #9ca3af; font-weight: 400; }

/* 섹션 라벨 */
.rv-section-label { font-size: 12px; font-weight: 700; color: #9ca3af; letter-spacing: .05em; margin-bottom: 10px; }

/* 카테고리 만족도 바 */
.rv-bar-wrap { margin-bottom: 10px; }
.rv-bar-label { font-size: 13px; color: var(--text-color); margin-bottom: 4px; display: flex; justify-content: space-between; }
.rv-bar-score { font-weight: 700; color: #7c3aed; }
.rv-bar-bg { background: rgba(128,128,128,0.15); border-radius: 6px; height: 8px; }
.rv-bar-fill { background: linear-gradient(90deg, #7c3aed, #a78bfa); border-radius: 6px; height: 8px; }

/* 키워드 태그 */
.rv-kw { display: inline-block; background: rgba(124,58,237,0.10); color: #7c3aed; border: 1px solid rgba(124,58,237,0.25); border-radius: 20px; padding: 5px 14px; font-size: 12px; font-weight: 600; margin: 3px 4px 3px 0; }
.rv-kw-gray { display: inline-block; background: rgba(128,128,128,0.08); color: #9ca3af; border: 1px solid rgba(128,128,128,0.15); border-radius: 20px; padding: 5px 14px; font-size: 12px; font-weight: 600; margin: 3px 4px 3px 0; }

/* 리뷰 요약 카드 */
.rv-review-card { border-radius: 12px; padding: 16px 18px; font-size: 13px; line-height: 1.7; box-shadow: 0 4px 16px rgba(0,0,0,.07), 0 1px 4px rgba(0,0,0,.04); }
.rv-review-card.pos { background: rgba(16,185,129,0.06); border: 1.5px solid rgba(16,185,129,0.3); }
.rv-review-card.neg { background: rgba(239,68,68,0.06); border: 1.5px solid rgba(239,68,68,0.3); }
.rv-review-card-label { font-size: 12px; font-weight: 700; margin-bottom: 8px; }
.rv-review-card-label.pos { color: #10b981; }
.rv-review-card-label.neg { color: #ef4444; }
.rv-review-card-text { color: var(--text-color); }

/* Complaints · Opportunities */
.rv-section-title { font-size: 13px; font-weight: 700; margin-bottom: 10px; }
.rv-section-title.red { color: #ef4444; }
.rv-section-title.green { color: #10b981; }
.rv-complaint-row { margin-bottom: 8px; display: flex; align-items: center; gap: 10px; }
.rv-complaint-label { font-size: 13px; font-weight: 600; color: var(--text-color); width: 120px; flex-shrink: 0; }
.rv-complaint-bar-bg { flex: 1; background: rgba(239,68,68,0.12); border-radius: 6px; height: 8px; }
.rv-complaint-bar-fill { background: #ef4444; border-radius: 6px; height: 8px; }
.rv-complaint-pct { font-size: 12px; color: #ef4444; font-weight: 700; width: 36px; text-align: right; }
.rv-opp-item { font-size: 12px; color: var(--text-color); margin-bottom: 8px; line-height: 1.5; }

/* Meta 광고 모니터링 */
[data-testid="stHorizontalBlock"]:has(.mon-card) { align-items: stretch !important; }
[data-testid="stHorizontalBlock"]:has(.mon-card) > [data-testid="stColumn"] { display: flex !important; flex-direction: column !important; }
[data-testid="stHorizontalBlock"]:has(.mon-card) > [data-testid="stColumn"] > div,
[data-testid="stHorizontalBlock"]:has(.mon-card) > [data-testid="stColumn"] > div > div,
[data-testid="stHorizontalBlock"]:has(.mon-card) > [data-testid="stColumn"] > div > div > div { flex: 1 !important; display: flex !important; flex-direction: column !important; }
.mon-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.mon-title { font-size: 17px; font-weight: 700; color: var(--text-color); }
.mon-updated { font-size: 11px; color: #9ca3af; }
.mon-card { background: var(--background-color); border: 1.5px solid rgba(128,128,128,0.2); border-radius: 14px; padding: 20px 18px 18px; box-shadow: 0 2px 10px rgba(0,0,0,.06); height: 100% !important; min-height: 250px; box-sizing: border-box; display: flex; flex-direction: column; }
.mon-brand-name { display: inline-block; background: rgba(139,92,246,0.12); color: #7c3aed; font-size: 14px; font-weight: 700; border-radius: 8px; padding: 4px 12px; margin-bottom: 16px; }
.mon-count-row { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 12px; }
.mon-count-label { font-size: 12px; color: #9ca3af; font-weight: 500; }
.mon-count-value { font-size: 26px; font-weight: 800; color: var(--text-color); }
.mon-copy-label { font-size: 11px; font-weight: 700; color: #9ca3af; letter-spacing: .05em; margin-bottom: 6px; }
.mon-copy-text { font-size: 13px; color: var(--text-color); line-height: 1.5; font-style: flex: 1; }
.mon-link { display: inline-block; margin-top: 14px; font-size: 13px; font-weight: 600; color: #6366f1; text-decoration: none; }
.mon-link:hover { text-decoration: underline; }

/* AI 마케팅 전략 제안 — 전체 외곽 컨테이너 */
/* 보고서 박스 */
.report-box-header { display: flex; align-items: center; gap: 14px; margin-bottom: 20px; }
.report-icon-box { width: 44px; height: 44px; border-radius: 12px; border: 1.5px solid rgba(128,128,128,0.25); display: flex; align-items: center; justify-content: center; flex-shrink: 0; color: var(--text-color); }
.report-box-title { font-size: 18px; font-weight: 700; color: var(--text-color); line-height: 1.3; }
.report-box-subtitle { font-size: 13px; color: #9ca3af; margin-top: 2px; }
.report-download-label { display: flex; align-items: center; gap: 10px; font-size: 14px; font-weight: 600; color: var(--text-color); margin-bottom: 12px; }
/* 보고서 다운로드 버튼 보라색 */
.st-key-report_box [data-testid="stDownloadButton"] button { background-color: #8271FF !important; border-color: #8271FF !important; color: #fff !important; }
.st-key-report_box [data-testid="stDownloadButton"] button:hover { background-color: #6f5ee6 !important; border-color: #6f5ee6 !important; }

/* 시장 분석 시작하기 버튼 */
.st-key-submit_btn button { background-color: #8271FF !important; border-color: #8271FF !important; color: #fff !important; }
.st-key-submit_btn button:hover { background-color: #6f5ee6 !important; border-color: #6f5ee6 !important; }
.st-key-submit_btn button p::before {
    content: '';
    display: inline-block;
    width: 15px;
    height: 15px;
    margin-right: 7px;
    vertical-align: -2px;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='white' stroke-width='2'%3E%3Ccircle cx='11' cy='11' r='8'/%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M21 21l-4.35-4.35'/%3E%3C/svg%3E");
    background-size: contain;
    background-repeat: no-repeat;
}

.ad-strategy-outer { background: linear-gradient(135deg, #1a1f35 0%, #3a3d6a 100%); border-radius: 18px; padding: 32px 36px 36px; position: relative; overflow: hidden; }

/* 배지 */
.ad-strategy-badge { display: inline-flex; align-items: center; gap: 14px; margin-bottom: 20px; }
.badge-icon-box { width: 44px; height: 44px; border-radius: 12px; border: none; display: flex; align-items: center; justify-content: center; flex-shrink: 0; background: rgba(255,255,255,0.18); }
.badge-title { font-size: 18px; font-weight: 700; color: rgba(255,255,255,0.95); line-height: 1.3; }
.badge-subtitle { font-size: 12px; color: rgba(255,255,255,0.45); margin-top: 2px; }

/* 컨셉 박스 */
.ad-concept-box { background: rgba(255,255,255,0.06); border-radius: 14px; padding: 28px 32px; margin-bottom: 28px; }
.ad-strategy-concept { font-size: 44px; font-weight: 800; color: #fff; margin-bottom: 12px; line-height: 1.25; word-break: keep-all; }
.ad-strategy-reasoning { font-size: 13px; color: rgba(255,255,255,0.65); line-height: 1.7; margin: 0; }

/* 섹션 헤더 */
.ad-section-header-item { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 700; color: #fff; margin-bottom: 12px; }
.ad-section-header-item .header-icon-box { width: 26px; height: 26px; border-radius: 7px; border: none; display: flex; align-items: center; justify-content: center; background: rgba(255,255,255,0.18); flex-shrink: 0; }

/* 카드 전체 행 + 컬럼 */
.ad-cards-row { display: flex; gap: 16px; align-items: flex-start; }
.ad-col-usp { flex: 0 0 350px; display: flex; flex-direction: column; }
.ad-col-refs { flex: 1; display: flex; flex-direction: column; }
.ad-ref-cards-inner { display: flex; gap: 16px; flex: 1; }

/* 핵심 소구점 카드 */
.ad-usp-card { flex: 1; background: #fff; border-radius: 14px; padding: 24px; justify-content: center; display: flex; flex-direction: column; border: 1.5px solid rgba(128,128,128,0.2); box-shadow: 0 4px 16px rgba(0,0,0,.1), 0 1px 4px rgba(0,0,0,.06); }
.ad-usp-item { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 16px; }
.ad-usp-item:last-child { margin-bottom: 0; }
.ad-usp-check { width: 24px; height: 24px; border-radius: 50%; background: rgba(139,92,246,0.15); color: #7c3aed; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; flex-shrink: 0; margin-top: 1px; }
.ad-usp-text { font-size: 13px; font-weight: 600; color: #1f2937; line-height: 1.55; }

/* 광고 시안 카드 */
.ad-ref-card { flex: 1; min-width: 200px; background: #fff; border-radius: 14px; overflow: hidden; border: 1.5px solid rgba(128,128,128,0.2); box-shadow: 0 4px 16px rgba(0,0,0,.1), 0 1px 4px rgba(0,0,0,.06); }
.ad-ref-img { width: 100%; height: 300px; background: #e5e7eb; display: flex; align-items: center; justify-content: center; flex-direction: column; gap: 8px; }
.img-spinner { width: 36px; height: 36px; border: 3px solid #6366f1; border-top-color: transparent; border-radius: 50%; animation: spin 1s linear infinite; }
.ad-ref-content { padding: 18px 20px; }
.ad-ref-label { font-size: 12px; font-weight: 700; letter-spacing: .06em; color: #7c3aed; margin-bottom: 6px; }
.ad-ref-headline { font-size: 16px; font-weight: 700; color: #1f2937; line-height: 1.4; margin-bottom: 14px; }
.ad-ref-body { font-size: 14px; color: #6b7280; line-height: 1.6; }

/* st.container(border=True) 통일 */
[data-testid="stVerticalBlockBorderWrapper"] > div:first-child {
    background: var(--background-color) !important;
    border-radius: 14px !important;
    border: 1.5px solid rgba(128,128,128,0.25) !important;
    box-shadow: 0 4px 16px rgba(0,0,0,.08), 0 1px 4px rgba(0,0,0,.05) !important;
}

/* ─── 리뷰 탭 (플랫폼 탭) 스타일 ────────────────────────────────────── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    gap: 0 !important;
    border-bottom: 2px solid rgba(128,128,128,0.15) !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    font-size: 14px !important;
    font-weight: 600 !important;
    color: #9ca3af !important;
    padding: 10px 0 !important;
    flex: 1 !important;
    justify-content: center !important;
    background: transparent !important;
    border-bottom: 2px solid transparent !important;
}
[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {
    color: #7c3aed !important;
    border-bottom: 2px solid #7c3aed !important;
    background: transparent !important;
}
[data-testid="stTabs"] [data-baseweb="tab"]:hover {
    color: #7c3aed !important;
    background: rgba(124,58,237,0.04) !important;
}
[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
    background: #7c3aed !important;
    height: 2px !important;
}

/* ─── 국가 선택 오버레이 버튼 ─────────────────────────────────────── */
[class*="st-key-btn_country_"] {
    margin-top: -84px !important;
    height: 84px !important;
    min-height: 0 !important;
    position: relative !important;
    z-index: 3 !important;
    margin-bottom: 0 !important;
    width: 100% !important;
}
[class*="st-key-btn_country_"] button {
    opacity: 0 !important;
    height: 84px !important;
    min-height: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
    border: none !important;
    cursor: pointer !important;
    width: 100% !important;
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

/* 파일 업로더 Browse files → 한국어 */
[data-testid="stFileUploaderDropzone"] button { font-size: 0 !important; }
[data-testid="stFileUploaderDropzone"] button::after { content: '파일 선택'; font-size: 14px; }
</style>
"""
