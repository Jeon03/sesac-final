"""PDF 보고서 생성 — 2페이지 이내

Page 1: 커버 + 1.최적국가 + 2.광고전략
Page 2: 3.시장분석 + 4.리뷰
"""

from __future__ import annotations

import base64
import io
from datetime import date

from fpdf import FPDF

COUNTRY_KO   = {"US": "미국", "JP": "일본"}
_BASE = "ui/fonts"
FONT_PATH      = f"{_BASE}/Pretendard-Regular.ttf"
FONT_BOLD_PATH = f"{_BASE}/Pretendard-Bold.ttf"

BLUE        = (108, 99, 230)    # VORA purple
DARK        = (30, 41, 59)
GRAY        = (107, 114, 128)
LIGHT_BG    = (245, 244, 255)   # purple tint bg
BORDER_COLOR = (200, 196, 245)  # purple tint border
GREEN       = (6, 95, 70)
PINK        = (157, 23, 77)


class ReportPDF(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.add_font("pretendard", "",  FONT_PATH,      uni=True)
        self.add_font("pretendard", "B", FONT_BOLD_PATH, uni=True)
        self.set_auto_page_break(auto=True, margin=15)

    def footer(self):
        self.set_y(-10)
        self.set_font("pretendard", "", 8)
        self.set_text_color(*GRAY)
        self.cell(0, 4, str(self.page_no()), align="C")

    def section_title(self, text: str):
        self.set_font("pretendard", "B", 12)
        self.set_text_color(*DARK)
        x, y = self.get_x(), self.get_y()
        self.set_fill_color(*BLUE)
        self.rect(x, y + 1, 1.5, 4.5, style="F")
        self.set_x(x + 4)
        self.cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(1.5)

    def sub_title(self, text: str):
        self.set_font("pretendard", "B", 10)
        self.set_text_color(*DARK)
        self.cell(0, 5, text, new_x="LMARGIN", new_y="NEXT")

    def kpi_row(self, items: list[tuple[str, str]]):
        n = len(items)
        if not n:
            return
        w = (self.w - self.l_margin - self.r_margin) / n
        y0 = self.get_y()
        for label, value in items:
            x = self.get_x()
            self.set_fill_color(*LIGHT_BG)
            self.set_draw_color(226, 232, 240)
            self.rect(x, y0, w - 1.5, 13, style="FD")
            self.set_xy(x + 2, y0 + 1)
            self.set_font("pretendard", "", 8)
            self.set_text_color(*GRAY)
            self.cell(w - 5, 3.5, label, align="C")
            self.set_xy(x + 2, y0 + 5.5)
            self.set_font("pretendard", "B", 10)
            self.set_text_color(*BLUE)
            self.cell(w - 5, 5.5, str(value), align="C")
            self.set_xy(x + w, y0)
        self.set_y(y0 + 14)

    def tag_line(self, label: str, tags: list[str], color: tuple):
        if not tags:
            return
        self.set_font("pretendard", "B", 9)
        self.set_text_color(*DARK)
        self.cell(18, 5, label)
        self.set_font("pretendard", "", 9)
        self.set_text_color(*color)
        self.cell(0, 5, "  ".join(tags), new_x="LMARGIN", new_y="NEXT")

    def quote_box(self, text: str, max_chars: int = 220):
        if not text:
            return
        truncated = text[:max_chars] + ("..." if len(text) > max_chars else "")
        self.set_font("pretendard", "", 9)
        self.set_text_color(*GRAY)
        self.multi_cell(0, 5, truncated, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)


def _embed_image(pdf: ReportPDF, b64_str: str, x: float, y: float, w: float, h: float):
    try:
        buf = io.BytesIO(base64.b64decode(b64_str))
        pdf.image(buf, x=x, y=y, w=w, h=h, keep_aspect_ratio=True)
    except Exception:
        pass


def generate_report_pdf(
    product_name: str,
    category: str,
    ingredients: str,
    effects: str,
    rec_data: dict | None,
    research: dict | None,
    strategy_data: dict | None,
    top_country: str = "US",
    ad_images: list | None = None,
    review_summary: dict | None = None,
) -> bytes:
    today = date.today().strftime("%Y-%m-%d")
    pdf = ReportPDF()
    pdf.add_page()

    # ── 커버 타이틀 ───────────────────────────────────────────────────────────
    import os
    logo_path = "ui/fonts/vora_logo.png"
    if os.path.exists(logo_path):
        pdf.image(logo_path, x=pdf.l_margin, y=pdf.get_y(), h=12)
        pdf.ln(15)

    pdf.set_font("pretendard", "B", 16)
    pdf.set_text_color(*DARK)
    pdf.cell(0, 8, "Beauty Market Insight Report", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.set_font("pretendard", "", 9)
    pdf.set_text_color(*GRAY)
    pdf.cell(0, 4.5, product_name + "  |  " + today, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # 제품 정보 (라벨 : 값, 한 줄씩)
    label_w = 22
    info_items = [("카테고리", category), ("제품명", product_name)]
    if ingredients:
        info_items.append(("주요 성분", ingredients))
    if effects:
        info_items.append(("핵심 효능", effects))
    for label, val in info_items:
        pdf.set_font("pretendard", "B", 8.5)
        pdf.set_text_color(*GRAY)
        pdf.cell(label_w, 5, label + " ", new_x="RIGHT")
        pdf.set_font("pretendard", "", 8.5)
        pdf.set_text_color(*DARK)
        pdf.cell(0, 5, val, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # ════════════════════════════════════════════════════════════════════════
    # 1. 최적 진출 국가 추천
    # ════════════════════════════════════════════════════════════════════════
    if rec_data:
        top       = rec_data.get("top_country", {})
        ccode     = top.get("country", "US")
        score     = top.get("score", 0)
        detail    = top.get("score_detail", {})
        rationale = rec_data.get("rationale", "")
        countries = rec_data.get("recommended_countries", [])

        pdf.section_title("1. AI 우선 진출 국가 추천")

        # 추천 국가 + 점수 한 줄
        pdf.set_font("pretendard", "B", 11)
        pdf.set_text_color(*BLUE)
        pdf.cell(0, 6, f"{COUNTRY_KO.get(ccode, ccode)}   {score}점",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

        pdf.kpi_row([
            ("트렌드 적합도", str(detail.get("trend",  "-"))),
            ("시장 매력도",   str(detail.get("market", "-"))),
            ("리뷰 경쟁력",   str(detail.get("review", "-"))),
        ])
        pdf.ln(3)
        tags = top.get("trend_matched", [])
        if tags:
            pdf.set_font("pretendard", "", 8)
            pdf.set_text_color(55, 48, 163)
            pdf.cell(0, 4, "매칭 트렌드:  " + "  |  ".join(tags), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)

        if rationale:
            pdf.set_font("pretendard", "", 9)
            pdf.set_text_color(*GRAY)
            pdf.multi_cell(0, 4, rationale, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(5)

    # ════════════════════════════════════════════════════════════════════════
    # 2. AI 광고 전략
    # ════════════════════════════════════════════════════════════════════════
    if strategy_data:
        concept   = strategy_data.get("brand_concept", "")
        reasoning = strategy_data.get("concept_reasoning", "")
        messages  = strategy_data.get("key_messages", [])
        ad_copies = strategy_data.get("ad_copies", [])

        pdf.section_title("2. AI 광고 전략")

        # 광고 이미지
        usable = [img for img in (ad_images or []) if img and img.get("data")]
        if usable:
            page_w = pdf.w - pdf.l_margin - pdf.r_margin
            img_w  = (page_w - 6) / min(len(usable), 2)
            img_h  = 65
            y_img  = pdf.get_y()
            for i, img in enumerate(usable[:2]):
                _embed_image(pdf, img["data"], pdf.l_margin + i * (img_w + 6), y_img, img_w, img_h)
            pdf.set_y(y_img + img_h + 2)
            captions = ["피드 광고 (1:1)", "스토리 광고 (9:16)"]
            for i in range(min(len(usable), 2)):
                pdf.set_xy(pdf.l_margin + i * (img_w + 6), pdf.get_y())
                pdf.set_font("pretendard", "", 6.5)
                pdf.set_text_color(*GRAY)
                pdf.cell(img_w, 4, captions[i], align="C")
            pdf.ln(5)

        # 브랜드 컨셉
        if concept:
            pdf.sub_title("브랜드 컨셉")
            pdf.ln(1)
            pdf.set_font("pretendard", "B", 11)
            pdf.set_text_color(*DARK)
            pdf.multi_cell(0, 4.5, concept, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)
            if reasoning:
                pdf.set_font("pretendard", "", 8.5)
                pdf.set_text_color(*GRAY)
                pdf.multi_cell(0, 4, reasoning[:300] + ("..." if len(reasoning) > 300 else ""),
                               new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)

        # 핵심 메시지
        if messages:
            pdf.sub_title("핵심 메시지")
            pdf.set_font("pretendard", "", 9)
            pdf.set_text_color(*DARK)
            for m in messages[:3]:
                pdf.cell(0, 4.5, "  ✓  " + m, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)

        # 광고 카피
        for i, ad in enumerate(ad_copies[:2], 1):
            pdf.set_font("pretendard", "B", 12)
            pdf.set_text_color(*BLUE)
            pdf.cell(0, 5, f"광고 카피 {i}: {ad.get('headline', '')}",
                     new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("pretendard", "", 9)
            pdf.set_text_color(*DARK)
            pdf.multi_cell(0, 4, ad.get("body_text", ""), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)

    # ════════════════════════════════════════════════════════════════════════
    # 3. 시장 분석 (추천 국가)
    # ════════════════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.ln(1.5)
    r = (research or {}).get(top_country, {})
    if r:
        ms          = r.get("market_size", {})
        kb          = r.get("kbeauty_share", {})
        trends      = r.get("trends", {})
        channels    = r.get("channels", {})

        pdf.section_title(f"3. {COUNTRY_KO.get(top_country, top_country)} 시장 분석")

        cagr_val = ms.get("cagr") or ms.get("growth_rate") or "-"
        pdf.kpi_row([
            ("시장 규모",     str(ms.get("value", "-"))),
            ("CAGR",         str(cagr_val)),
            ("K-뷰티 점유율", str(kb.get("share", "-"))),
            ("수출액",        str(kb.get("export_value", "-"))),
        ])
        pdf.ln(1.5)

        def _근거(label: str, data: dict):
            desc = data.get("description") or data.get("source_quote") or ""
            if desc:
                pdf.set_font("pretendard", "B", 10)
                pdf.set_text_color(*DARK)
                pdf.cell(0, 5.5, label, new_x="LMARGIN", new_y="NEXT")
                pdf.quote_box(desc)

        # 시장 규모 근거
        _근거("시장 규모", ms)

        # 성장률 근거 (market_size 안에 growth_rate 관련 description이 있을 수 있으나
        # 별도 섹션이 없으므로 ms description으로 통합 — 이미 위에서 출력됨)

        # K-뷰티 점유율 근거
        _근거("K-뷰티 점유율", kb)

        # 트렌드 근거
        pdf.sub_title("트렌드")
        ingr   = (trends.get("ingredients") or [])[:6]
        func   = (trends.get("functions") or [])[:5]
        rising = (trends.get("rising_keywords") or [])[:4]
        pdf.tag_line("성분",   ingr,   (30, 64, 175))
        pdf.tag_line("기능",   func,   PINK)
        pdf.tag_line("급상승", rising, GREEN)
        pdf.ln(1)
        _근거("", trends)

        # 채널 근거
        online_ch  = channels.get("online", [])
        offline_ch = channels.get("offline", [])
        ch_names = [(ch.get("name", ch) if isinstance(ch, dict) else str(ch))
                    for ch in (online_ch + offline_ch)[:6]]
        if ch_names:
            pdf.set_font("pretendard", "B", 9)
            pdf.set_text_color(*DARK)
            pdf.cell(22, 5, "주요 채널", new_x="RIGHT")
            pdf.set_font("pretendard", "", 9)
            pdf.cell(0, 5, "  |  ".join(ch_names), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(0.5)
        _근거("", channels)

        pdf.ln(3)

    # ════════════════════════════════════════════════════════════════════════
    # 4. 리뷰 분석
    # ════════════════════════════════════════════════════════════════════════
    platforms_data = (review_summary or {}).get("platforms", {})
    if platforms_data:
        pdf.section_title(f"4. 플랫폼 리뷰 분석")

        for platform, pdata in platforms_data.items():
            pdf.sub_title(platform)

            pos = pdata.get("positive_summary", "")
            neg = pdata.get("negative_summary", "")
            if pos:
                pdf.set_font("pretendard", "B", 7.5)
                pdf.set_text_color(30, 100, 50)
                pdf.cell(0, 4.5, "긍정 리뷰 요약", new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("pretendard", "", 7.5)
                pdf.set_text_color(*DARK)
                pdf.multi_cell(0, 4, pos, new_x="LMARGIN", new_y="NEXT")
            if neg:
                pdf.set_font("pretendard", "B", 7.5)
                pdf.set_text_color(180, 40, 40)
                pdf.cell(0, 4.5, "부정 리뷰 요약", new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("pretendard", "", 7.5)
                pdf.set_text_color(*DARK)
                pdf.multi_cell(0, 4, neg, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(4)

    # 푸터 텍스트
    pdf.set_font("pretendard", "", 6.5)
    pdf.set_text_color(*GRAY)
    pdf.cell(0, 4, "Generated by VORA  ·  " + today, align="C")

    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()
