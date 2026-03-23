"""
Meta 광고 라이브러리 크롤링 모듈 (자동화 파이프라인용)

crawl(channel) → (raw_df, df_90d, summary_df)
  - channel: ulta / sephora / qoo10 / rakuten
  - CSV도 meta_crawling_result/ 에 저장
"""
import asyncio
import json
import re
import threading
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from playwright.async_api import async_playwright

_BASE = Path(__file__).parent
PAGE_ID_JSON  = _BASE / "brand_page_ids_all.json"
OUTPUT_DIR    = _BASE / "meta_crawling_result"

HEADLESS          = False
MAX_ADS_PER_BRAND = 200
SCROLL_ROUNDS     = 40
SCROLL_WAIT_MS    = 2200

CHANNEL_CONFIG = {
    "ulta":    {"rankings": _BASE / "ulta_rankings_current.jsonl",    "brand_field": "brand",     "market": "US"},
    "sephora": {"rankings": _BASE / "sephora_rankings_current.jsonl", "brand_field": "brand",     "market": "US"},
    "qoo10":   {"rankings": _BASE / "qoo10_rankings_current.jsonl",   "brand_field": "shop_name", "market": "JP"},
    "rakuten": {"rankings": _BASE / "rakuten_rankings_current.jsonl", "brand_field": "shop_name", "market": "JP"},
}


# ── 유틸 ──────────────────────────────────────────────────────────────────────

def _load_rankings(channel: str) -> list:
    path = CHANNEL_CONFIG[channel]["rankings"]
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def _load_page_map(channel: str) -> dict:
    data = json.load(open(PAGE_ID_JSON, encoding="utf-8"))
    return data.get(channel, {}).get("brands", {})


def _normalize_brand(text: str) -> str:
    return re.sub(r"[\s\u3000]+", "", str(text).strip().lower()) if text else ""


def _extract_date(text: str) -> str:
    if not text:
        return ""
    for pat in [
        r"(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})",
        r"(\d{4})-\s*(\d{1,2})-\s*(\d{1,2})",
        r"(\d{4})/\s*(\d{1,2})/\s*(\d{1,2})",
        r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日",
    ]:
        m = re.search(pat, text)
        if m:
            return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return ""


def _extract_text(raw: str) -> str:
    if not raw:
        return ""
    ignore = ["라이브러리 ID", "Library ID", "게재 시작", "Started running",
               "광고 상세 정보 보기", "See ad details", "플랫폼", "광고"]
    for line in [x.strip() for x in raw.split("\n") if x.strip()]:
        if len(line) > 20 and not any(x.lower() in line.lower() for x in ignore):
            return line
    return ""



def _build_page_url(page_id: str, country: str) -> str:
    return (
        "https://www.facebook.com/ads/library/"
        f"?active_status=active&ad_type=all&country=all"
        "&is_targeted_country=false&media_type=all&search_type=page"
        "&sort_data[direction]=desc&sort_data[mode]=total_impressions"
        f"&view_all_page_id={page_id}"
    )



# ── Playwright 크롤링 ──────────────────────────────────────────────────────────

async def _scroll(page):
    prev = -1
    for _ in range(SCROLL_ROUNDS):
        h = await page.evaluate("document.body.scrollHeight")
        if h == prev:
            break
        prev = h
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(SCROLL_WAIT_MS)


async def _get_cards(page):
    return page.locator(
        '[data-testid="ad-library-dynamic-content-container"]'
    ).locator("xpath=ancestor::div[5]")


async def _parse_card(card, brand, page_id, market, channel, mode) -> dict:
    raw = ""
    try:
        raw = await card.inner_text(timeout=5000)
    except Exception:
        pass
    return {
        "brand":       brand,
        "page_id":     page_id,
        "market":      market,
        "retailer":    channel,
        "source_mode": mode,
        "library_id":  (re.search(r"\d{10,}", raw).group(0)
                        if re.search(r"\d{10,}", raw) else ""),
        "media_type":  "video" if ("video" in raw.lower() or "동영상" in raw.lower()) else "image",
        "start_date":  _extract_date(raw),
        "ad_text":     _extract_text(raw),
    }


async def _collect(page, brand, page_id, market, channel, mode) -> list:
    await _scroll(page)
    cards = await _get_cards(page)
    count = await cards.count()

    ads, seen = [], set()
    for i in range(count):
        data = await _parse_card(cards.nth(i), brand, page_id, market, channel, mode)
        key = data["library_id"] or re.sub(r"\s+", " ", data["ad_text"].lower())[:120]
        if key in seen:
            continue
        seen.add(key)
        ads.append(data)
        if len(ads) >= MAX_ADS_PER_BRAND:
            break
    return ads


async def _crawl_async(channel: str) -> list:
    cfg       = CHANNEL_CONFIG[channel]
    market    = cfg["market"]
    b_field   = cfg["brand_field"]
    rankings  = _load_rankings(channel)
    page_map  = _load_page_map(channel)

    # JP 채널은 브랜드명 정규화 후 매칭
    norm_map = {_normalize_brand(k): v for k, v in page_map.items()}

    brands = list(dict.fromkeys(
        str(r.get(b_field, "")).strip() for r in rankings if r.get(b_field)
    ))

    all_ads = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=HEADLESS,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page = await context.new_page()

        for brand in brands:
            print(f"  [meta/{channel}] {brand} ...")

            # page_id 조회
            if channel in ("ulta", "sephora"):
                entry = page_map.get(brand)
            else:
                entry = norm_map.get(_normalize_brand(brand))

            if not entry:
                print(f"    → page_id 없음, skip")
                continue

            page_id = entry["page_id"]

            await page.goto(_build_page_url(page_id, market),
                            wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(5000 if channel in ("qoo10", "rakuten") else 3000)

            ads = await _collect(page, brand, page_id, market, channel, "page")

            if ads:
                all_ads.extend(ads)
            else:
                # 광고 0개도 집계에 포함 (국가 추천 등 분석용)
                all_ads.append({
                    "brand": brand, "page_id": page_id,
                    "market": market, "retailer": channel,
                    "source_mode": "page", "library_id": "",
                    "media_type": "", "start_date": "", "ad_text": "",
                })
            print(f"    → {len(ads)}개")

        await context.close()
        await browser.close()

    return all_ads


def _summarize(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    now    = datetime.now()
    cutoff = pd.Timestamp(now - timedelta(days=90))
    for brand, g in df.groupby("brand"):
        # dummy 행 제거 후 90일 필터 적용
        real = g[g["library_id"].str.strip() != ""].copy()
        real["dt"] = pd.to_datetime(real["start_date"], errors="coerce")
        real = real[real["dt"] >= cutoff]
        total = len(real)
        img   = (real["media_type"] == "image").sum()
        vid   = (real["media_type"] == "video").sum()
        dates  = real["dt"].dropna()
        latest = dates.max().strftime("%Y-%m-%d") if len(dates) else ""
        r30    = (dates >= pd.Timestamp(now - timedelta(days=30))).sum()
        rows.append({
            "brand":          brand,
            "total_ads":      total,
            "image_ads":      int(img),
            "video_ads":      int(vid),
            "image_ratio":    round(img / total, 3) if total else 0,
            "video_ratio":    round(vid / total, 3) if total else 0,
            "latest_ad_date": latest,
            "recent_30d_ads": int(r30),
        })
    return pd.DataFrame(rows)


# ── 공개 인터페이스 ────────────────────────────────────────────────────────────

def crawl(channel: str):
    """
    channel: ulta / sephora / qoo10 / rakuten
    반환: (raw_df, df_90d, summary_df)
    """
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Windows asyncio 호환 (ProactorEventLoop)
    result = {}
    def _thread():
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
        try:
            result["ads"] = loop.run_until_complete(_crawl_async(channel))
        finally:
            loop.close()

    t = threading.Thread(target=_thread)
    t.start()
    t.join()

    all_ads = result.get("ads", [])
    cols = ["brand", "page_id", "market", "retailer", "source_mode",
            "library_id", "media_type", "start_date", "ad_text"]
    raw_df = pd.DataFrame(all_ads, columns=cols) if all_ads else pd.DataFrame(columns=cols)

    raw_df.to_csv(OUTPUT_DIR / f"{channel}_meta.csv", index=False)

    cutoff  = pd.Timestamp(datetime.now() - timedelta(days=90))
    raw_df["dt"] = pd.to_datetime(raw_df["start_date"], errors="coerce")
    df_90d  = raw_df[raw_df["dt"] >= cutoff].copy()
    df_90d.to_csv(OUTPUT_DIR / f"{channel}_meta_90.csv", index=False)

    # raw_df 전체로 summarize (0개 브랜드 포함), 90일 필터는 내부에서 처리
    summary = _summarize(raw_df) if not raw_df.empty else pd.DataFrame()
    summary.to_csv(OUTPUT_DIR / f"{channel}_meta_summary.csv", index=False)

    print(f"  [meta/{channel}] 완료: 전체 {len(raw_df)}개 / 90일 {len(df_90d)}개")
    return raw_df, df_90d, summary
