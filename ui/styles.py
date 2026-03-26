STYLES = """
<style>
@keyframes spin { to { transform: rotate(360deg); } }
/* 배경 · 레이아웃 */
[data-testid="stAppViewContainer"], [data-testid="stMain"] { background: var(--secondary-background-color) !important; }
[data-testid="stHeader"] { background: transparent !important; }
.main .block-container, .stMainBlockContainer { padding-top: 2rem !important; padding-bottom: 2rem !important; padding-left: 20% !important; padding-right: 20% !important; max-width: 100% !important; }

/* 섹션 제목 */
.section-header { font-size: 16px; font-weight: 700; color: var(--text-color); padding-left: 12px; border-left: 4px solid #1d4ed8; margin-bottom: 16px; }

/* ── 제품 정보 입력 카드 ── */
/* 첫 번째 bordered container = 입력 폼 카드 */
[data-testid="stVerticalBlockBorderWrapper"]:first-of-type > div:first-child {
    border: 1.5px dashed rgba(128,128,128,0.35) !important;
    border-radius: 16px !important;
    box-shadow: none !important;
}
.input-card-header { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.input-card-icon { width: 36px; height: 36px; border-radius: 10px; background: rgba(99,102,241,0.1); display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0; }
.input-card-title { font-size: 16px; font-weight: 700; color: var(--text-color); line-height: 1.3; }
.input-card-subtitle { font-size: 12px; color: #9ca3af; margin-top: 2px; }
.input-field-label { font-size: 13px; font-weight: 600; color: var(--text-color); margin-bottom: 4px; }
.input-field-label .required { color: #6366f1; margin-left: 2px; }
.input-field-label .optional { font-size: 11px; font-weight: 500; color: #9ca3af; background: rgba(128,128,128,0.1); border-radius: 4px; padding: 1px 6px; margin-left: 6px; }

/* 파일 업로더 커스텀 스타일 */
[data-testid="stFileUploaderDropzone"] {
    border: 1.5px dashed rgba(128,128,128,0.35) !important;
    border-radius: 12px !important;
    background: rgba(128,128,128,0.03) !important;
    padding: 20px 16px !important;
}
[data-testid="stFileUploaderDropzone"] > div { justify-content: center; flex-direction: column; align-items: center; gap: 4px; }
[data-testid="stFileUploaderDropzoneInstructions"] > div > span { font-size: 13px !important; font-weight: 600 !important; color: var(--text-color) !important; }
[data-testid="stFileUploaderDropzoneInstructions"] > div > small { font-size: 11px !important; color: #9ca3af !important; }
[data-testid="stFileUploadDropzoneInput"] + div { display: none !important; } /* Browse files 버튼 숨김 */

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

/* AI 마케팅 전략 제안 — 전체 외곽 컨테이너 */
.ad-strategy-outer { background: #1a1f35; border-radius: 18px; padding: 32px 36px 36px; position: relative; overflow: hidden; }
.ad-strategy-outer::before { content: ''; position: absolute; top: -60px; right: -60px; width: 200px; height: 200px; background: rgba(255,255,255,0.03); border-radius: 50%; }

/* 배지 + 부제 */
.ad-strategy-badge { display: inline-flex; align-items: center; gap: 6px; background: rgba(139,92,246,0.2); border-radius: 20px; padding: 6px 16px; font-size: 13px; font-weight: 600; color: rgba(255,255,255,0.95); margin-bottom: 4px; }
.ad-strategy-badge .badge-icon { color: #a78bfa; font-size: 16px; }
.ad-strategy-subtitle { font-size: 12px; color: rgba(255,255,255,0.45); margin-bottom: 20px; }

/* 컨셉 박스 (안쪽 더 어두운 영역) */
.ad-concept-box { background: rgba(255,255,255,0.06); border-radius: 14px; padding: 28px 32px; margin-bottom: 28px; }
.ad-strategy-concept { font-size: 44px; font-weight: 800; color: #fff; margin-bottom: 12px; line-height: 1.25; word-break: keep-all; }
.ad-strategy-reasoning { font-size: 13px; color: rgba(255,255,255,0.65); line-height: 1.7; margin: 0; }

/* 하단 섹션 헤더 (다크 배경 위 흰 텍스트) */
.ad-section-headers { display: flex; gap: 24px; margin-bottom: 16px; flex-wrap: wrap; }
.ad-section-header-item { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 700; color: #fff; }
.ad-section-header-item:first-child { flex: 1; min-width: 240px; }
.ad-section-header-item:last-child { flex: 2; min-width: 400px; }
.ad-section-header-item .header-icon { width: 28px; height: 28px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 14px; background: rgba(139,92,246,0.2); color: #a78bfa; }

/* 하단 카드 행 */
.ad-cards-row { display: flex; gap: 16px; flex-wrap: wrap; }

/* 핵심 소구점 카드 */
.ad-usp-card { flex: 1; min-width: 240px; background: #fff; border-radius: 14px; padding: 24px 24px; justify-content: center; display: flex; flex-direction: column;}
.ad-usp-item { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 16px; }
.ad-usp-item:last-child { margin-bottom: 0; }
.ad-usp-check { width: 24px; height: 24px; border-radius: 50%; background: rgba(139,92,246,0.15); color: #7c3aed; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; flex-shrink: 0; margin-top: 1px; }
.ad-usp-text { font-size: 13px; font-weight: 600; color: #1f2937; line-height: 1.55; }

/* 광고 시안 카드 */
.ad-ref-card { flex: 1; min-width: 220px; background: #fff; border-radius: 14px; overflow: hidden; }
.ad-ref-img { width: 100%; height: 300px; background: #e5e7eb; display: flex; align-items: center; justify-content: center; flex-direction: column; gap: 8px; }
.img-spinner { width: 36px; height: 36px; border: 3px solid #6366f1; border-top-color: transparent; border-radius: 50%; animation: spin 1s linear infinite; }
.ad-ref-content { padding: 18px 20px; }
.ad-ref-label { font-size: 11px; font-weight: 700; letter-spacing: .06em; color: #7c3aed; margin-bottom: 6px; }
.ad-ref-headline { font-size: 14px; font-weight: 700; color: #1f2937; line-height: 1.4; margin-bottom: 14px; }
.ad-ref-body { font-size: 12px; color: #6b7280; line-height: 1.6; }

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
"""
